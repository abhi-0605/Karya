"""Unit tests for KaryaOS Core Workflow Engine, Skill Registry, and Audit Log."""
import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import Base
import app.models  # noqa: F401
from app.models.workflow import WorkflowRun, StepRun, ApprovalRequest, AuditLog, RunStatus, StepStatus
from core.engine.loader import load_workflow, load_all_workflows
from core.engine.skill_registry import load_all_skills, get_skill, reload_registry
from core.audit.logger import AuditLogger
from core.killswitch.killswitch import KillSwitch
from core.engine.state import WorkflowStateMachine


@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite async test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_load_onboarding_workflow():
    wf_path = Path(__file__).parent.parent / "extensions" / "workflows" / "onboarding.yaml"
    wf = load_workflow(wf_path)
    assert wf.id == "onboarding"
    assert wf.trigger == "employee.hired"
    assert len(wf.steps) == 8
    # Check dependencies
    email_step = next(s for s in wf.steps if s.id == "provision_email")
    assert "create_directory_account" in email_step.depends_on
    # Check approval mode
    comp_step = next(s for s in wf.steps if s.id == "confirm_compensation")
    assert comp_step.mode == "approval"
    assert comp_step.approver_role == "hrbp"


def test_skill_registry_discovery():
    skills = reload_registry()
    expected_skills = [
        "directory.create_account",
        "email.provision",
        "assets.allocate_laptop",
        "admin.issue_access_card",
        "payroll.setup_employee",
        "hr.confirm_compensation",
        "manager.assign_buddy",
        "comms.send_welcome",
    ]
    for name in expected_skills:
        assert name in skills, f"Missing skill {name}"
        skill = get_skill(name)
        assert skill is not None
        assert skill.manifest.name == name
        assert callable(skill.run)


@pytest.mark.asyncio
async def test_audit_hash_chain_integrity(db_session: AsyncSession):
    audit = AuditLogger(db_session)
    seq1 = await audit.log(
        actor_type="agent", actor_id="test_actor", action="step_1",
        reasoning="first step", outcome="ok"
    )
    seq2 = await audit.log(
        actor_type="agent", actor_id="test_actor", action="step_2",
        reasoning="second step", outcome="ok"
    )
    assert seq2 == seq1 + 1

    # Verify chain intact
    valid, broken_seq = await AuditLogger.verify_chain(db_session)
    assert valid is True
    assert broken_seq is None


@pytest.mark.asyncio
async def test_audit_hash_chain_tamper_detection(db_session: AsyncSession):
    from sqlalchemy import update
    audit = AuditLogger(db_session)
    await audit.log(actor_type="agent", actor_id="actor", action="action_1", outcome="orig")
    await audit.log(actor_type="agent", actor_id="actor", action="action_2", outcome="orig")

    # Tamper with row 1
    await db_session.execute(
        update(AuditLog).where(AuditLog.seq == 1).values(outcome="TAMPERED")
    )
    await db_session.commit()

    # Chain verification must FAIL
    valid, broken_seq = await AuditLogger.verify_chain(db_session)
    assert valid is False
    assert broken_seq == 1


@pytest.mark.asyncio
async def test_onboarding_workflow_execution(db_session: AsyncSession):
    """Test full execution of onboarding workflow: auto steps complete, reserved step creates ApprovalRequest."""
    wf_path = Path(__file__).parent.parent / "extensions" / "workflows" / "onboarding.yaml"
    wf = load_workflow(wf_path)

    # Insert test WorkflowRun record
    run_record = WorkflowRun(
        id="run-test-001",
        workflow_id=wf.id,
        version=wf.version,
        subject_id="EMP0001",
        trigger_event_id="evt-001",
        status=RunStatus.pending,
    )
    db_session.add(run_record)
    await db_session.commit()

    context = {
        "employee_id": "EMP0001",
        "first_name": "Arjun",
        "last_name": "Sharma",
        "legal_name": "Arjun Sharma",
        "grade": "L2",
        "location": "Bengaluru",
        "department": "Engineering",
        "role_title": "Associate Software Engineer",
    }

    state_machine = WorkflowStateMachine(
        definition=wf,
        run_id="run-test-001",
        subject_id="EMP0001",
        context=context,
        db=db_session,
    )

    result = await state_machine.run()
    # 7 auto steps should be completed
    assert "create_directory_account" in result["completed_steps"]
    assert "provision_email" in result["completed_steps"]
    assert "allocate_laptop" in result["completed_steps"]
    assert "issue_access_card" in result["completed_steps"]
    assert "setup_payroll" in result["completed_steps"]
    assert "assign_buddy" in result["completed_steps"]
    assert "welcome_message" in result["completed_steps"]

    # confirm_compensation is an approval step -> must be in awaiting_approval!
    assert "confirm_compensation" in result["awaiting_approval"]

    # Verify audit chain integrity
    valid, _ = await AuditLogger.verify_chain(db_session)
    assert valid is True


@pytest.mark.asyncio
async def test_reserved_action_blocked_in_auto_mode(db_session: AsyncSession):
    """Governance rule: if an action is reserved (e.g. compensation.confirm), it CANNOT run with mode='auto'."""
    from core.engine.models import WorkflowDefinition, StepDefinition
    from app.models.workflow import WorkflowRun, RunStatus

    illegal_wf = WorkflowDefinition(
        id="illegal_wf",
        version=1,
        trigger="test.trigger",
        inputs=["employee_id"],
        steps=[
            StepDefinition(
                id="illegal_step",
                skill="hr.confirm_compensation",
                action="compensation.confirm",
                mode="auto",  # VIOLATION: reserved action in auto mode
            )
        ],
    )

    db_session.add(WorkflowRun(
        id="run-illegal", workflow_id="illegal_wf", version=1,
        subject_id="EMP0001", trigger_event_id="evt-illegal", status=RunStatus.pending
    ))
    await db_session.commit()

    sm = WorkflowStateMachine(
        definition=illegal_wf,
        run_id="run-illegal",
        subject_id="EMP0001",
        context={"employee_id": "EMP0001"},
        db=db_session,
    )
    result = await sm.run()
    assert "illegal_step" in result["failed_steps"]
    assert result["status"] == RunStatus.failed


@pytest.mark.asyncio
async def test_killswitch_pauses_step(db_session: AsyncSession):
    """Governance rule: pausing a skill in killswitch immediately parks that step in human queue."""
    from core.engine.models import WorkflowDefinition, StepDefinition
    from app.models.workflow import WorkflowRun, RunStatus

    ks = KillSwitch(db_session)
    await ks.pause(scope="skill", name="directory.create_account", paused_by="hrbp_priya")

    wf = WorkflowDefinition(
        id="ks_test_wf",
        version=1,
        trigger="test.trigger",
        inputs=["employee_id"],
        steps=[
            StepDefinition(id="step_dir", skill="directory.create_account", mode="auto")
        ],
    )

    db_session.add(WorkflowRun(
        id="run-ks", workflow_id="ks_test_wf", version=1,
        subject_id="EMP0001", trigger_event_id="evt-ks", status=RunStatus.pending
    ))
    await db_session.commit()

    sm = WorkflowStateMachine(
        definition=wf,
        run_id="run-ks",
        subject_id="EMP0001",
        context={"employee_id": "EMP0001"},
        db=db_session,
        killswitch=ks,
    )
    result = await sm.run()
    assert "step_dir" in result["paused_steps"]
    assert result["status"] == RunStatus.paused

