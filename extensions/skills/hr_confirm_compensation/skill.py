"""Skill: hr.confirm_compensation (Executed only after named HRBP approval)."""
from typing import Any


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    grade = inputs.get("grade", "L2")

    return {
        "status": "compensation_confirmed",
        "employee_id": employee_id,
        "grade": grade,
        "confirmed_by_role": "hrbp",
        "idempotency_key": ctx.idempotency_key,
    }
