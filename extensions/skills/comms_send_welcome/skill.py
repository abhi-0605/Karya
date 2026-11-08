"""Skill: comms.send_welcome (Drafts warm personalized Day 1 welcome message)."""
from typing import Any


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    first_name = inputs.get("first_name", "Arjun")
    department = inputs.get("department", "Engineering")
    role_title = inputs.get("role_title", "Associate Software Engineer")
    location = inputs.get("location", "Bengaluru")

    message = (
        f"Welcome to TBO, {first_name}! 🎉 "
        f"We are thrilled to have you join the {department} team as {role_title} in our {location} office. "
        "Your directory account and email are active. Your laptop and access card are provisioned. "
        "Have an amazing Day 1!"
    )

    return {
        "status": "sent",
        "employee_id": employee_id,
        "channel": "slack_and_email",
        "message": message,
        "idempotency_key": ctx.idempotency_key,
    }
