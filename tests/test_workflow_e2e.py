"""End-to-end integration test: event -> workflow execution -> audit log."""
import pytest
import pytest_asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import Base
import app.models  # noqa: F401
from app.main import app
from app.database import get_db
from core.audit.logger import AuditLogger


@pytest_asyncio.fixture
async def test_app():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_employee_hired_event_triggers_onboarding(test_app):
    client, session_factory = test_app

    payload = {
        "employee_id": "EMP0101",
        "legal_name": "Rohan Gupta",
        "grade": "L3",
        "location": "Bengaluru",
        "department": "Engineering",
        "role_title": "Senior Software Engineer",
        "start_date": "2026-05-01",
        "manager_id": "EMP0001",
        "event_id": "evt-rohan-hired-001",
    }

    response = await client.post("/api/events/employee.hired", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["workflow_id"] == "onboarding"
    assert "create_directory_account" in data["completed_steps"]
    assert "allocate_laptop" in data["completed_steps"]
    assert "confirm_compensation" in data["awaiting_approval"]

    # Deduplication test: re-sending the same event returns replayed
    dup_response = await client.post("/api/events/employee.hired", json=payload)
    assert dup_response.status_code == 202
    dup_data = dup_response.json()
    assert dup_data["status"] == "already_exists"
    assert dup_data["run_id"] == data["run_id"]
    assert dup_data["replayed"] is True

    # Verify audit chain integrity
    async with session_factory() as db:
        valid, broken_seq = await AuditLogger.verify_chain(db)
        assert valid is True
        assert broken_seq is None
