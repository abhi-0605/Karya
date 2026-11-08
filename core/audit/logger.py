"""
Hash-chained audit log.
Every entry contains the SHA-256 hash of the previous entry, making tampering detectable.
This is an APPEND-ONLY log — no updates, no deletes.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

log = structlog.get_logger()

GENESIS_HASH = "0" * 64


def _compute_hash(entry: dict) -> str:
    """SHA-256 of canonical JSON representation of the entry."""
    canonical = json.dumps(entry, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditLogger:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_prev_hash(self) -> str:
        from app.models.workflow import AuditLog
        result = await self.db.execute(
            select(AuditLog.hash).order_by(AuditLog.seq.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row else GENESIS_HASH

    async def log(
        self,
        actor_type: str,
        actor_id: str,
        action: str,
        inputs_ref: Optional[str] = None,
        rule_or_prompt_version: Optional[str] = None,
        model: Optional[str] = None,
        reasoning: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> int:
        """Append a new audit entry and return its sequence number."""
        from app.models.workflow import AuditLog

        ts = datetime.now(timezone.utc).replace(microsecond=0)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        prev_hash = await self._get_prev_hash()

        entry_data = {
            "ts": ts_str,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "inputs_ref": inputs_ref,
            "rule_or_prompt_version": rule_or_prompt_version,
            "model": model,
            "reasoning": reasoning,
            "outcome": outcome,
            "prev_hash": prev_hash,
        }
        entry_hash = _compute_hash(entry_data)

        audit_entry = AuditLog(
            ts=ts,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            inputs_ref=inputs_ref,
            rule_or_prompt_version=rule_or_prompt_version,
            model=model,
            reasoning=reasoning,
            outcome=outcome,
            prev_hash=prev_hash,
            hash=entry_hash,
        )
        self.db.add(audit_entry)
        await self.db.commit()
        await self.db.refresh(audit_entry)

        log.info("Audit entry recorded", seq=audit_entry.seq, action=action, actor=actor_id)
        return audit_entry.seq

    @staticmethod
    async def verify_chain(db: AsyncSession) -> tuple[bool, Optional[int]]:
        """
        Verify the entire audit chain.
        Returns (True, None) if intact, (False, broken_at_seq) if tampered.
        """
        from app.models.workflow import AuditLog

        result = await db.execute(select(AuditLog).order_by(AuditLog.seq.asc()))
        entries = result.scalars().all()

        prev_hash = GENESIS_HASH
        for entry in entries:
            ts_str = entry.ts.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(entry.ts, "strftime") else str(entry.ts)
            entry_data = {
                "ts": ts_str,
                "actor_type": entry.actor_type,
                "actor_id": entry.actor_id,
                "action": entry.action,
                "inputs_ref": entry.inputs_ref,
                "rule_or_prompt_version": entry.rule_or_prompt_version,
                "model": entry.model,
                "reasoning": entry.reasoning,
                "outcome": entry.outcome,
                "prev_hash": entry.prev_hash,
            }
            expected_hash = _compute_hash(entry_data)
            if entry.hash != expected_hash:
                log.error("Audit hash mismatch", seq=entry.seq, expected=expected_hash, actual=entry.hash)
                return False, entry.seq
            if entry.prev_hash != prev_hash:
                log.error("Audit prev_hash link broken", seq=entry.seq, expected_prev=prev_hash, actual_prev=entry.prev_hash)
                return False, entry.seq
            prev_hash = entry.hash

        return True, None
