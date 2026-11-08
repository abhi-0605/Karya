"""
KaryaOS Workflow Scaffolding CLI tool.
Quickly generates a workflow YAML, policy YAML with embedded test fixtures,
and a pytest test file in under 2 seconds.

Usage:
  python scripts/new_workflow.py <workflow_id> [--trigger <trigger_name>]
"""
from __future__ import annotations
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = PROJECT_ROOT / "extensions" / "workflows"
POLICIES_DIR = PROJECT_ROOT / "extensions" / "policies"
TESTS_DIR = PROJECT_ROOT / "tests"


def scaffold_workflow(workflow_id: str, trigger: str | None = None) -> None:
    w_id = workflow_id.lower().replace("-", "_").strip()
    trig = trigger or f"employee.{w_id}_requested"

    print(f"⚡ Scaffolding extension assets for: '{w_id}'...")

    # 1. Scaffolding Workflow YAML
    wf_path = WORKFLOWS_DIR / f"{w_id}.yaml"
    wf_content = f"""id: {w_id}
version: 1
trigger: {trig}
description: "Declarative workflow for {w_id.replace('_', ' ').title()}"
inputs:
  - employee_id
steps:
  - id: evaluate_{w_id}_policy
    skill: manager.assign_buddy
    mode: auto
    timeout_s: 15

  - id: approve_{w_id}_decision
    skill: hr.confirm_compensation
    action: policy.exception
    depends_on:
      - evaluate_{w_id}_policy
    mode: approval
    approver_role: hrbp

  - id: execute_fulfillment
    skill: admin.issue_access_card
    depends_on:
      - approve_{w_id}_decision
    mode: auto
    timeout_s: 15

  - id: notify_subject
    skill: comms.send_welcome
    depends_on:
      - execute_fulfillment
    mode: auto
    timeout_s: 10
"""
    wf_path.write_text(wf_content, encoding="utf-8")
    print(f"  • Created workflow: {wf_path}")

    # 2. Scaffolding Policy YAML with embedded test fixtures
    policy_path = POLICIES_DIR / f"{w_id}.yaml"
    policy_content = f"""id: {w_id}
version: 1
effective_from: 2026-01-01
description: "Business and statutory policy rules for {w_id.replace('_', ' ').title()}"
rules:
  - name: standard_{w_id}
    when:
      grade: [L1, L2, L3]
    then:
      eligible: true
      max_limit_days: 30

  - name: senior_{w_id}
    when:
      grade: [L4, L5, L6]
    then:
      eligible: true
      max_limit_days: 90
      requires_vp_signoff: true

tests:
  - given:
      grade: L2
    expect:
      eligible: true
      max_limit_days: 30

  - given:
      grade: L5
    expect:
      eligible: true
      max_limit_days: 90
      requires_vp_signoff: true
"""
    policy_path.write_text(policy_content, encoding="utf-8")
    print(f"  • Created policy: {policy_path}")

    # 3. Scaffolding Pytest test file
    test_path = TESTS_DIR / f"test_{w_id}.py"
    test_content = f'''"""Automated tests for workflow '{w_id}'."""
from pathlib import Path
import pytest
from core.engine.loader import load_workflow
from core.engine.validator import validate_workflow
from core.policy.engine import PolicyEngine


def test_{w_id}_workflow_validity():
    wf = load_workflow(Path("extensions/workflows/{w_id}.yaml"))
    warnings = validate_workflow(wf, validate_skills=True)
    assert len(warnings) == 0


def test_{w_id}_policy_embedded_fixtures():
    engine = PolicyEngine()
    results = engine.run_policy_tests("{w_id}")
    assert len(results) > 0
    for r in results:
        assert r["passed"] is True
'''
    test_path.write_text(test_content, encoding="utf-8")
    print(f"  • Created test harness: {test_path}")

    print("\n✅ Scaffold complete! Run validation now:")
    print("   python scripts/validate.py")
    print(f"   pytest tests/test_{w_id}.py -q")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold a new KaryaOS extension workflow")
    parser.add_argument("id", help="Unique workflow ID (e.g. gym_reimbursement, relocation)")
    parser.add_argument("--trigger", help="Event trigger name", default=None)
    args = parser.parse_args()

    scaffold_workflow(args.id, args.trigger)
