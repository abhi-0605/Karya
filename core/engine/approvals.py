"""
Approval service — manages ApprovalRequest lifecycle.
Enforces that agent tokens CAN NEVER call the approve endpoint.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

log = structlog.get_logger()


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(
        self,
        run_id: str,
        step_id: str,
        action: str,
        approver_role: str,
        context_bundle: dict,
        approver_person_id: Optional[str] = None,
    ) -> str:
        from app.models.workflow import ApprovalRequest

        req_id = str(uuid.uuid4())[:8]
        req = ApprovalRequest(
            id=req_id,
            run_id=run_id,
            step_id=step_id,
            action=action,
            approver_role=approver_role,
            approver_person_id=approver_person_id,
            context_bundle=context_bundle,
        )
        self.db.add(req)
        await self.db.commit()
        log.info("Approval request created", id=req_id, action=action, role=approver_role)
        return req_id

    async def approve(
        self,
        request_id: str,
        approver_person_id: str,
        approver_role: str,
        principal_type: str,
        reason: Optional[str] = None,
    ) -> dict:
        """
        Approve an action.
        CRITICAL GOVERNANCE RULE: principal_type MUST be 'human'. Agent tokens are rejected.
        """
        if principal_type != "human":
            raise PermissionError("Agent tokens cannot approve reserved decisions. A named human must approve.")

        from app.models.workflow import ApprovalRequest

        result = await self.db.execute(select(ApprovalRequest).where(ApprovalRequest.id == request_id))
        req = result.scalar_one_or_none()
        if not req:
            raise ValueError(f"ApprovalRequest {request_id} not found")
        if req.decision:
            raise ValueError(f"ApprovalRequest {request_id} already decided: {req.decision}")

        await self.db.execute(
            update(ApprovalRequest)
            .where(ApprovalRequest.id == request_id)
            .values(
                decision="approved",
                decided_at=datetime.now(timezone.utc),
                approver_person_id=approver_person_id,
                reason=reason,
            )
        )
        await self.db.commit()
        log.info("Approval granted", id=request_id, by=approver_person_id)
        return {"approved": True, "request_id": request_id}

    async def reject(
        self,
        request_id: str,
        approver_person_id: str,
        principal_type: str,
        reason: Optional[str] = None,
    ) -> dict:
        if principal_type != "human":
            raise PermissionError("Agent tokens cannot reject decisions. A named human must decide.")

        from app.models.workflow import ApprovalRequest

        await self.db.execute(
            update(ApprovalRequest)
            .where(ApprovalRequest.id == request_id)
            .values(
                decision="rejected",
                decided_at=datetime.now(timezone.utc),
                approver_person_id=approver_person_id,
                reason=reason,
            )
        )
        await self.db.commit()
        log.info("Approval rejected", id=request_id, by=approver_person_id)
        return {"approved": False, "request_id": request_id}
