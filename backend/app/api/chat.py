"""Chat router — conversational HR assistant endpoint."""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    session_id: str | None = None
    context: dict | None = None


@router.post("/message")
async def chat_message(body: ChatMessage) -> dict[str, Any]:
    """Stub: accepts a user message and returns a placeholder assistant reply."""
    return {
        "session_id": body.session_id or "new_session",
        "reply": "Hello! I'm KaryaOS. How can I help you today? (stub response)",
        "confidence": 1.0,
        "escalated": False,
    }
