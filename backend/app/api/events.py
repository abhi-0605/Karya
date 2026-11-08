"""Events router — receives HR domain events and enqueues workflow runs."""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class EmployeeHiredPayload(BaseModel):
    employee_id: str
    name: str
    role: str
    department: str
    start_date: str
    manager_id: str | None = None


@router.post("/employee.hired", status_code=202)
async def employee_hired(payload: EmployeeHiredPayload) -> dict[str, Any]:
    """Stub: accepts an employee.hired event and returns a run ID placeholder."""
    return {
        "status": "accepted",
        "event": "employee.hired",
        "run_id": "run_placeholder",
        "employee_id": payload.employee_id,
    }
