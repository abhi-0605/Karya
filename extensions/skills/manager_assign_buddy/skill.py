"""Skill: manager.assign_buddy"""
from typing import Any


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    department = inputs.get("department", "Engineering")

    # Match buddy in same department / location
    buddy_id = "EMP0005"
    buddy_name = "Priya Nair"

    return {
        "status": "buddy_assigned",
        "employee_id": employee_id,
        "buddy_id": buddy_id,
        "buddy_name": buddy_name,
        "department": department,
        "idempotency_key": ctx.idempotency_key,
    }
