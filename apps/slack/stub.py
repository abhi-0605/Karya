"""
Slack Bot Adapter (Stub) — maps Slack events to KaryaOS Chat API.
Compatible with Slack Bolt framework.
"""
from __future__ import annotations
import structlog
from typing import Any

log = structlog.get_logger()


class SlackBotAdapter:
    """Translates incoming Slack mention/DM events to KaryaOS ChatRequest."""

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url

    async def handle_message(self, event: dict[str, Any]) -> dict[str, Any]:
        """Convert a Slack message event into an HR assistant response."""
        user = event.get("user", "slack_user")
        text = event.get("text", "")
        channel = event.get("channel", "")

        log.info("Received Slack message", user=user, channel=channel, text_len=len(text))

        # Forward to internal chat handler (or mock locally for demo)
        from backend.app.api.chat import chat_message, ChatRequest
        req = ChatRequest(message=text, user_id=user, user_role="employee")
        res = await chat_message(req)

        return {
            "channel": channel,
            "text": res.reply,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": res.reply},
                }
            ],
        }
