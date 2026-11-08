"""
Role-Based Access Control (RBAC) Engine.
Enforces the fundamental delegation rule:
  effective_agent_permissions = agent_skill_permissions ∩ acting_user_permissions
An agent can NEVER exceed the permissions of the human who initiated the request.
"""
from __future__ import annotations
from typing import Iterable, Optional
import structlog

log = structlog.get_logger()

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "employee": {
        "profile:read_own",
        "onboarding:read_own",
        "policy:read",
        "chat:ask",
        "dsr:create",
    },
    "manager": {
        "profile:read_own",
        "onboarding:read_own",
        "policy:read",
        "chat:ask",
        "dsr:create",
        "team:read",
        "buddy:assign",
        "probation:review",
        "approval:manager",
    },
    "hrbp": {
        "profile:read_own",
        "onboarding:read_own",
        "policy:read",
        "chat:ask",
        "dsr:create",
        "team:read",
        "buddy:assign",
        "probation:review",
        "approval:manager",
        "employee:read_all",
        "workflow:run",
        "approval:hrbp",
        "human_queue:resolve",
        "policy:exception",
        "compensation:confirm",
    },
    "hr_head": {
        "profile:read_own",
        "onboarding:read_own",
        "policy:read",
        "chat:ask",
        "dsr:create",
        "team:read",
        "buddy:assign",
        "probation:review",
        "approval:manager",
        "employee:read_all",
        "workflow:run",
        "approval:hrbp",
        "approval:hr_head",
        "human_queue:resolve",
        "policy:exception",
        "compensation:confirm",
        "killswitch:manage",
        "resignation:accept",
        "disciplinary:manage",
        "audit:read",
    },
    "it_ops": {
        "asset:allocate",
        "directory:create",
        "email:provision",
        "it:manage",
        "killswitch:manage",
    },
    "admin_ops": {
        "admin:access_card",
        "admin:desk",
        "killswitch:manage",
    },
    "finance": {
        "payroll:setup",
        "payroll:run_signoff",
        "compensation:read",
        "compensation:confirm",
    },
    "auditor": {
        "audit:read",
        "policy:read",
        "metrics:read",
        "audit:verify",
    },
    "developer": {
        "workflow:validate",
        "skill:test",
        "policy:read",
    },
}


class RBACEngine:
    @staticmethod
    def get_role_permissions(role: str) -> set[str]:
        return ROLE_PERMISSIONS.get(role, set()).copy()

    @staticmethod
    def has_permission(role: str, permission: str) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def compute_effective_agent_permissions(
        acting_user_role: str,
        skill_declared_permissions: Iterable[str],
    ) -> set[str]:
        """
        Delegation rule:
        effective_permissions = skill_declared_permissions ∩ acting_user_permissions
        """
        user_perms = ROLE_PERMISSIONS.get(acting_user_role, set())
        declared = set(skill_declared_permissions)
        effective = declared.intersection(user_perms)
        log.debug(
            "Computed effective agent permissions",
            user_role=acting_user_role,
            declared=list(declared),
            effective=list(effective),
        )
        return effective

    @staticmethod
    def assert_agent_authorized(acting_user_role: str, required_permission: str) -> None:
        """Raise PermissionError if the acting human user does not hold the required permission."""
        if not RBACEngine.has_permission(acting_user_role, required_permission):
            raise PermissionError(
                f"Agent run blocked: Acting user role '{acting_user_role}' lacks permission '{required_permission}'"
            )
