"""Unit tests for KaryaOS Policy Engine (CI-blocking)."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.policy.engine import PolicyEngine


@pytest.fixture
def policy_engine():
    return PolicyEngine()


def test_all_policies_loaded(policy_engine: PolicyEngine):
    assert "notice_period" in policy_engine.policies
    assert "probation" in policy_engine.policies
    assert "leave_policy" in policy_engine.policies


def test_notice_period_evaluation(policy_engine: PolicyEngine):
    result_l2, tag_l2 = policy_engine.evaluate("notice_period", {"grade": "L2"})
    assert result_l2["notice_days"] == 30
    assert result_l2["buyout_allowed"] is True
    assert tag_l2 == "notice_period@4"

    result_l5, tag_l5 = policy_engine.evaluate("notice_period", {"grade": "L5"})
    assert result_l5["notice_days"] == 90
    assert result_l5["buyout_allowed"] is False
    assert tag_l5 == "notice_period@4"


def test_probation_evaluation(policy_engine: PolicyEngine):
    res_l1, tag = policy_engine.evaluate("probation", {"grade": "L1"})
    assert res_l1["probation_days"] == 90

    res_l6, tag = policy_engine.evaluate("probation", {"grade": "L6"})
    assert res_l6["probation_days"] == 180


def test_leave_policy_evaluation(policy_engine: PolicyEngine):
    res_l2, _ = policy_engine.evaluate("leave_policy", {"grade": "L2"})
    assert res_l2["annual_privilege_leave"] == 18
    assert res_l2["maternity_leave_weeks"] == 26

    res_l4, _ = policy_engine.evaluate("leave_policy", {"grade": "L4"})
    assert res_l4["annual_privilege_leave"] == 24


def test_policy_yaml_embedded_fixtures(policy_engine: PolicyEngine):
    """Run all test cases declared inside the policy YAML files themselves."""
    for policy_id in ["notice_period", "probation", "leave_policy"]:
        results = policy_engine.run_policy_tests(policy_id)
        assert len(results) > 0, f"Policy {policy_id} has no embedded tests"
        for r in results:
            assert r["passed"] is True, f"Failed embedded test in {policy_id}: {r}"
