"""
Kill switch — per-agent/workflow/skill flag checked before every step.
Cached for <= 1s.
"""
from __future__ import annotations
import time
from typing import Optional
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

log = structlog.get_logger()

CACHE_TTL_S = 1.0


class KillSwitch:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self._cache: dict[str, tuple[bool, float]] = {}

    async def is_paused(self, key: str) -> bool:
        """
        Check if a workflow, skill, or agent is paused.
        key: 'workflow:onboarding' | 'skill:assets.allocate_laptop' | 'agent:it'
        """
        now = time.monotonic()
        if key in self._cache:
            paused, expires_at = self._cache[key]
            if now < expires_at:
                return paused

        paused = await self._query_db(key)
        self._cache[key] = (paused, now + CACHE_TTL_S)
        return paused

    async def _query_db(self, key: str) -> bool:
        from app.models.workflow import Flag
        try:
            result = await self.db.execute(select(Flag).where(Flag.id == key))
            flag = result.scalar_one_or_none()
            return flag.paused if flag else False
        except Exception as e:
            log.warning("Killswitch DB query error, defaulting to False", error=str(e))
            return False

    async def pause(self, scope: str, name: str, paused_by: str) -> None:
        """Pause a workflow, skill, or agent."""
        from app.models.workflow import Flag
        key = f"{scope}:{name}"
        now = datetime.now(timezone.utc)

        result = await self.db.execute(select(Flag).where(Flag.id == key))
        flag = result.scalar_one_or_none()

        if flag:
            await self.db.execute(
                update(Flag).where(Flag.id == key).values(
                    paused=True, paused_by=paused_by, paused_at=now
                )
            )
        else:
            self.db.add(Flag(
                id=key, scope=scope, name=name,
                paused=True, paused_by=paused_by, paused_at=now
            ))
        await self.db.commit()

        self._cache.pop(key, None)
        if self.redis:
            try:
                await self.redis.publish("killswitch:invalidate", key)
            except Exception:
                pass
        log.info("Kill switch activated", scope=scope, name=name, by=paused_by)

    async def resume(self, scope: str, name: str, resumed_by: str) -> None:
        """Resume a paused workflow, skill, or agent."""
        from app.models.workflow import Flag
        key = f"{scope}:{name}"

        await self.db.execute(
            update(Flag).where(Flag.id == key).values(paused=False, paused_by=resumed_by)
        )
        await self.db.commit()

        self._cache.pop(key, None)
        if self.redis:
            try:
                await self.redis.publish("killswitch:invalidate", key)
            except Exception:
                pass
        log.info("Kill switch deactivated", scope=scope, name=name, by=resumed_by)
