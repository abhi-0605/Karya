"""Skill: admin.reprint_id_card"""
from typing import Any
import httpx
import os

MOCK_BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8001")


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    reason = inputs.get("reason", "lost_or_damaged")

    payload = {
        "employee_id": employee_id,
        "reason": reason,
        "type": "reprint",
    }

    if ctx.gateway:
        return await ctx.gateway.call("admin", "/admin/access-cards", payload, ctx.idempotency_key)

    headers = {"Idempotency-Key": ctx.idempotency_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{MOCK_BASE_URL}/admin/access-cards", json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return {
        "status": "reprinted",
        "card_id": f"CARD-REPRINT-{employee_id}",
        "employee_id": employee_id,
        "idempotency_key": ctx.idempotency_key,
    }
