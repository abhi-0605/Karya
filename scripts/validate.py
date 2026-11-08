"""
KaryaOS Validation Utility (make validate).
Validates all declarative workflows, skill registrations, DAG dependencies,
reserved decisions, and policy test fixtures across the platform.
"""
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from core.engine.loader import load_workflow
from core.engine.validator import validate_workflow, WorkflowValidationError
from core.policy.engine import PolicyEngine
from core.engine.skill_registry import load_all_skills, get_registry


def validate_all() -> bool:
    print("=" * 60)
    print("🔍 Running KaryaOS Platform Validation (make validate)...")
    print("=" * 60)
    has_errors = False

    # 1. Discover skills
    skills = load_all_skills()
    print(f"📦 Discovered {len(skills)} skills in extensions/skills/:")
    for s_name in sorted(skills.keys()):
        print(f"   • {s_name}")
    print()

    # 2. Validate workflows
    workflows_dir = PROJECT_ROOT / "extensions" / "workflows"
    workflow_files = list(workflows_dir.glob("*.yaml"))
    print(f"🔄 Validating {len(workflow_files)} workflows in extensions/workflows/:")

    for wf_file in workflow_files:
        if wf_file.name.startswith("_"):
            continue
        try:
            wf = load_workflow(wf_file)
            warnings = validate_workflow(wf, validate_skills=True)
            status = "✅ VALID" if not warnings else "⚠️  WARNINGS"
            print(f"   • {wf.id:<20} v{wf.version} [{len(wf.steps)} steps] -> {status}")
            for w in warnings:
                print(f"       warning: {w}")
        except WorkflowValidationError as e:
            print(f"   • {wf_file.stem:<20} -> ❌ VALIDATION FAILED:")
            print(f"       {e}")
            has_errors = True
        except Exception as e:
            print(f"   • {wf_file.stem:<20} -> ❌ ERROR: {e}")
            has_errors = True
    print()

    # 3. Validate policies and embedded fixtures
    engine = PolicyEngine()
    print(f"📜 Validating {len(engine.policies)} policies in extensions/policies/:")
    for p_id in sorted(engine.policies.keys()):
        test_results = engine.run_policy_tests(p_id)
        passed = sum(1 for r in test_results if r["passed"])
        total = len(test_results)
        if passed == total:
            print(f"   • {p_id:<20} -> ✅ ALL {total} EMBEDDED TESTS PASSED")
        else:
            print(f"   • {p_id:<20} -> ❌ {total - passed}/{total} TESTS FAILED")
            has_errors = True
    print()

    print("=" * 60)
    if has_errors:
        print("❌ Platform validation FAILED with errors.")
        return False
    else:
        print("✅ ALL WORKFLOWS, SKILLS, AND POLICIES ARE VALID!")
        print("=" * 60)
        return True


if __name__ == "__main__":
    success = validate_all()
    sys.exit(0 if success else 1)
