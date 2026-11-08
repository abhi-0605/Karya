"""
Tests for Hash-Chained Audit Log Integrity & Tamper-Evidence.
Enforces: Any mutation of historic records breaks the SHA-256 chain.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, delete

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import Base
import app.models  # noqa: F401
from app.models.workflow import AuditLog
from core.audit.logger import AuditLogger


@pytest_asyncio.fixture
async def audit_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_chain_valid_on_sequential_appends(audit_session: AsyncSession):
    """Multiple sequential log entries must form a cryptographically unbroken chain."""
    logger = AuditLogger(audit_session)

    seq1 = await logger.log("human", "hrbp001", "workflow.start", inputs_ref="ref1", outcome="ok")
    seq2 = await logger.log("agent", "it_agent", "laptop.allocate", inputs_ref="ref2", outcome="ok")
    seq3 = await logger.log("human", "finance", "compensation.confirm", inputs_ref="ref3", outcome="approved")

    assert seq1 == 1
    assert seq2 == 2
    assert seq3 == 3

    valid, broken_at = await AuditLogger.verify_chain(audit_session)
    assert valid is True
    assert broken_at is None


@pytest.mark.asyncio
async def test_audit_chain_detects_data_tampering(audit_session: AsyncSession):
    """Mutating any data field in a historic audit row must be detected immediately."""
    logger = AuditLogger(audit_session)

    await logger.log("human", "hrbp001", "workflow.start", inputs_ref="ref1", outcome="ok")
    seq2 = await logger.log("agent", "it_agent", "laptop.allocate", inputs_ref="ref2", outcome="ok")
    await logger.log("human", "finance", "compensation.confirm", inputs_ref="ref3", outcome="approved")

    # Attacker tampers with row seq=2 (changes outcome from 'ok' to 'failed')
    await audit_session.execute(
        update(AuditLog).where(AuditLog.seq == seq2).values(outcome="tampered_outcome")
    )
    await audit_session.commit()

    valid, broken_at = await AuditLogger.verify_chain(audit_session)
    assert valid is False
    assert broken_at == 2, f"Expected chain to break at sequence 2, broke at {broken_at}"


@pytest.mark.asyncio
async def test_audit_chain_detects_row_deletion(audit_session: AsyncSession):
    """Deleting a row from the middle must break the prev_hash link."""
    logger = AuditLogger(audit_session)

    await logger.log("human", "hrbp001", "workflow.start")
    seq2 = await logger.log("agent", "it_agent", "laptop.allocate")
    await logger.log("human", "finance", "compensation.confirm")

    # Attacker deletes row 2 entirely
    await audit_session.execute(delete(AuditLog).where(AuditLog.seq == seq2))
    await audit_session.commit()

    valid, broken_at = await AuditLogger.verify_chain(audit_session)
    assert valid is False
    # Row 3 will have prev_hash pointing to row 2's hash, but row 1 is now previous in sequence
    assert broken_at == 3
