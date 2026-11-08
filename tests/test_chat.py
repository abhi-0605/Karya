"""
Tests for P6 Chat API: intent classification, policy RAG, RBAC gate.
Uses httpx.AsyncClient against the FastAPI app — no external APIs.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_chat.db")

from app.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_chat_check_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/chat/message", json={
            "message": "What is the status of my onboarding?",
            "user_id": "emp001",
            "user_role": "employee",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "check_status"
    assert data["confidence"] >= 0.90
    assert "onboarding" in data["reply"].lower() or "workflow" in data["reply"].lower()
    assert data["escalated"] is False


@pytest.mark.asyncio
async def test_chat_policy_qa_leave():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/chat/message", json={
            "message": "How many leave days do I get?",
            "user_id": "emp001",
            "user_role": "employee",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in ("leave_query", "policy_qa")
    assert len(data["reply"]) > 20


@pytest.mark.asyncio
async def test_chat_policy_qa_notice():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/chat/message", json={
            "message": "What is my notice period?",
            "user_id": "emp001",
            "user_role": "employee",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in ("notice_query", "policy_qa")
    assert len(data["reply"]) > 20


@pytest.mark.asyncio
async def test_chat_rbac_denied_approval_for_employee():
    """An employee asking to approve should be denied — min role is hrbp."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/chat/message", json={
            "message": "Approve the pending compensation request",
            "user_id": "emp001",
            "user_role": "employee",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "approval_action"
    # Employee is not allowed; reply should mention permission / role
    assert "permission" in data["reply"].lower() or "role" in data["reply"].lower()


@pytest.mark.asyncio
async def test_chat_approval_action_hrbp():
    """HRBP asking about approvals should get a list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/chat/message", json={
            "message": "Show me pending approvals to signoff",
            "user_id": "hrbp001",
            "user_role": "hrbp",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "approval_action"
    assert data["escalated"] is False
    assert "approval" in data["reply"].lower()


@pytest.mark.asyncio
async def test_chat_laptop_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/chat/message", json={
            "message": "When will my laptop arrive?",
            "user_id": "emp001",
            "user_role": "employee",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "laptop_query"
    assert "laptop" in data["reply"].lower()


@pytest.mark.asyncio
async def test_chat_general_qa_escalates():
    """Completely ambiguous message should escalate (confidence < 0.75)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/chat/message", json={
            "message": "Tell me something interesting about the universe",
            "user_id": "emp001",
            "user_role": "employee",
        })
    assert resp.status_code == 200
    data = resp.json()
    # Should escalate because FakeLLMProvider returns confidence=0.65 for general_qa
    assert data["escalated"] is True
    assert data["human_queue_item_id"] is not None


@pytest.mark.asyncio
async def test_chat_intents_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/chat/intents")
    assert resp.status_code == 200
    intents = resp.json()["intents"]
    assert "check_status" in intents
    assert "approval_action" in intents
