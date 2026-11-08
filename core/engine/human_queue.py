"""
Human Queue — receives items when a step fails, has low confidence, data conflict, or is paused.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

log = structlog.get_logger()


class HumanQueue:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def enqueue(
        self,
        run_id: str,
        step_id: Optional[str],
        reason: str,
        context: dict,
    ) -> str:
        """Create a human queue item and return its ID."""
        from app.models.workflow import HumanQueueItem

        item_id = str(uuid.uuid4())[:8]
        item = HumanQueueItem(
            id=item_id,
            run_id=run_id,
            step_id=step_id,
            reason=reason,
            context_bundle=context,
        )
        self.db.add(item)
        await self.db.commit()
        log.info("Human queue item created", id=item_id, reason=reason, run_id=run_id)
        return item_id

    async def resolve(self, item_id: str, resolved_by: str, resolution: str) -> None:
        """Mark a human queue item as resolved."""
        from app.models.workflow import HumanQueueItem
        await self.db.execute(
            update(HumanQueueItem)
            .where(HumanQueueItem.id == item_id)
            .values(
                resolved_at=datetime.now(timezone.utc),
                resolved_by=resolved_by,
                resolution=resolution,
            )
        )
        await self.db.commit()
        log.info("Human queue item resolved", id=item_id, by=resolved_by)

    async def list_open(self) -> list:
        from app.models.workflow import HumanQueueItem
        result = await self.db.execute(
            select(HumanQueueItem).where(HumanQueueItem.resolved_at.is_(None))
        )
        return result.scalars().all()
