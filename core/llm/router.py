"""
Model Router — routes prompts between Small (default) and Escalation (mid-tier) models.
Routing rule:
  confidence < 0.75 OR input_tokens > 3000 OR validation_failed -> escalation model
Otherwise small model.
Always routes through PIIGateway to ensure zero PII leaves the platform boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml
import structlog

from core.pii.masker import PIIGateway
from core.llm.fake_provider import FakeLLMProvider, LLMResponse

log = structlog.get_logger()

CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "models.yaml"


@dataclass
class RouterDecision:
    selected_tier: str  # "small" | "escalation"
    model_name: str
    reason: str
    masked_text: str
    rehydration_map: dict


class ModelRouter:
    def __init__(self, config_path: Path = CONFIG_FILE, pii_gateway: Optional[PIIGateway] = None):
        self.config = self._load_config(config_path)
        self.pii = pii_gateway or PIIGateway()
        self.confidence_threshold = float(self.config.get("router", {}).get("confidence_threshold", 0.75))
        self.max_small_tokens = int(self.config.get("router", {}).get("max_small_tokens", 3000))

        # Providers
        self.small_provider = FakeLLMProvider(model_name="small-default")
        self.escalation_provider = FakeLLMProvider(model_name="escalation-mid")

        # Stats
        self.total_calls = 0
        self.small_model_calls = 0
        self.escalation_model_calls = 0

    def _load_config(self, path: Path) -> dict:
        if path.exists():
            try:
                return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as e:
                log.warning("Could not load models config", error=str(e))
        return {}

    def decide_tier(self, prompt: str, initial_confidence: float = 1.0, validation_failed: bool = False) -> tuple[str, str]:
        """Determine whether prompt goes to small model or escalation model."""
        tokens_est = len(prompt.split())

        if validation_failed:
            return "escalation", "Previous validation check failed; escalated to mid-tier model"
        if tokens_est > self.max_small_tokens:
            return "escalation", f"Prompt length ({tokens_est} tokens) exceeds small model limit ({self.max_small_tokens})"
        if initial_confidence < self.confidence_threshold:
            return "escalation", f"Initial confidence ({initial_confidence:.2f}) is below threshold ({self.confidence_threshold:.2f})"

        return "small", "Standard query within token limit and confidence bound"

    async def generate(
        self,
        prompt: str,
        task: str = "general",
        context: Optional[dict] = None,
        initial_confidence: float = 1.0,
        validation_failed: bool = False,
    ) -> LLMResponse:
        """
        1. Mask PII via PIIGateway.
        2. Assert no forbidden PII leak.
        3. Decide model tier (small vs escalation).
        4. Invoke model.
        5. Check output confidence; if small model returns low confidence, re-route to escalation!
        6. Rehydrate tokens.
        """
        # 1. Mask PII
        mask_result = self.pii.mask(prompt)
        sanitized_prompt = mask_result.masked_text

        # 2. Hard check
        PIIGateway.assert_no_pii_leak(sanitized_prompt)

        # 3. Router decision
        tier, reason = self.decide_tier(
            prompt=sanitized_prompt,
            initial_confidence=initial_confidence,
            validation_failed=validation_failed,
        )

        self.total_calls += 1

        if tier == "escalation":
            self.escalation_model_calls += 1
            log.info("Prompt routed to ESCALATION model", reason=reason)
            resp = await self.escalation_provider.generate(sanitized_prompt, task=task, context=context)
        else:
            # First try small model
            resp = await self.small_provider.generate(sanitized_prompt, task=task, context=context)
            # If small model confidence drops below threshold -> escalate!
            if resp.confidence < self.confidence_threshold:
                self.escalation_model_calls += 1
                log.info("Small model confidence below threshold; re-routing to ESCALATION model", conf=resp.confidence)
                resp = await self.escalation_provider.generate(sanitized_prompt, task=task, context=context)
            else:
                self.small_model_calls += 1

        # 4. Rehydrate tokens in generated response
        if mask_result.rehydration_map:
            resp.text = self.pii.rehydrate(resp.text, mask_result.rehydration_map)

        return resp

    def get_stats(self) -> dict:
        small_pct = (self.small_model_calls / self.total_calls * 100) if self.total_calls > 0 else 100.0
        return {
            "total_calls": self.total_calls,
            "small_model_calls": self.small_model_calls,
            "escalation_model_calls": self.escalation_model_calls,
            "small_model_share_pct": round(small_pct, 1),
        }
