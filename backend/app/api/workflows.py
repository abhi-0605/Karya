"""Workflows router — list and inspect workflow runs."""
from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_runs() -> dict[str, Any]:
    """Stub: returns an empty list of workflow runs."""
    return {"runs": [], "total": 0}


@router.get("/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Stub: returns a placeholder workflow run."""
    return {"run_id": run_id, "status": "pending", "steps": []}
