"""
Chat API — conversational HR assistant endpoint.
Accepts a user message, classifies intent, enforces RBAC, dispatches to handler.

Intents handled:
  check_status   → query workflow run status for the user
  laptop_query   → query laptop allocation status
  leave_query    → query leave balance / policy
  notice_query   → query notice period policy
  policy_qa      → policy RAG (grounded in YAML policy files)
  approval_action→ list pending approvals for the user
  general_qa     → LLM general answer (escalated if low confidence)
"""
from __future__ import annotations
import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.llm.intent import IntentClassifier
from core.llm.rag import PolicyRAG
from core.llm.fake_provider import FakeLLMProvider

log = structlog.get_logger()
router = APIRouter()

# Module-level singletons (stateless except for stats counters)
_intent_clf = IntentClassifier()
_rag = PolicyRAG()
_fake_llm = FakeLLMProvider()

# In-memory chat audit log (lightweight, no DB session needed)
_chat_audit: list[dict] = []
# In-memory escalation queue for chat (no DB for demo simplicity)
_chat_escalations: list[dict] = []


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "demo_employee"
    user_role: Optional[str] = "employee"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    confidence: float
    escalated: bool
    citations: list[str] = []
    human_queue_item_id: Optional[str] = None


# ── Handlers per intent ───────────────────────────────────────────────────────

async def _handle_check_status(user_id: str) -> str:
    """Return a synthetic workflow status summary for the demo."""
    return (
        f"The onboarding workflow for **{user_id}** is currently **in progress**. "
        "Steps completed: Directory, Email, Laptop, Access Card, Payroll Setup, Buddy Assignment, Welcome Message. "
        "Awaiting: **Compensation Confirmation** (pending HRBP approval)."
    )


async def _handle_laptop_query(user_id: str) -> str:
    return (
        "Your laptop allocation request has been **submitted** to IT. "
        "Expected delivery: within 2 business days of your joining date. "
        "If not received, escalate via `IT-OPS` ticket or contact your buddy."
    )


async def _handle_leave_query() -> str:
    rag_result = await _rag.answer("leave policy annual casual maternity")
    return rag_result.answer


async def _handle_notice_query() -> str:
    rag_result = await _rag.answer("notice period resignation")
    return rag_result.answer


async def _handle_policy_qa(message: str) -> tuple[str, list[str]]:
    rag_result = await _rag.answer(message)
    return rag_result.answer, rag_result.citations


async def _handle_approval_action(user_role: str) -> str:
    if user_role not in ("hrbp", "hr_head", "manager"):
        return "You don't have permissions to view pending approvals. Please contact your HRBP."
    return (
        "You have **1 pending approval**: Compensation confirmation for new hire. "
        "Use `POST /api/approvals/{id}/approve` or visit the HR Dashboard to approve/reject."
    )


async def _handle_general_qa(message: str, user_id: str = "user", already_escalated: bool = False) -> tuple[str, bool, Optional[str]]:
    """LLM general answer; escalate to human queue if confidence is low."""
    resp = await _fake_llm.generate(message, task="general")
    escalated = already_escalated or (resp.confidence < 0.75)
    hq_id = None

    if escalated:
        # Park in in-memory escalation log (no DB session needed for chat)
        hq_id = str(uuid.uuid4())[:8]
        _chat_escalations.append({
            "id": hq_id,
            "user_id": user_id,
            "message": message,
            "confidence": resp.confidence,
            "model": resp.model,
        })
        reply = (
            "I'm not fully certain about this. I've flagged your query for an HRBP to follow up. "
            f"Queue reference: `{hq_id}`."
        )
    else:
        reply = resp.text

    return reply, escalated, hq_id


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/message", response_model=ChatResponse)
async def chat_message(body: ChatRequest) -> ChatResponse:
    session_id = body.session_id or str(uuid.uuid4())
    user_id = body.user_id or "demo_employee"
    user_role = body.user_role or "employee"

    # 1. Classify intent
    intent_result = await _intent_clf.classify(body.message, user_role=user_role)

    # 2. RBAC gate
    if not intent_result.allowed_for_role:
        reply = (
            f"Your role (`{user_role}`) does not have permission to perform `{intent_result.intent}` actions. "
            f"Minimum required role: `{intent_result.min_role}`."
        )
        _chat_audit.append({
            "actor": user_id,
            "action": "chat.rbac_denied",
            "intent": intent_result.intent,
            "role": user_role,
        })
        log.info("Chat RBAC denied", actor=user_id, intent=intent_result.intent, role=user_role)
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            escalated=False,
        )

    # 3. Dispatch by intent
    citations: list[str] = []
    hq_id: Optional[str] = None
    escalated = intent_result.escalated

    intent = intent_result.intent

    if intent == "check_status":
        reply = await _handle_check_status(user_id)

    elif intent == "laptop_query":
        reply = await _handle_laptop_query(user_id)

    elif intent == "leave_query":
        reply = await _handle_leave_query()

    elif intent == "notice_query":
        reply = await _handle_notice_query()

    elif intent == "policy_qa":
        reply, citations = await _handle_policy_qa(body.message)

    elif intent == "approval_action":
        reply = await _handle_approval_action(user_role)

    else:  # general_qa or unknown
        reply, escalated, hq_id = await _handle_general_qa(
            body.message, user_id=user_id, already_escalated=intent_result.escalated
        )

    # 4. Lightweight in-memory audit (no DB session needed for chat endpoint)
    _chat_audit.append({
        "actor": user_id,
        "action": f"chat.{intent}",
        "intent": intent,
        "role": user_role,
        "session_id": session_id,
        "escalated": escalated,
        "message_len": len(body.message),
    })
    log.info("Chat handled", actor=user_id, intent=intent, escalated=escalated)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        intent=intent,
        confidence=intent_result.confidence,
        escalated=escalated,
        citations=citations,
        human_queue_item_id=hq_id,
    )


@router.get("/intents")
async def list_intents() -> dict[str, Any]:
    """List supported intents and their minimum required roles."""
    from core.llm.intent import INTENT_ROLE_MAP
    return {"intents": INTENT_ROLE_MAP}
