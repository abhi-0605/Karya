"""
Intent Classifier — classifies user messages into HR intents.
Rules-first: keyword matching returns confident intents without an LLM call.
Only ambiguous / unknown messages invoke the FakeLLMProvider (or real model).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import structlog

from core.llm.fake_provider import FakeLLMProvider, LLMResponse

log = structlog.get_logger()

# Intent → minimum role that can act on it
INTENT_ROLE_MAP: dict[str, str] = {
    "check_status":    "employee",
    "laptop_query":    "employee",
    "leave_query":     "employee",
    "notice_query":    "employee",
    "policy_qa":       "employee",
    "approval_action": "hrbp",
    "admin_action":    "hr_head",
    "general_qa":      "employee",
}

# Fast keyword → intent, no LLM needed
_KEYWORD_RULES: list[tuple[list[str], str, float]] = [
    (["status", "where is", "progress", "onboarding", "workflow"], "check_status", 0.95),
    (["laptop", "macbook", "computer", "asset", "hardware"],       "laptop_query",  0.95),
    (["leave", "vacation", "holiday", "sick", "pl ", "cl "],       "leave_query",   0.92),
    (["notice", "resignation", "exit", "settlement"],               "notice_query",  0.90),
    (["approve", "reject", "signoff", "pending approval"],          "approval_action", 0.95),
    (["policy", "probation", "notice period", "gratuity"],         "policy_qa",     0.90),
]


@dataclass
class IntentResult:
    intent: str
    confidence: float
    source: str  # "rules" | "llm"
    escalated: bool
    allowed_for_role: bool
    min_role: str


class IntentClassifier:
    def __init__(self, provider: Optional[FakeLLMProvider] = None):
        self.provider = provider or FakeLLMProvider()

    async def classify(self, message: str, user_role: str = "employee") -> IntentResult:
        p = message.lower()

        # 1. Fast rules-first path
        for keywords, intent, conf in _KEYWORD_RULES:
            if any(k in p for k in keywords):
                min_role = INTENT_ROLE_MAP.get(intent, "employee")
                allowed = self._role_can(user_role, min_role)
                log.info("Intent classified by rules", intent=intent, conf=conf, role=user_role)
                return IntentResult(
                    intent=intent, confidence=conf, source="rules",
                    escalated=False, allowed_for_role=allowed, min_role=min_role,
                )

        # 2. Fall back to LLM classification
        resp: LLMResponse = await self.provider.generate(message, task="intent")
        intent = resp.intent or "general_qa"
        min_role = INTENT_ROLE_MAP.get(intent, "employee")
        allowed = self._role_can(user_role, min_role)
        escalated = resp.confidence < 0.75

        log.info("Intent classified by LLM", intent=intent, conf=resp.confidence,
                 escalated=escalated, role=user_role)
        return IntentResult(
            intent=intent, confidence=resp.confidence, source="llm",
            escalated=escalated, allowed_for_role=allowed, min_role=min_role,
        )

    def _role_can(self, user_role: str, required_role: str) -> bool:
        """True if user_role can perform actions requiring required_role."""
        hierarchy = ["employee", "manager", "hrbp", "hr_head", "it_ops",
                     "admin_ops", "finance", "auditor"]
        try:
            return hierarchy.index(user_role) >= hierarchy.index(required_role)
        except ValueError:
            return False
