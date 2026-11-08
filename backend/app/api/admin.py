"""Admin router — killswitch and operational controls."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user

router = APIRouter()


@router.post("/killswitch/{scope}/{name}/pause")
async def pause_killswitch(
    scope: str,
    name: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Stub: pause a workflow or skill via the killswitch."""
    return {
        "scope": scope,
        "name": name,
        "action": "paused",
        "triggered_by": user.get("sub"),
    }


@router.post("/killswitch/{scope}/{name}/resume")
async def resume_killswitch(
    scope: str,
    name: str,
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Stub: resume a paused workflow or skill."""
    return {
        "scope": scope,
        "name": name,
        "action": "resumed",
        "triggered_by": user.get("sub"),
    }
