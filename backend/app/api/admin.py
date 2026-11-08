"""
Admin Router — Kill switch controls, system flags, and hot-reload.
Allows HR and Ops to pause an agent, workflow, or skill with instant effect (<= 1s).
"""
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user
from app.database import get_db
from app.models.workflow import Flag
from core.killswitch.killswitch import KillSwitch
from core.audit.logger import AuditLogger
from core.engine.skill_registry import reload_registry
from core.engine.loader import load_all_workflows

router = APIRouter()


def _require_admin_or_hr(user: dict) -> dict:
    role = user.get("role", "")
    if role not in ("hr_head", "hrbp", "it_ops", "admin_ops"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized to operate kill switch controls.",
        )
    return user


@router.get("/killswitch")
async def list_killswitch_flags(
    user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all flags in the kill switch table."""
    result = await db.execute(select(Flag))
    flags = result.scalars().all()
    return [
        {
            "id": f.id,
            "scope": f.scope,
            "name": f.name,
            "paused": f.paused,
            "paused_by": f.paused_by,
            "paused_at": f.paused_at.isoformat() if f.paused_at else None,
        }
        for f in flags
    ]


@router.get("/killswitch/{scope}/{name}/status")
async def get_flag_status(
    scope: str,
    name: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Check if a specific scope and name is paused."""
    ks = KillSwitch(db)
    paused = await ks.is_paused(f"{scope}:{name}")
    return {"scope": scope, "name": name, "paused": paused}


@router.post("/killswitch/{scope}/{name}/pause")
async def pause_target(
    scope: str,
    name: str,
    user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Pause an agent, workflow, or skill. Takes effect immediately on next step."""
    _require_admin_or_hr(user)
    ks = KillSwitch(db)
    audit = AuditLogger(db)

    paused_by = user.get("sub", "UNKNOWN")
    await ks.pause(scope=scope, name=name, paused_by=paused_by)

    await audit.log(
        actor_type="human",
        actor_id=paused_by,
        action=f"killswitch:pause:{scope}:{name}",
        reasoning="Paused by HR via Admin UI",
        outcome=f"{scope}:{name} paused",
    )

    return {"status": "paused", "scope": scope, "name": name, "paused_by": paused_by}


@router.post("/killswitch/{scope}/{name}/resume")
async def resume_target(
    scope: str,
    name: str,
    user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Resume a paused agent, workflow, or skill."""
    _require_admin_or_hr(user)
    ks = KillSwitch(db)
    audit = AuditLogger(db)

    resumed_by = user.get("sub", "UNKNOWN")
    await ks.resume(scope=scope, name=name, resumed_by=resumed_by)

    await audit.log(
        actor_type="human",
        actor_id=resumed_by,
        action=f"killswitch:resume:{scope}:{name}",
        reasoning="Resumed by HR via Admin UI",
        outcome=f"{scope}:{name} resumed",
    )

    return {"status": "active", "scope": scope, "name": name, "resumed_by": resumed_by}


@router.post("/reload")
async def reload_extensions(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Hot-reload skills and workflow definitions from disk."""
    _require_admin_or_hr(user)
    skills = reload_registry()
    workflows = load_all_workflows()
    return {
        "status": "reloaded",
        "skills_loaded": len(skills),
        "workflows_loaded": len(workflows),
    }
