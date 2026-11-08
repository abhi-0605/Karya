"""
Deterministic Fake LLM Provider.
Guarantees end-to-end platform functionality offline with 0 external API keys.
Returns realistic, structured responses for HR intent classification, welcome drafting, and policy Q&A.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int
    confidence: float
    model: str
    intent: Optional[str] = None
    citations: list[str] = None


class FakeLLMProvider:
    def __init__(self, model_name: str = "fake-default"):
        self.model_name = model_name

    async def generate(self, prompt: str, task: str = "general", context: Optional[dict] = None) -> LLMResponse:
        """Generate deterministic response based on task type and keywords in prompt."""
        tokens_in = max(10, len(prompt.split()))
        p_lower = prompt.lower()

        # 1. Intent Classification
        if task == "intent" or "classify" in p_lower:
            if any(k in p_lower for k in ["status", "where is", "progress", "onboarding"]):
                intent = "check_status"
                conf = 0.94
                text = "check_status"
            elif any(k in p_lower for k in ["laptop", "macbook", "computer", "asset", "hardware"]):
                intent = "laptop_query"
                conf = 0.92
                text = "laptop_query"
            elif any(k in p_lower for k in ["leave", "vacation", "holiday", "sick"]):
                intent = "leave_query"
                conf = 0.89
                text = "leave_query"
            elif any(k in p_lower for k in ["notice", "resignation", "exit", "settlement"]):
                intent = "notice_query"
                conf = 0.88
                text = "notice_query"
            elif any(k in p_lower for k in ["approve", "signoff", "reject"]):
                intent = "approval_action"
                conf = 0.95
                text = "approval_action"
            else:
                intent = "general_qa"
                conf = 0.65  # Triggers escalation router!
                text = "general_qa"

            tokens_out = len(text.split())
            return LLMResponse(
                text=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                confidence=conf,
                model=self.model_name,
                intent=intent,
            )

        # 2. Welcome Message Drafting
        elif task == "welcome" or "welcome" in p_lower:
            name = (context or {}).get("first_name", "Team Member")
            dept = (context or {}).get("department", "TBO")
            role = (context or {}).get("role_title", "Associate")
            text = (
                f"Welcome to TBO, {name}! 🎉 We are thrilled to have you join as {role} in {dept}. "
                "Your directory account and email are setup. Your laptop and access card are in progress. "
                "Reach out anytime if you have any questions!"
            )
            tokens_out = len(text.split())
            return LLMResponse(
                text=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                confidence=0.98,
                model=self.model_name,
            )

        # 3. Policy Q&A
        elif task == "policy_qa" or "policy" in p_lower:
            if "notice" in p_lower:
                text = "Per TBO Notice Period Policy (notice_period@4), standard notice period for grades L1-L3 is 30 days with buyout allowed. For grades L4-L6, notice period is 90 days."
                citations = ["extensions/policies/notice_period.yaml#rules"]
            elif "probation" in p_lower:
                text = "Per TBO Probation Policy (probation@2), standard probation duration is 90 days for L1-L3 and 180 days for L4-L6, subject to manager review."
                citations = ["extensions/policies/probation.yaml#rules"]
            elif "leave" in p_lower:
                text = "Per TBO Leave Policy (leave_policy@1), employees in grades L1-L3 receive 18 days of annual privilege leave and 12 days casual leave. Maternity leave is 26 weeks."
                citations = ["extensions/policies/leave_policy.yaml#rules"]
            else:
                text = "I checked TBO HR policies: please reach out to your designated HRBP for custom guidelines."
                citations = ["extensions/policies/"]

            tokens_out = len(text.split())
            return LLMResponse(
                text=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                confidence=0.95,
                model=self.model_name,
                citations=citations,
            )

        # 4. Default general text
        text = "KaryaOS assistant: Request processed successfully."
        return LLMResponse(
            text=text,
            tokens_in=tokens_in,
            tokens_out=len(text.split()),
            confidence=0.90,
            model=self.model_name,
        )
