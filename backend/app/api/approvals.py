"""Approvals router — human approval endpoints.

Agent tokens (principal_type == 'agent') are NEVER allowed to approve.
Only human principals may call POST /{id}/approve or POST /{id}/reject.
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user

router = APIRouter()


def _require_human(user: dict) -> dict:
    """Dependency that blocks agent tokens from approving decisions."""
    if user.get("principal_type") != "human":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approval actions are reserved for human principals.",
        )
    return user


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Stub: approve a pending decision. Agents are blocked."""
    _require_human(user)
    return {"approval_id": approval_id, "status": "approved", "approver": user.get("sub")}


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Stub: reject a pending decision. Agents are blocked."""
    _require_human(user)
    return {"approval_id": approval_id, "status": "rejected", "approver": user.get("sub")}
