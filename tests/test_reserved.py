"""
Tests for Reserved Decisions, Approval Service, Load-time Validation, and RBAC.
Maps to Hackathon Non-negotiable Rules 4 & 5.
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
from app.models.workflow import ApprovalRequest, WorkflowRun, RunStatus
from app.main import app
from app.database import get_db
from app.api.auth import create_token
from core.engine.models import WorkflowDefinition, StepDefinition
from core.engine.validator import validate_workflow, WorkflowValidationError
from core.engine.approvals import ApprovalService
from core.rbac.engine import RBACEngine


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


def test_validator_blocks_reserved_action_in_auto_mode():
    """Load-time validation: a reserved step cannot have mode='auto'."""
    invalid_wf = WorkflowDefinition(
        id="invalid_resignation",
        version=1,
        trigger="employee.resigned",
        inputs=["employee_id"],
        steps=[
            StepDefinition(
                id="auto_accept_resignation",
                skill="hr.accept_resignation",
                action="resignation.accept",
                mode="auto",  # VIOLATION
            )
        ],
    )
    with pytest.raises(WorkflowValidationError) as exc:
        validate_workflow(invalid_wf, validate_skills=False)
    assert "reserved action 'resignation.accept' but mode is set to 'auto'" in str(exc.value)


def test_validator_passes_valid_workflow():
    from core.engine.loader import load_workflow
    wf_path = Path(__file__).parent.parent / "extensions" / "workflows" / "onboarding.yaml"
    wf = load_workflow(wf_path)
    warnings = validate_workflow(wf, validate_skills=True)
    assert len(warnings) == 0


@pytest.mark.asyncio
async def test_agent_token_cannot_call_approve_endpoint(app_client):
    """
    CRITICAL GOVERNANCE RULE:
    An agent token (principal_type='agent') can NEVER approve a reserved decision.
    Must return 403 Forbidden.
    """
    client, session_factory = app_client

    # 1. Create a pending ApprovalRequest in DB
    async with session_factory() as db:
        service = ApprovalService(db)
        req_id = await service.create_request(
            run_id="run-test",
            step_id="confirm_comp",
            action="compensation.confirm",
            approver_role="hrbp",
            context_bundle={"employee_id": "EMP123"},
        )

    # 2. Forge an AGENT token
    agent_token = create_token({
        "sub": "agent:workflow_runner",
        "role": "hrbp",
        "principal_type": "agent",  # AGENT
    })

    # 3. Call approve endpoint as agent -> MUST BE REJECTED 403
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    resp = await client.post(f"/api/approvals/{req_id}/approve", json={"reason": "Auto"}, headers=agent_headers)
    assert resp.status_code == 403
    assert "reserved for human principals" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_human_hrbp_can_approve(app_client):
    """A human user with HRBP role can approve the reserved decision."""
    client, session_factory = app_client

    async with session_factory() as db:
        service = ApprovalService(db)
        req_id = await service.create_request(
            run_id="run-test-2",
            step_id="confirm_comp",
            action="compensation.confirm",
            approver_role="hrbp",
            context_bundle={"employee_id": "EMP123"},
        )

    # Human HRBP token
    human_token = create_token({
        "sub": "hrbp1",
        "role": "hrbp",
        "person_id": "HRB001",
        "name": "Deepa Menon",
        "principal_type": "human",
    })

    headers = {"Authorization": f"Bearer {human_token}"}
    resp = await client.post(f"/api/approvals/{req_id}/approve", json={"reason": "Salary band verified"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["approved"] is True


def test_rbac_delegation_rule():
    """Agent effective permissions are the intersection of skill declaration and acting user role."""
    # Employee acting user has no asset:allocate permission
    eff_emp = RBACEngine.compute_effective_agent_permissions(
        acting_user_role="employee",
        skill_declared_permissions=["asset:allocate", "profile:read_own"],
    )
    assert "asset:allocate" not in eff_emp
    assert "profile:read_own" in eff_emp

    # IT Ops user has asset:allocate
    eff_it = RBACEngine.compute_effective_agent_permissions(
        acting_user_role="it_ops",
        skill_declared_permissions=["asset:allocate", "directory:create"],
    )
    assert "asset:allocate" in eff_it
    assert "directory:create" in eff_it

    # Assert unauthorized raises PermissionError
    with pytest.raises(PermissionError):
        RBACEngine.assert_agent_authorized("employee", "asset:allocate")
