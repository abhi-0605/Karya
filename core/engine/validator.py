"""
Workflow Validator — validates workflow definitions at load time.
Enforces:
1. Skills referenced exist in skill registry.
2. Dependencies form a valid DAG (no cycles, no missing dependencies).
3. GOVERNANCE RULE: Any step matching reserved_decisions.yaml CANNOT run in mode='auto'.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml
import structlog

from core.engine.models import WorkflowDefinition
from core.engine.skill_registry import get_skill

log = structlog.get_logger()

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class WorkflowValidationError(Exception):
    """Raised when a workflow definition violates governance or graph rules."""
    pass


def load_reserved_decision_actions(config_path: Optional[Path] = None) -> list[str]:
    """Parse list of reserved actions from reserved_decisions.yaml."""
    cfg_file = config_path or (CONFIG_DIR / "reserved_decisions.yaml")
    if not cfg_file.exists():
        return []
    data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    actions = []
    for entry in data.get("reserved", []):
        act = entry.get("action", "")
        for part in act.split("|"):
            actions.append(part.strip())
    return actions


def validate_workflow(
    workflow: WorkflowDefinition,
    validate_skills: bool = True,
    config_path: Optional[Path] = None,
) -> list[str]:
    """
    Validate a WorkflowDefinition.
    Returns a list of warnings or raises WorkflowValidationError on hard violations.
    """
    warnings = []
    step_ids = {s.id for s in workflow.steps}
    reserved_actions = load_reserved_decision_actions(config_path)

    for step in workflow.steps:
        action = step.action or step.skill

        # 1. Hard Rule: Reserved actions CANNOT be mode='auto'
        for r in reserved_actions:
            if action == r or action.startswith(r.rstrip("*")):
                if step.mode == "auto":
                    raise WorkflowValidationError(
                        f"Step '{step.id}' defines reserved action '{action}' but mode is set to 'auto'. "
                        "Reserved actions must have mode='approval' or mode='route_only' with a named human approver."
                    )

        # 2. Dependency existence
        for dep in step.depends_on:
            if dep not in step_ids:
                raise WorkflowValidationError(
                    f"Step '{step.id}' depends on '{dep}', but '{dep}' does not exist in workflow."
                )

        # 3. Skill registry existence check (optional warning or error)
        if validate_skills:
            skill = get_skill(step.skill)
            if not skill:
                warnings.append(f"Skill '{step.skill}' for step '{step.id}' is not yet registered in skill registry.")

    # 4. Cycle Detection (Topological Sort)
    in_degree = {s.id: 0 for s in workflow.steps}
    adj = {s.id: [] for s in workflow.steps}

    for step in workflow.steps:
        for dep in step.depends_on:
            adj[dep].append(step.id)
            in_degree[step.id] += 1

    queue = [s_id for s_id, deg in in_degree.items() if deg == 0]
    visited_count = 0
    while queue:
        curr = queue.pop(0)
        visited_count += 1
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited_count != len(workflow.steps):
        raise WorkflowValidationError(f"Workflow '{workflow.id}' contains a circular dependency cycle!")

    return warnings
