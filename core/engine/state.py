"""
Workflow State Machine and Runner.
Executes WorkflowDefinition steps in dependency order (parallel where possible).
Checks kill switch before every step, enforces reserved decisions, logs to audit chain.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
import yaml

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from core.engine.models import WorkflowDefinition, StepDefinition
from core.engine.skill_registry import get_skill
from core.audit.logger import AuditLogger
from core.killswitch.killswitch import KillSwitch
from core.engine.human_queue import HumanQueue
from core.engine.approvals import ApprovalService

log = structlog.get_logger()

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_idempotency_key(run_id: str, step_id: str, payload: dict) -> str:
    """Canonical idempotency key: sha256(run_id + step_id + sorted_payload)."""
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    raw = f"{run_id}:{step_id}:{payload_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_reserved_actions() -> list[str]:
    """Load list of reserved actions from config/reserved_decisions.yaml."""
    reserved_file = CONFIG_DIR / "reserved_decisions.yaml"
    if not reserved_file.exists():
        return []
    data = yaml.safe_load(reserved_file.read_text(encoding="utf-8"))
    actions = []
    for item in data.get("reserved", []):
        act = item.get("action", "")
        # Can be pipe-delimited e.g. complaint.posh|grievance|whistleblower
        for sub in act.split("|"):
            actions.append(sub.strip())
    return actions


class SkillContext:
    """Passed to every skill.run(ctx, inputs)."""
    def __init__(
        self,
        run_id: str,
        step_id: str,
        subject_id: str,
        idempotency_key: str,
        db: AsyncSession,
        gateway: Any = None,
        context: Optional[dict] = None,
    ):
        self.run_id = run_id
        self.step_id = step_id
        self.subject_id = subject_id
        self.idempotency_key = idempotency_key
        self.db = db
        self.gateway = gateway
        self.context = context or {}


class WorkflowStateMachine:
    def __init__(
        self,
        definition: WorkflowDefinition,
        run_id: str,
        subject_id: str,
        context: dict,
        db: AsyncSession,
        audit: Optional[AuditLogger] = None,
        killswitch: Optional[KillSwitch] = None,
        human_queue: Optional[HumanQueue] = None,
        approvals: Optional[ApprovalService] = None,
        gateway: Any = None,
    ):
        self.definition = definition
        self.run_id = run_id
        self.subject_id = subject_id
        self.context = context.copy()
        self.db = db
        self.audit = audit or AuditLogger(db)
        self.killswitch = killswitch or KillSwitch(db)
        self.human_queue = human_queue or HumanQueue(db)
        self.approvals = approvals or ApprovalService(db)
        self.gateway = gateway
        self.reserved_actions = load_reserved_actions()
        self._db_lock = asyncio.Lock()

        self._completed: set[str] = set()
        self._failed: set[str] = set()
        self._paused: set[str] = set()
        self._awaiting_approval: set[str] = set()

    def is_action_reserved(self, action: str) -> bool:
        """Check if an action is in the reserved decisions list."""
        for r in self.reserved_actions:
            if action == r or action.startswith(r.rstrip("*")):
                return True
        return False

    async def _check_killswitch(self, step: StepDefinition) -> bool:
        """Check if workflow or skill is paused by HR."""
        keys = [
            f"workflow:{self.definition.id}",
            f"skill:{step.skill}",
        ]
        for k in keys:
            if await self.killswitch.is_paused(k):
                return True
        return False

    async def _get_ready_steps(self, remaining: list[StepDefinition]) -> list[StepDefinition]:
        """Return steps whose dependencies have completed."""
        ready = []
        for step in remaining:
            if all(dep in self._completed for dep in step.depends_on):
                ready.append(step)
        return ready

    async def run(self) -> dict:
        """Execute the workflow graph to completion or human pause."""
        from app.models.workflow import WorkflowRun, StepRun, RunStatus, StepStatus

        log.info("Starting workflow run", run_id=self.run_id, workflow_id=self.definition.id)

        # Ensure WorkflowRun record exists and is set to running
        async with self._db_lock:
            res = await self.db.execute(select(WorkflowRun).where(WorkflowRun.id == self.run_id))
            wf_record = res.scalar_one_or_none()
            if wf_record:
                await self.db.execute(
                    update(WorkflowRun)
                    .where(WorkflowRun.id == self.run_id)
                    .values(status=RunStatus.running, started_at=_utcnow())
                )
                await self.db.commit()

        remaining = list(self.definition.steps)

        # BFS execution: run independent steps in parallel
        while remaining:
            ready = await self._get_ready_steps(remaining)
            if not ready:
                # Deadlock check
                log.warning("Workflow has unresolvable dependencies or blocked steps", remaining=[s.id for s in remaining])
                break

            tasks = [self._execute_step(step) for step in ready]
            await asyncio.gather(*tasks, return_exceptions=True)

            ready_ids = {s.id for s in ready}
            remaining = [s for s in remaining if s.id not in ready_ids]

        # Final workflow status
        final_status = RunStatus.completed
        if self._failed:
            final_status = RunStatus.failed
        elif self._awaiting_approval or self._paused:
            final_status = RunStatus.paused

        async with self._db_lock:
            await self.db.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == self.run_id)
                .values(status=final_status, ended_at=_utcnow(), context=self.context)
            )
            await self.db.commit()

        log.info(
            "Workflow run finished",
            run_id=self.run_id,
            status=final_status,
            completed=len(self._completed),
            failed=len(self._failed),
        )
        return {
            "run_id": self.run_id,
            "status": final_status,
            "completed_steps": list(self._completed),
            "failed_steps": list(self._failed),
            "awaiting_approval": list(self._awaiting_approval),
            "paused_steps": list(self._paused),
        }

    async def _execute_step(self, step: StepDefinition):
        """Execute a single step: kill switch -> reserved check -> execute -> audit."""
        from app.models.workflow import StepRun, StepStatus

        step_run_id = f"{self.run_id}:{step.id}"
        idem_key = make_idempotency_key(self.run_id, step.id, self.context)

        # 1. Kill Switch Check
        if await self._check_killswitch(step):
            log.warning("Step blocked by kill switch", step=step.id, skill=step.skill)
            self._paused.add(step.id)
            await self._record_step(step, step_run_id, idem_key, StepStatus.paused, error="Paused by kill switch")
            await self.human_queue.enqueue(
                run_id=self.run_id,
                step_id=step.id,
                reason="paused",
                context={"step_id": step.id, "skill": step.skill, "cause": "killswitch_active"},
            )
            return

        # 2. Reserved Decisions Enforcement (Load-time & Runtime check)
        action = step.action or step.skill
        if self.is_action_reserved(action) and step.mode == "auto":
            err = f"Reserved action '{action}' cannot run in mode='auto'. Requires human approval."
            log.error("Governance violation: reserved action in auto mode", action=action, step=step.id)
            self._failed.add(step.id)
            await self._record_step(step, step_run_id, idem_key, StepStatus.failed, error=err)
            await self.human_queue.enqueue(
                run_id=self.run_id,
                step_id=step.id,
                reason="reserved_decision_violation",
                context={"step_id": step.id, "action": action, "error": err},
            )
            return

        # 3. Handle Approval Step
        if step.mode in ("approval", "route_only"):
            log.info("Step requires human approval", step=step.id, action=action)
            self._awaiting_approval.add(step.id)
            await self._record_step(step, step_run_id, idem_key, StepStatus.awaiting_approval)
            async with self._db_lock:
                req_id = await self.approvals.create_request(
                    run_id=self.run_id,
                    step_id=step.id,
                    action=action,
                    approver_role=step.approver_role or "hrbp",
                    context_bundle=self.context,
                )
                await self.audit.log(
                    actor_type="agent",
                    actor_id=f"workflow:{self.definition.id}",
                    action=f"approval_requested:{step.id}",
                    inputs_ref=step_run_id,
                    reasoning=f"Step {step.id} has mode={step.mode}; routed to {step.approver_role}",
                    outcome=f"ApprovalRequest:{req_id}",
                )
            return

        # 4. Auto Skill Execution
        await self._record_step(step, step_run_id, idem_key, StepStatus.running)
        skill = get_skill(step.skill)
        if not skill:
            err = f"Skill not found in registry: {step.skill}"
            log.error(err)
            self._failed.add(step.id)
            await self._record_step(step, step_run_id, idem_key, StepStatus.failed, error=err)
            if step.on_failure == "human_queue":
                await self.human_queue.enqueue(
                    run_id=self.run_id, step_id=step.id, reason="failure",
                    context={"error": err, "step_id": step.id}
                )
            return

        skill_ctx = SkillContext(
            run_id=self.run_id,
            step_id=step.id,
            subject_id=self.subject_id,
            idempotency_key=idem_key,
            db=self.db,
            gateway=self.gateway,
            context=self.context,
        )

        try:
            outputs = await skill.run(skill_ctx, self.context)
            self.context[step.id] = outputs or {}
            self._completed.add(step.id)
            await self._record_step(
                step, step_run_id, idem_key, StepStatus.completed,
                outputs=outputs, human_touch=False
            )
            async with self._db_lock:
                await self.audit.log(
                    actor_type="agent",
                    actor_id=f"skill:{step.skill}",
                    action=step.id,
                    inputs_ref=step_run_id,
                    rule_or_prompt_version=f"{self.definition.id}@{self.definition.version}",
                    reasoning=f"Auto skill execution: {step.skill}",
                    outcome=str(outputs)[:400] if outputs else "success",
                )
        except Exception as e:
            log.error("Skill execution failed", skill=step.skill, error=str(e))
            self._failed.add(step.id)
            await self._record_step(step, step_run_id, idem_key, StepStatus.failed, error=str(e))
            if step.on_failure == "human_queue":
                await self.human_queue.enqueue(
                    run_id=self.run_id,
                    step_id=step.id,
                    reason="failure",
                    context={"error": str(e), "step_id": step.id, "skill": step.skill},
                )

    async def _record_step(
        self,
        step: StepDefinition,
        step_run_id: str,
        idem_key: str,
        status: Any,
        inputs: Optional[dict] = None,
        outputs: Optional[dict] = None,
        error: Optional[str] = None,
        human_touch: bool = False,
    ):
        """Create or update StepRun database record."""
        from app.models.workflow import StepRun

        now = _utcnow()
        async with self._db_lock:
            res = await self.db.execute(select(StepRun).where(StepRun.id == step_run_id))
            record = res.scalar_one_or_none()

            if not record:
                record = StepRun(
                    id=step_run_id,
                    run_id=self.run_id,
                    step_id=step.id,
                    mode=step.mode,
                    status=status,
                    human_touch=human_touch,
                    idempotency_key=idem_key,
                    attempts=1,
                    skill_id=step.skill,
                    inputs=inputs or self.context,
                    outputs=outputs,
                    error=error,
                    started_at=now if status.value == "running" else None,
                )
                self.db.add(record)
            else:
                record.status = status
                record.attempts += 1
                if outputs:
                    record.outputs = outputs
                if error:
                    record.error = error
                if status.value in ("completed", "failed", "paused", "awaiting_approval"):
                    record.ended_at = now

            await self.db.commit()
