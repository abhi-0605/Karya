"""Skill: dsr.extract_pii"""
from typing import Any
from core.pii.masker import PIIGateway


async def run(ctx: Any, inputs: dict) -> dict:
    subject_id = inputs.get("subject_id", "EMP0001")
    gateway = PIIGateway()

    # Synthetic profile data
    raw_summary = (
        f"Subject Record for {subject_id}: Email: emp.{subject_id.lower()}@tbo.com, "
        "Phone: +91 9876543210, PAN: ABCDE1234F, Aadhaar: 9876 5432 1012, "
        "Bank A/C: 987654321098."
    )

    # Clean through PII Gateway: Aadhaar, PAN, Bank are blocked/redacted
    masked = gateway.mask(raw_summary)

    return {
        "status": "extracted",
        "subject_id": subject_id,
        "pii_detected": masked.pii_detected,
        "redacted_items": masked.redacted_items,
        "sanitized_summary": masked.masked_text,
        "idempotency_key": getattr(ctx, "idempotency_key", f"dsr-pii-{subject_id}"),
    }
