"""
Approvals router — human approval endpoints for reserved decisions.

NON-NEGOTIABLE GOVERNANCE RULE:
Agent tokens (principal_type == 'agent') are NEVER allowed to approve.
Only human principals with appropriate roles may approve or reject.
"""
from typing import Annotated, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user
from app.database import get_db
from app.models.workflow import ApprovalRequest
from core.engine.approvals import ApprovalService
from core.audit.logger import AuditLogger

router = APIRouter()


class DecisionPayload(BaseModel):
    reason: Optional[str] = None


def _require_human(user: dict) -> dict:
    """Dependency that blocks agent tokens from approving decisions."""
    principal_type = user.get("principal_type", "")
    if principal_type != "human":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approval actions are reserved for human principals. Agent tokens cannot call this endpoint.",
        )
    return user


@router.get("/")
async def list_pending_approvals(
    user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List pending approval requests."""
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.decision.is_(None))
    )
    reqs = result.scalars().all()
    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "step_id": r.step_id,
            "action": r.action,
            "approver_role": r.approver_role,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "context_bundle": r.context_bundle,
        }
        for r in reqs
    ]


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full details and context bundle for a pending approval."""
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="ApprovalRequest not found")
    return {
        "id": req.id,
        "run_id": req.run_id,
        "step_id": req.step_id,
        "action": req.action,
        "approver_role": req.approver_role,
        "approver_person_id": req.approver_person_id,
        "decision": req.decision,
        "decided_at": req.decided_at.isoformat() if req.decided_at else None,
        "reason": req.reason,
        "context_bundle": req.context_bundle,
    }


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    payload: Optional[DecisionPayload] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Approve a reserved decision.
    CRITICAL: Agent tokens are strictly forbidden.
    """
    _require_human(user)
    service = ApprovalService(db)
    audit = AuditLogger(db)

    try:
        result = await service.approve(
            request_id=approval_id,
            approver_person_id=user.get("person_id", user.get("sub", "UNKNOWN")),
            approver_role=user.get("role", "hrbp"),
            principal_type=user.get("principal_type", "human"),
            reason=payload.reason if payload else None,
        )
        await audit.log(
            actor_type="human",
            actor_id=user.get("sub", "UNKNOWN"),
            action=f"approval_granted:{approval_id}",
            reasoning=payload.reason if payload else "Approved by human user",
            outcome="approved",
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    user: Annotated[dict, Depends(get_current_user)],
    payload: Optional[DecisionPayload] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Reject a reserved decision.
    CRITICAL: Agent tokens are strictly forbidden.
    """
    _require_human(user)
    service = ApprovalService(db)
    audit = AuditLogger(db)

    try:
        result = await service.reject(
            request_id=approval_id,
            approver_person_id=user.get("person_id", user.get("sub", "UNKNOWN")),
            principal_type=user.get("principal_type", "human"),
            reason=payload.reason if payload else None,
        )
        await audit.log(
            actor_type="human",
            actor_id=user.get("sub", "UNKNOWN"),
            action=f"approval_rejected:{approval_id}",
            reasoning=payload.reason if payload else "Rejected by human user",
            outcome="rejected",
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
