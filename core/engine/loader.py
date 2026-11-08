"""Load and validate workflow definitions from YAML files."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import yaml
import structlog

from core.engine.models import WorkflowDefinition, StepDefinition, RetryConfig

log = structlog.get_logger()

WORKFLOWS_DIR = Path(__file__).parent.parent.parent / "extensions" / "workflows"


def load_workflow(path: Path) -> WorkflowDefinition:
    """Parse a YAML workflow definition file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = []
    for s in data.get("steps", []):
        retry_data = s.get("retry", {})
        retry = RetryConfig(
            max=retry_data.get("max", 3),
            backoff=retry_data.get("backoff", "exponential"),
        )
        step = StepDefinition(
            id=s["id"],
            skill=s["skill"],
            mode=s.get("mode", "auto"),
            depends_on=s.get("depends_on", []),
            sla_minutes=s.get("sla_minutes"),
            on_failure=s.get("on_failure", "fail"),
            llm=s.get("llm"),
            approver_role=s.get("approver_role"),
            timeout_s=s.get("timeout_s", 30),
            retry=retry,
            action=s.get("action", s["skill"]),
        )
        steps.append(step)

    return WorkflowDefinition(
        id=data["id"],
        version=data.get("version", 1),
        trigger=data["trigger"],
        inputs=data.get("inputs", []),
        steps=steps,
        description=data.get("description", ""),
    )


def load_all_workflows(directory: Path = WORKFLOWS_DIR) -> dict[str, WorkflowDefinition]:
    """Auto-load all .yaml files from the workflows directory."""
    workflows: dict[str, WorkflowDefinition] = {}
    if not directory.exists():
        log.warning("Workflows directory not found", path=str(directory))
        return workflows
    for path in directory.glob("*.yaml"):
        if path.name.startswith("_"):
            continue
        try:
            wf = load_workflow(path)
            workflows[wf.id] = wf
            log.info("Loaded workflow", id=wf.id, version=wf.version, steps=len(wf.steps))
        except Exception as e:
            log.error("Failed to load workflow", path=str(path), error=str(e))
    return workflows
