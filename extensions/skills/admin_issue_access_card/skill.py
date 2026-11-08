"""Skill: admin.issue_access_card"""
from typing import Any
import httpx
import os

MOCK_BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8001")


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    employee_name = inputs.get("legal_name") or f"{inputs.get('first_name', 'Arjun')} {inputs.get('last_name', 'Sharma')}"
    location = inputs.get("location", "Bengaluru")

    payload = {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "location": location,
        "access_zones": ["general", "cafeteria"],
    }

    if ctx.gateway:
        return await ctx.gateway.call("admin_cards", "/admin/access-cards/issue", payload, ctx.idempotency_key)

    headers = {"Idempotency-Key": ctx.idempotency_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{MOCK_BASE_URL}/admin/access-cards/issue", json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return {
        "status": "issued",
        "card_id": f"CARD-{employee_id}-{ctx.idempotency_key[:6].upper()}",
        "employee_id": employee_id,
        "location": location,
        "access_zones": ["general", "cafeteria"],
        "idempotency_key": ctx.idempotency_key,
    }
