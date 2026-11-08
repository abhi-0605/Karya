"""
Cost Meter — records tokens, model tier, and INR costs per step.
Computes metrics per completed workflow, including infra amortisation.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import yaml
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

log = structlog.get_logger()

INFRA_CONFIG = Path(__file__).parent.parent.parent / "config" / "infra_costs.yaml"
MODELS_CONFIG = Path(__file__).parent.parent.parent / "config" / "models.yaml"


@dataclass
class CostRecord:
    tokens_in: int
    tokens_out: int
    cost_inr: float
    model: str
    infra_share_inr: float
    total_step_cost_inr: float


class CostMeter:
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        models_config_path: Path = MODELS_CONFIG,
        infra_config_path: Path = INFRA_CONFIG,
    ):
        self.db = db
        self.models_cfg = self._load_yaml(models_config_path)
        self.infra_cfg = self._load_yaml(infra_config_path)

        # Default pricing (INR per 1k tokens)
        self.small_cost_per_1k = float(self.models_cfg.get("default", {}).get("cost_per_1k_tokens_inr", 0.0))
        self.esc_in_per_1k = float(self.models_cfg.get("escalation", {}).get("cost_per_1k_in_inr", 0.4))
        self.esc_out_per_1k = float(self.models_cfg.get("escalation", {}).get("cost_per_1k_out_inr", 1.6))

        # Infra allocation per workflow
        self.infra_share_per_workflow = float(self.infra_cfg.get("infra_cost_per_workflow_inr", 2.5))

    def _load_yaml(self, path: Path) -> dict:
        if path.exists():
            try:
                return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass
        return {}

    def calculate_step_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """Calculate INR cost for tokens used."""
        if "escalation" in model.lower() or "pro" in model.lower():
            in_cost = (tokens_in / 1000.0) * self.esc_in_per_1k
            out_cost = (tokens_out / 1000.0) * self.esc_out_per_1k
            return round(in_cost + out_cost, 4)
        else:
            # Small model self-hosted / low-cost tier
            return round(((tokens_in + tokens_out) / 1000.0) * self.small_cost_per_1k, 4)

    async def record_call(
        self,
        step_run_id: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        pii_masked: bool = True,
    ) -> CostRecord:
        """Record model call in database and return CostRecord."""
        token_cost = self.calculate_step_cost(tokens_in, tokens_out, model)
        now = datetime.now(timezone.utc)

        record = CostRecord(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_inr=token_cost,
            model=model,
            infra_share_inr=0.0,
            total_step_cost_inr=token_cost,
        )

        if self.db:
            from app.models.workflow import ModelCallMeter
            meter_entry = ModelCallMeter(
                id=f"meter-{uuid.uuid4().hex[:10]}",
                step_run_id=step_run_id,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_inr=token_cost,
                pii_masked=pii_masked,
                called_at=now,
            )
            self.db.add(meter_entry)
            await self.db.commit()

        log.info("Cost recorded", step_run_id=step_run_id, model=model, inr=token_cost)
        return record

    @staticmethod
    def project_monthly_costs(
        hires_per_month: int = 300,
        employees: int = 5000,
        chat_msgs_per_employee: int = 2,
        cost_per_onboarding: float = 3.5,
        cost_per_chat_msg: float = 0.10,
        fixed_infra_monthly_inr: float = 25000.0,
    ) -> dict:
        """
        Monthly projection formula from docs/COST_MODEL_AND_METRICS.md §6:
        monthly_cost = H * cost_per_onboarding + E * M * cost_per_chat_msg + fixed_infra
        """
        onboarding_total = hires_per_month * cost_per_onboarding
        chat_total = employees * chat_msgs_per_employee * cost_per_chat_msg
        monthly_total = onboarding_total + chat_total + fixed_infra_monthly_inr

        return {
            "hires_per_month": hires_per_month,
            "employees": employees,
            "onboarding_cost_inr": round(onboarding_total, 2),
            "chat_cost_inr": round(chat_total, 2),
            "fixed_infra_monthly_inr": round(fixed_infra_monthly_inr, 2),
            "total_monthly_projection_inr": round(monthly_total, 2),
            "cost_per_hire_effective_inr": round(monthly_total / hires_per_month, 2) if hires_per_month > 0 else 0,
        }
