"""Skill: payroll.setup_employee"""
from typing import Any
import httpx
import os

MOCK_BASE_URL = os.getenv("MOCK_API_BASE_URL", "http://localhost:8001")


async def run(ctx: Any, inputs: dict) -> dict:
    employee_id = inputs.get("employee_id", "EMP0001")
    grade = inputs.get("grade", "L2")
    location = inputs.get("location", "Bengaluru")
    department = inputs.get("department", "Engineering")
    start_date = inputs.get("start_date", "2026-04-01")

    payload = {
        "employee_id": employee_id,
        "grade": grade,
        "location": location,
        "department": department,
        "start_date": str(start_date),
        "bank_account_ref": "BANK_REF_MASKED",
    }

    if ctx.gateway:
        return await ctx.gateway.call("payroll", "/payroll/employees/setup", payload, ctx.idempotency_key)

    headers = {"Idempotency-Key": ctx.idempotency_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{MOCK_BASE_URL}/payroll/employees/setup", json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return {
        "status": "setup_initiated",
        "payroll_id": f"PAY-{employee_id}",
        "employee_id": employee_id,
        "grade": grade,
        "pf_enrolled": True,
        "esic_applicable": grade in ("L1", "L2"),
        "idempotency_key": ctx.idempotency_key,
    }
