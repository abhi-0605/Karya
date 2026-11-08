"""Skill: assets.allocate_laptop"""
from typing import Any
import httpx
import os

MOCK_BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8001")


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    employee_name = inputs.get("legal_name") or f"{inputs.get('first_name', 'Arjun')} {inputs.get('last_name', 'Sharma')}"
    grade = inputs.get("grade", "L2")
    location = inputs.get("location", "Bengaluru")

    payload = {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "grade": grade,
        "location": location,
        "asset_type": "laptop",
    }

    if ctx.gateway:
        return await ctx.gateway.call("it_assets", "/it/assets/allocate", payload, ctx.idempotency_key)

    headers = {"Idempotency-Key": ctx.idempotency_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{MOCK_BASE_URL}/it/assets/allocate", json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    model = "MacBook Pro 14\"" if grade in ("L4", "L5", "L6") else "Dell Latitude 5540"
    return {
        "status": "allocated",
        "asset_id": f"ASSET-{employee_id[-4:]}-{ctx.idempotency_key[:6].upper()}",
        "model": model,
        "pool": "premium" if grade in ("L4", "L5", "L6") else "standard",
        "employee_id": employee_id,
        "idempotency_key": ctx.idempotency_key,
    }
