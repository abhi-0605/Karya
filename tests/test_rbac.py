"""
Tests for KaryaOS RBAC Engine & Delegation Guardrails.
Enforces: effective_agent_permissions = skill_permissions ∩ acting_user_permissions.
An agent can NEVER exceed the permissions of the initiating human.
"""
from __future__ import annotations
import pytest
from core.rbac.engine import RBACEngine


def test_role_permissions_lookup():
    emp_perms = RBACEngine.get_role_permissions("employee")
    assert "chat:ask" in emp_perms
    assert "profile:read_own" in emp_perms
    assert "compensation:confirm" not in emp_perms
    assert "killswitch:manage" not in emp_perms

    hrbp_perms = RBACEngine.get_role_permissions("hrbp")
    assert "compensation:confirm" in hrbp_perms
    assert "workflow:run" in hrbp_perms
    assert "resignation:accept" not in hrbp_perms


def test_delegation_rule_intersection():
    """Agent permissions cannot exceed acting human user's permissions."""
    # A skill requests both 'chat:ask' and 'compensation:confirm'
    skill_perms = ["chat:ask", "compensation:confirm", "asset:allocate"]

    # When initiated by an employee:
    eff_emp = RBACEngine.compute_effective_agent_permissions("employee", skill_perms)
    assert eff_emp == {"chat:ask"}
    assert "compensation:confirm" not in eff_emp
    assert "asset:allocate" not in eff_emp

    # When initiated by an HRBP:
    eff_hrbp = RBACEngine.compute_effective_agent_permissions("hrbp", skill_perms)
    assert eff_hrbp == {"chat:ask", "compensation:confirm"}
    assert "asset:allocate" not in eff_hrbp

    # When initiated by IT Ops:
    eff_it = RBACEngine.compute_effective_agent_permissions("it_ops", skill_perms)
    assert eff_it == {"asset:allocate"}
    assert "compensation:confirm" not in eff_it


def test_assert_agent_authorized_raises_permission_error():
    """Attempting an action outside user's role raises PermissionError."""
    # Employee cannot authorize asset allocation
    with pytest.raises(PermissionError, match="lacks permission 'asset:allocate'"):
        RBACEngine.assert_agent_authorized("employee", "asset:allocate")

    # Manager cannot authorize compensation confirmation
    with pytest.raises(PermissionError, match="lacks permission 'compensation:confirm'"):
        RBACEngine.assert_agent_authorized("manager", "compensation:confirm")

    # HRBP CAN authorize compensation confirmation
    RBACEngine.assert_agent_authorized("hrbp", "compensation:confirm")

    # HR Head CAN authorize resignation acceptance
    RBACEngine.assert_agent_authorized("hr_head", "resignation:accept")


def test_unknown_role_has_empty_permissions():
    perms = RBACEngine.get_role_permissions("unknown_hacker_role")
    assert perms == set()
    eff = RBACEngine.compute_effective_agent_permissions("unknown_hacker_role", ["chat:ask"])
    assert eff == set()
