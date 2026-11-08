"""Events router — receives HR domain events and executes workflow runs."""
import uuid
from typing import Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.workflow import WorkflowRun, RunStatus
from core.engine.loader import load_workflow
from core.engine.state import WorkflowStateMachine

router = APIRouter()

ONBOARDING_WF_PATH = Path(__file__).parent.parent.parent.parent / "extensions" / "workflows" / "onboarding.yaml"


class EmployeeHiredPayload(BaseModel):
    employee_id: str
    name: Optional[str] = None
    legal_name: Optional[str] = None
    grade: str = "L2"
    location: str = "Bengaluru"
    department: str = "Engineering"
    role_title: str = "Associate Software Engineer"
    start_date: str = "2026-04-01"
    manager_id: Optional[str] = "EMP0002"
    event_id: Optional[str] = None


@router.post("/employee.hired", status_code=202)
async def employee_hired(
    payload: EmployeeHiredPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Subscribes to employee.hired event.
    Deduplicates on trigger_event_id to ensure exactly-once execution.
    """
    event_id = payload.event_id or f"evt-{payload.employee_id}-hire"

    # 1. Deduplication check
    existing = await db.execute(
        select(WorkflowRun).where(WorkflowRun.trigger_event_id == event_id)
    )
    dup = existing.scalar_one_or_none()
    if dup:
        return {
            "status": "already_exists",
            "run_id": dup.id,
            "workflow_id": dup.workflow_id,
            "workflow_status": dup.status,
            "replayed": True,
        }

    # 2. Load workflow definition
    if not ONBOARDING_WF_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Onboarding workflow definition file not found",
        )
    wf_def = load_workflow(ONBOARDING_WF_PATH)

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    emp_name = payload.legal_name or payload.name or "New Hire"
    names = emp_name.split(maxsplit=1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""

    context = {
        "employee_id": payload.employee_id,
        "legal_name": emp_name,
        "first_name": first_name,
        "last_name": last_name,
        "grade": payload.grade,
        "location": payload.location,
        "department": payload.department,
        "role_title": payload.role_title,
        "start_date": payload.start_date,
        "manager_id": payload.manager_id,
    }

    # 3. Create initial WorkflowRun row
    run_record = WorkflowRun(
        id=run_id,
        workflow_id=wf_def.id,
        version=wf_def.version,
        subject_id=payload.employee_id,
        trigger_event_id=event_id,
        status=RunStatus.pending,
        context=context,
    )
    db.add(run_record)
    await db.commit()

    # 4. Execute workflow
    sm = WorkflowStateMachine(
        definition=wf_def,
        run_id=run_id,
        subject_id=payload.employee_id,
        context=context,
        db=db,
    )
    result = await sm.run()

    return {
        "status": "accepted",
        "run_id": run_id,
        "workflow_id": wf_def.id,
        "workflow_status": result["status"],
        "completed_steps": result["completed_steps"],
        "awaiting_approval": result["awaiting_approval"],
        "paused_steps": result["paused_steps"],
    }
