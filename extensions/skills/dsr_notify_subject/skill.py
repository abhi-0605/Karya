"""Skill: dsr.notify_subject"""
from typing import Any


async def run(ctx: Any, inputs: dict) -> dict:
    subject_id = inputs.get("subject_id", "EMP0001")
    request_type = inputs.get("request_type", "access")

    message = (
        f"DPDP Notice: Your Data Subject Request ({request_type}) for ID {subject_id} "
        "has been reviewed, approved by the Data Protection Officer, and completed."
    )

    return {
        "status": "delivered",
        "subject_id": subject_id,
        "notification_message": message,
        "channel": "email",
        "delivered_at": "2026-11-08T18:05:00Z",
        "idempotency_key": getattr(ctx, "idempotency_key", f"dsr-notif-{subject_id}"),
    }
