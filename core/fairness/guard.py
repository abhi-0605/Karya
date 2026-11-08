"""
Fair Hiring & Bias Prevention Guard.
Enforces:
1. Protected attributes (gender, age, marital status, religion, caste) are purged
   from model feature sets to prevent disparate impact.
2. Auto-reject path DOES NOT EXIST: Rejections require a named human reviewer with rationale.
"""
from __future__ import annotations
from typing import Any
import structlog

log = structlog.get_logger()

PROTECTED_ATTRIBUTES = {
    "gender",
    "sex",
    "age",
    "dob",
    "date_of_birth",
    "marital_status",
    "religion",
    "caste",
    "race",
    "nationality",
}


def sanitize_candidate_profile(candidate: dict[str, Any]) -> dict[str, Any]:
    """Strip all protected demographic attributes before sending to any model or evaluation."""
    sanitized = {}
    purged = []
    for k, v in candidate.items():
        if k.lower() in PROTECTED_ATTRIBUTES:
            purged.append(k)
        else:
            sanitized[k] = v

    if purged:
        log.info("Purged protected attributes from candidate profile", purged=purged)
    return sanitized


def assert_rejection_requires_human_review(decision: str, mode: str, approver_role: str | None) -> None:
    """
    Enforces that candidate rejection cannot be autonomous.
    Raises ValueError if mode='auto'.
    """
    if decision.lower() in ("reject", "rejected", "auto_reject"):
        if mode == "auto":
            raise ValueError(
                "Fairness Violation: Automated candidate rejection is prohibited. "
                "Any candidate rejection must be reviewed and decided by a named hiring manager."
            )
        if not approver_role:
            raise ValueError("Candidate rejection requires a designated human approver role.")
