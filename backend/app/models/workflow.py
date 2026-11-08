"""Workflow run, step run, approval, human queue, and audit models."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Text, JSON, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class WorkflowRun(Base, TimestampMixin):
    __tablename__ = "workflow_run"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer)
    subject_id: Mapped[str] = mapped_column(String(50))  # employee_id
    trigger_event_id: Mapped[str] = mapped_column(String(100))  # dedup key
    status: Mapped[RunStatus] = mapped_column(String(20), default=RunStatus.pending)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)

    steps: Mapped[list["StepRun"]] = relationship(back_populates="run")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(back_populates="run")
    human_queue_items: Mapped[list["HumanQueueItem"]] = relationship(back_populates="run")


class StepStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"
    awaiting_approval = "awaiting_approval"
    queued_human = "queued_human"
    paused = "paused"


class StepRun(Base, TimestampMixin):
    __tablename__ = "step_run"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # run_id:step_id
    run_id: Mapped[str] = mapped_column(String(50), ForeignKey("workflow_run.id"))
    step_id: Mapped[str] = mapped_column(String(100))
    mode: Mapped[str] = mapped_column(String(20))  # auto | approval | route_only
    status: Mapped[StepStatus] = mapped_column(String(30), default=StepStatus.pending)
    human_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    inputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    outputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skill_id: Mapped[str] = mapped_column(String(200))
    policy_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    run: Mapped["WorkflowRun"] = relationship(back_populates="steps")
    meter: Mapped[Optional["ModelCallMeter"]] = relationship(back_populates="step_run", uselist=False)


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_request"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(50), ForeignKey("workflow_run.id"))
    step_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(200))
    approver_role: Mapped[str] = mapped_column(String(50))
    approver_person_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # approved | rejected
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_bundle: Mapped[dict] = mapped_column(JSON, default=dict)

    run: Mapped["WorkflowRun"] = relationship(back_populates="approval_requests")


class HumanQueueItem(Base, TimestampMixin):
    __tablename__ = "human_queue_item"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(50), ForeignKey("workflow_run.id"))
    step_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reason: Mapped[str] = mapped_column(String(50))  # failure | low_conf | conflict | paused | reserved
    context_bundle: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    run: Mapped["WorkflowRun"] = relationship(back_populates="human_queue_items")


class AuditLog(Base):
    """Append-only, hash-chained audit log. Never update rows."""
    __tablename__ = "audit_log"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_type: Mapped[str] = mapped_column(String(20))  # human | agent | system
    actor_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(200))
    inputs_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    rule_or_prompt_version: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64))  # SHA-256 hex of previous entry
    hash: Mapped[str] = mapped_column(String(64))  # SHA-256 hex of this entry


class ModelCallMeter(Base, TimestampMixin):
    __tablename__ = "model_call_meter"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    step_run_id: Mapped[str] = mapped_column(String(100), ForeignKey("step_run.id"))
    model: Mapped[str] = mapped_column(String(100))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_inr: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0)
    pii_masked: Mapped[bool] = mapped_column(Boolean, default=False)
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    step_run: Mapped["StepRun"] = relationship(back_populates="meter")


class Flag(Base, TimestampMixin):
    """Kill switch flags. Checked before every step."""
    __tablename__ = "flag"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # scope:name
    scope: Mapped[str] = mapped_column(String(30))  # agent | workflow | skill
    name: Mapped[str] = mapped_column(String(200))
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    paused_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DSRRequest(Base, TimestampMixin):
    """Data Subject Request (DPDP compliance)."""
    __tablename__ = "dsr_request"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(30))  # access | correction | erasure
    status: Mapped[str] = mapped_column(String(30), default="open")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class PolicyVector(Base, TimestampMixin):
    """Policy chunks stored with embeddings for RAG."""
    __tablename__ = "policy_vector"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(100))
    policy_version: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)
    # embedding stored as JSON array until pgvector extension applied
    embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
