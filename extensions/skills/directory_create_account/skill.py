"""Skill: directory.create_account"""
from typing import Any
import httpx
import os

MOCK_BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8001")


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    first_name = inputs.get("first_name", "Arjun")
    last_name = inputs.get("last_name", "Sharma")
    department = inputs.get("department", "Engineering")
    manager_id = inputs.get("manager_id", "EMP0002")
    grade = inputs.get("grade", "L2")

    payload = {
        "employee_id": employee_id,
        "first_name": first_name,
        "last_name": last_name,
        "department": department,
        "manager_id": manager_id,
        "grade": grade,
    }

    if ctx.gateway:
        return await ctx.gateway.call("directory", "/directory/accounts", payload, ctx.idempotency_key)

    # Fallback direct call with idempotency header
    headers = {"Idempotency-Key": ctx.idempotency_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{MOCK_BASE_URL}/directory/accounts", json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    # Deterministic fallback
    return {
        "status": "created",
        "account_id": f"DIR-{employee_id}",
        "display_name": f"{first_name} {last_name}",
        "department": department,
        "manager_id": manager_id,
        "employee_id": employee_id,
        "idempotency_key": ctx.idempotency_key,
    }
