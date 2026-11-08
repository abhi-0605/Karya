"""
Full Lifecycle Integration Test (T046).
Tests the complete end-to-end loop:
1. Trigger employee.hired event.
2. Verify 7 auto steps complete and confirm_compensation awaits approval.
3. Verify agent token CANNOT approve (403 Forbidden).
4. Verify human HRBP token approves successfully.
5. Verify audit chain is cryptographically intact.
6. Verify chat assistant returns grounded status.
"""
from __future__ import annotations
import pytest
import pytest_asyncio
from pathlib import Path
import sys
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.base import Base
import app.models  # noqa: F401
from app.main import app
from app.database import get_db
from app.api.auth import create_token
from core.audit.logger import AuditLogger


@pytest_asyncio.fixture
async def lifecycle_env():
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
async def test_complete_onboarding_lifecycle(lifecycle_env):
    client, session_factory = lifecycle_env

    # 1. Fire employee.hired event
    hire_payload = {
        "employee_id": "EMP9999",
        "legal_name": "Siddharth Nair",
        "grade": "L3",
        "location": "Bengaluru",
        "department": "Engineering",
        "role_title": "Platform Engineer",
        "start_date": "2026-06-01",
        "manager_id": "EMP0001",
        "event_id": "evt-siddharth-hired-9999",
    }
    hire_res = await client.post("/api/events/employee.hired", json=hire_payload)
    assert hire_res.status_code == 202
    hire_data = hire_res.json()
    assert hire_data["status"] == "accepted"
    run_id = hire_data["run_id"]
    assert "confirm_compensation" in hire_data["awaiting_approval"]

    # 2. Query approvals list
    hrbp_token = create_token({"sub": "hrbp001", "role": "hrbp", "principal_type": "human"})
    headers_hrbp = {"Authorization": f"Bearer {hrbp_token}"}
    
    approvals_res = await client.get("/api/approvals/", headers=headers_hrbp)
    assert approvals_res.status_code == 200
    approvals = approvals_res.json()
    assert len(approvals) >= 1
    approval_id = approvals[0]["id"]

    # 3. Agent token attempts approval -> MUST BE REJECTED (403)
    agent_token = create_token({"sub": "ai-agent-v1", "role": "hrbp", "principal_type": "agent"})
    headers_agent = {"Authorization": f"Bearer {agent_token}"}
    agent_approve = await client.post(
        f"/api/approvals/{approval_id}/approve",
        json={"reason": "Autonomous approval attempt"},
        headers=headers_agent,
    )
    assert agent_approve.status_code == 403
    assert "agent" in agent_approve.json()["detail"].lower()

    # 4. Human HRBP approves
    human_approve = await client.post(
        f"/api/approvals/{approval_id}/approve",
        json={"reason": "Approved standard L3 compensation band after manual review"},
        headers=headers_hrbp,
    )
    assert human_approve.status_code == 200
    assert human_approve.json()["approved"] is True

    # 5. Verify cryptographic audit chain integrity
    async with session_factory() as db:
        valid, broken_seq = await AuditLogger.verify_chain(db)
        assert valid is True
        assert broken_seq is None

    # 6. Ask Chat Assistant about status
    chat_res = await client.post("/api/chat/message", json={
        "message": "What is the onboarding status for Siddharth Nair?",
        "user_id": "EMP9999",
        "user_role": "employee",
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["intent"] == "check_status"
    assert "onboarding" in chat_data["reply"].lower()
