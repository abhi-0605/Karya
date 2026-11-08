"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-11-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # person
    op.create_table("person",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("dob", sa.Date, nullable=True),
        sa.Column("contact_encrypted", sa.Text, nullable=True),
        sa.Column("purpose_tags", sa.JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # employee
    op.create_table("employee",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("person_id", sa.String(50), sa.ForeignKey("person.id"), nullable=False),
        sa.Column("emp_code", sa.String(50), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("manager_id", sa.String(50), sa.ForeignKey("employee.id"), nullable=True),
        sa.Column("grade", sa.String(10), nullable=False),
        sa.Column("org_unit", sa.String(100), nullable=False),
        sa.Column("location", sa.String(100), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("role_title", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("grade_band", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # employment_event
    op.create_table("employment_event",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("employee_id", sa.String(50), sa.ForeignKey("employee.id"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("triggered_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # candidate
    op.create_table("candidate",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("person_id", sa.String(50), sa.ForeignKey("person.id"), nullable=False),
        sa.Column("requisition_id", sa.String(50), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False, server_default="applied"),
        sa.Column("rank_explanation", sa.JSON, nullable=True),
        sa.Column("human_reviewed_by", sa.String(100), nullable=True),
        sa.Column("agent_recommendation", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # consent_record
    op.create_table("consent_record",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("person_id", sa.String(50), sa.ForeignKey("person.id"), nullable=False),
        sa.Column("purpose", sa.String(200), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # workflow_run
    op.create_table("workflow_run",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("workflow_id", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("subject_id", sa.String(50), nullable=False),
        sa.Column("trigger_event_id", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # step_run
    op.create_table("step_run",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("run_id", sa.String(50), sa.ForeignKey("workflow_run.id"), nullable=False),
        sa.Column("step_id", sa.String(100), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("human_touch", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inputs", sa.JSON, nullable=True),
        sa.Column("outputs", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("skill_id", sa.String(200), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # approval_request
    op.create_table("approval_request",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("run_id", sa.String(50), sa.ForeignKey("workflow_run.id"), nullable=False),
        sa.Column("step_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("approver_role", sa.String(50), nullable=False),
        sa.Column("approver_person_id", sa.String(50), nullable=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("context_bundle", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # human_queue_item
    op.create_table("human_queue_item",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("run_id", sa.String(50), sa.ForeignKey("workflow_run.id"), nullable=False),
        sa.Column("step_id", sa.String(100), nullable=True),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("context_bundle", sa.JSON, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(100), nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # audit_log (append-only, hash-chained)
    op.create_table("audit_log",
        sa.Column("seq", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("inputs_ref", sa.String(200), nullable=True),
        sa.Column("rule_or_prompt_version", sa.String(200), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("outcome", sa.Text, nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
    )

    # model_call_meter
    op.create_table("model_call_meter",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("step_run_id", sa.String(100), sa.ForeignKey("step_run.id"), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("tokens_in", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_inr", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("pii_masked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # flag (kill switch)
    op.create_table("flag",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("paused", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("paused_by", sa.String(100), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # dsr_request
    op.create_table("dsr_request",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("person_id", sa.String(50), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # policy_vector (for RAG)
    op.create_table("policy_vector",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("policy_id", sa.String(100), nullable=False),
        sa.Column("policy_version", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes
    op.create_index("ix_workflow_run_subject", "workflow_run", ["subject_id"])
    op.create_index("ix_workflow_run_status", "workflow_run", ["status"])
    op.create_index("ix_step_run_run_id", "step_run", ["run_id"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_human_queue_resolved", "human_queue_item", ["resolved_at"])


def downgrade() -> None:
    op.drop_table("policy_vector")
    op.drop_table("dsr_request")
    op.drop_table("flag")
    op.drop_table("model_call_meter")
    op.drop_table("audit_log")
    op.drop_table("human_queue_item")
    op.drop_table("approval_request")
    op.drop_table("step_run")
    op.drop_table("workflow_run")
    op.drop_table("consent_record")
    op.drop_table("candidate")
    op.drop_table("employment_event")
    op.drop_table("employee")
    op.drop_table("person")
