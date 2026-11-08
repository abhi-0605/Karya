"""Human queue router — tasks waiting for human action."""
from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_queue() -> dict[str, Any]:
    """Stub: returns pending human-action items."""
    return {"items": [], "total": 0}


@router.get("/{item_id}")
async def get_item(item_id: str) -> dict[str, Any]:
    """Stub: returns a single queue item."""
    return {"item_id": item_id, "status": "pending", "type": "approval"}
