"""
Test suite for PII Gateway, Model Router, and Cost Meter.
Maps to Hackathon Non-negotiable Rules 6, 11, and 12:
- 'PII gateway masks/minimises data before any external model call and logs what was sent.
   Aadhaar/PAN/bank details never reach a model.'
- 'Model provider must be switchable through config only. Deterministic fake fallback.'
- 'Cost meter: record tokens, model and INR cost per step.'
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pii.masker import PIIGateway
from core.llm.fake_provider import FakeLLMProvider
from core.llm.router import ModelRouter
from core.llm.meter import CostMeter


def test_pii_masks_aadhaar_pan_and_bank_details():
    gateway = PIIGateway()
    sensitive_input = (
        "Candidate Arjun Sharma. Aadhaar: 3456 7890 1234, PAN: ABCDE1234F, "
        "Bank A/C: 987654321012, Phone: +91 9876543210, Email: arjun.sharma@gmail.com, Salary: 18 LPA."
    )

    result = gateway.mask(sensitive_input)
    masked = result.masked_text

    # Assert raw sensitive data is NOT present in masked output
    assert "3456 7890 1234" not in masked
    assert "ABCDE1234F" not in masked
    assert "987654321012" not in masked
    assert "+91 9876543210" not in masked
    assert "arjun.sharma@gmail.com" not in masked
    assert "18 LPA" not in masked

    # Assert correct redaction tokens
    assert "<REDACTED_AADHAAR>" in masked
    assert "<REDACTED_PAN>" in masked
    assert "<REDACTED_BANK_ACCOUNT>" in masked
    assert "<PHONE_1>" in masked
    assert "<EMAIL_1>" in masked

    # Verify no leak assertion passes on masked text
    PIIGateway.assert_no_pii_leak(masked)

    # Rehydration test: email and phone can be rehydrated, but Aadhaar/PAN cannot!
    rehydrated = gateway.rehydrate(masked, result.rehydration_map)
    assert "+91 9876543210" in rehydrated
    assert "arjun.sharma@gmail.com" in rehydrated
    assert "<REDACTED_AADHAAR>" in rehydrated  # Still redacted!


def test_assert_no_pii_leak_raises_on_raw_data():
    with pytest.raises(AssertionError) as exc:
        PIIGateway.assert_no_pii_leak("Here is my Aadhaar: 4567 8901 2345")
    assert "Aadhaar number detected" in str(exc.value)

    with pytest.raises(AssertionError) as exc:
        PIIGateway.assert_no_pii_leak("My PAN is BKRPK9981M")
    assert "PAN detected" in str(exc.value)


@pytest.mark.asyncio
async def test_model_router_threshold_and_escalation():
    router = ModelRouter()

    # 1. Normal prompt with high confidence -> small model
    resp_small = await router.generate("What is my onboarding status?", task="intent")
    assert resp_small.model == "small-default"
    assert resp_small.intent == "check_status"

    # 2. Ambiguous query with low initial confidence -> escalation model
    resp_esc = await router.generate(
        "Some random ambiguous text without clear HR intent",
        task="intent",
        initial_confidence=0.60,  # Below 0.75 threshold
    )
    assert resp_esc.model == "escalation-mid"

    # Check small model share metrics
    stats = router.get_stats()
    assert stats["total_calls"] >= 2
    assert "small_model_share_pct" in stats


def test_cost_meter_calculation_and_projection():
    meter = CostMeter()

    # Small model cost
    cost_small = meter.calculate_step_cost(tokens_in=100, tokens_out=50, model="small-default")
    assert cost_small == 0.0  # self-hosted default is 0 INR/token

    # Escalation model cost
    cost_esc = meter.calculate_step_cost(tokens_in=1000, tokens_out=500, model="escalation-mid")
    assert cost_esc > 0.0  # (1.0 * 0.4) + (0.5 * 1.6) = 0.4 + 0.8 = 1.2 INR
    assert cost_esc == 1.2

    # Monthly projection formula verification (docs/COST_MODEL_AND_METRICS.md §6)
    proj = CostMeter.project_monthly_costs(
        hires_per_month=300,
        employees=5000,
        chat_msgs_per_employee=2,
        cost_per_onboarding=3.0,
        cost_per_chat_msg=0.10,
        fixed_infra_monthly_inr=25000.0,
    )
    # 300 * 3 = 900
    # 5000 * 2 * 0.10 = 1000
    # fixed = 25000
    # total = 26900
    assert proj["onboarding_cost_inr"] == 900.0
    assert proj["chat_cost_inr"] == 1000.0
    assert proj["total_monthly_projection_inr"] == 26900.0
