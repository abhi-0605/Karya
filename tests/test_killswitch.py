"""
Test suite for Kill Switch and Human Queue lifecycle.
Maps to Hackathon Non-negotiable Rules 9 & 10:
'Kill switch: HR can pause an agent/workflow/skill from the UI, checked before every step.'
'Failures, low confidence and data conflicts go to a Human Queue with a context bundle.'
"""
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
from app.api.auth import create_token
from core.audit.logger import AuditLogger


@pytest_asyncio.fixture
async def app_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_killswitch_api_and_human_queue_lifecycle(app_client):
    client, session_factory = app_client

    # HR Head Auth Token
    hr_token = create_token({
        "sub": "hr_head1",
        "role": "hr_head",
        "person_id": "HRH001",
        "name": "Vikram Rao",
        "principal_type": "human",
    })
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # 1. HR pauses assets.allocate_laptop skill
    pause_resp = await client.post(
        "/api/admin/killswitch/skill/assets.allocate_laptop/pause",
        headers=hr_headers,
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    # Check status endpoint
    stat_resp = await client.get("/api/admin/killswitch/skill/assets.allocate_laptop/status")
    assert stat_resp.status_code == 200
    assert stat_resp.json()["paused"] is True

    # 2. Trigger an onboarding event while skill is paused
    event_payload = {
        "employee_id": "EMP5555",
        "legal_name": "Divya Deshmukh",
        "grade": "L2",
        "location": "Bengaluru",
        "department": "Engineering",
        "role_title": "Associate Software Engineer",
        "event_id": "evt-ks-test-1",
    }
    wf_resp = await client.post("/api/events/employee.hired", json=event_payload)
    assert wf_resp.status_code == 202
    data = wf_resp.json()

    # allocate_laptop MUST be in paused_steps!
    assert "allocate_laptop" in data["paused_steps"]

    # 3. Check Human Queue: should have an item for the paused step
    queue_resp = await client.get("/api/queue/", headers=hr_headers)
    assert queue_resp.status_code == 200
    items = queue_resp.json()
    assert len(items) >= 1
    item = next(i for i in items if i["step_id"] == "allocate_laptop")
    assert item["reason"] == "paused"
    assert "killswitch_active" in item["context_bundle"]["cause"]

    # 4. HR resolves the Human Queue item
    resolve_resp = await client.post(
        f"/api/queue/{item['id']}/resolve",
        json={"resolution": "Manual asset dispatch coordinated via IT helpdesk ticket #4412"},
        headers=hr_headers,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"

    # 5. HR resumes the skill via API
    resume_resp = await client.post(
        "/api/admin/killswitch/skill/assets.allocate_laptop/resume",
        headers=hr_headers,
    )
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "active"

    stat_after = await client.get("/api/admin/killswitch/skill/assets.allocate_laptop/status")
    assert stat_after.json()["paused"] is False

    # 6. Audit integrity verification
    async with session_factory() as db:
        valid, broken_seq = await AuditLogger.verify_chain(db)
        assert valid is True
        assert broken_seq is None
