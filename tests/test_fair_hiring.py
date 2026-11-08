"""
Tests for Fair Hiring Guardrails.
Enforces:
1. Protected attributes (gender, age, marital status) are purged from model features.
2. Auto-reject path does not exist; candidate rejection strictly requires human signoff.
"""
from __future__ import annotations
import pytest
from core.fairness.guard import sanitize_candidate_profile, assert_rejection_requires_human_review, PROTECTED_ATTRIBUTES


def test_protected_attributes_purged_from_candidate():
    raw_candidate = {
        "candidate_id": "CAND-102",
        "first_name": "Priyanka",
        "last_name": "Sen",
        "role_applied": "Senior Software Engineer",
        "years_experience": 6,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        # Protected attributes:
        "gender": "Female",
        "age": 28,
        "date_of_birth": "1998-05-14",
        "marital_status": "Single",
        "religion": "Hindu",
    }

    clean = sanitize_candidate_profile(raw_candidate)

    # Legitimate job-relevant skills remain
    assert clean["candidate_id"] == "CAND-102"
    assert clean["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker"]
    assert clean["years_experience"] == 6

    # All protected attributes are removed
    for attr in PROTECTED_ATTRIBUTES:
        assert attr not in clean


def test_auto_reject_path_is_blocked():
    """Attempting an automated rejection raises ValueError."""
    with pytest.raises(ValueError, match="Automated candidate rejection is prohibited"):
        assert_rejection_requires_human_review(
            decision="reject",
            mode="auto",
            approver_role=None,
        )


def test_human_rejection_with_approver_role_allowed():
    """Rejection with named human approver role is valid."""
    # Should not raise
    assert_rejection_requires_human_review(
        decision="reject",
        mode="approval",
        approver_role="hiring_manager",
    )
