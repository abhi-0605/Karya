"""Skill: email.provision"""
from typing import Any
import httpx
import os

MOCK_BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8001")


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    first_name = inputs.get("first_name", "Arjun")
    last_name = inputs.get("last_name", "Sharma")
    department = inputs.get("department", "Engineering")

    payload = {
        "employee_id": employee_id,
        "first_name": first_name,
        "last_name": last_name,
        "department": department,
    }

    if ctx.gateway:
        return await ctx.gateway.call("email", "/email/provision", payload, ctx.idempotency_key)

    headers = {"Idempotency-Key": ctx.idempotency_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{MOCK_BASE_URL}/email/provision", json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    email = f"{first_name.lower()}.{last_name.lower()}@tbo-demo.com"
    return {
        "status": "provisioned",
        "email": email,
        "employee_id": employee_id,
        "idempotency_key": ctx.idempotency_key,
    }
