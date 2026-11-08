"""
Human Queue Router — endpoints for viewing and resolving items in the Human Queue.
Items land here when:
- An external integration fails after retries / circuit breaker opens
- Agent confidence is below threshold (< 0.75)
- Data conflict is detected
- An agent or skill is paused by HR via the kill switch
"""
from typing import Annotated, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user
from app.database import get_db
from app.models.workflow import HumanQueueItem
from core.engine.human_queue import HumanQueue
from core.audit.logger import AuditLogger

router = APIRouter()


class ResolvePayload(BaseModel):
    resolution: str


@router.get("/")
async def list_queue_items(
    status_filter: Optional[str] = "open",
    user: Annotated[dict, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List Human Queue items. status_filter: 'open' | 'resolved' | 'all'."""
    stmt = select(HumanQueueItem).order_by(HumanQueueItem.created_at.desc())
    if status_filter == "open":
        stmt = stmt.where(HumanQueueItem.resolved_at.is_(None))
    elif status_filter == "resolved":
        stmt = stmt.where(HumanQueueItem.resolved_at.is_not(None))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": item.id,
            "run_id": item.run_id,
            "step_id": item.step_id,
            "reason": item.reason,
            "context_bundle": item.context_bundle,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
            "resolved_by": item.resolved_by,
            "resolution": item.resolution,
        }
        for item in items
    ]


@router.get("/{item_id}")
async def get_queue_item(
    item_id: str,
    user: Annotated[dict, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full context bundle and error details for a human queue item."""
    result = await db.execute(
        select(HumanQueueItem).where(HumanQueueItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="HumanQueueItem not found")

    return {
        "id": item.id,
        "run_id": item.run_id,
        "step_id": item.step_id,
        "reason": item.reason,
        "context_bundle": item.context_bundle,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        "resolved_by": item.resolved_by,
        "resolution": item.resolution,
    }


@router.post("/{item_id}/resolve")
async def resolve_queue_item(
    item_id: str,
    payload: ResolvePayload,
    user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Resolve a human queue item. Records human resolver and logs to audit chain."""
    queue = HumanQueue(db)
    audit = AuditLogger(db)

    # Verify item exists
    result = await db.execute(
        select(HumanQueueItem).where(HumanQueueItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="HumanQueueItem not found")

    resolver = user.get("sub", "UNKNOWN")
    await queue.resolve(item_id=item_id, resolved_by=resolver, resolution=payload.resolution)

    await audit.log(
        actor_type="human",
        actor_id=resolver,
        action=f"human_queue_resolved:{item_id}",
        reasoning=payload.resolution,
        outcome=f"Item {item_id} marked resolved by {resolver}",
    )

    return {
        "id": item_id,
        "status": "resolved",
        "resolved_by": resolver,
        "resolution": payload.resolution,
    }
