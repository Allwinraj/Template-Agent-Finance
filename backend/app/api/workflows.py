from __future__ import annotations

"""Routes: workflow execution (run a saved Agent against files)."""
from fastapi import APIRouter, HTTPException

from app.services import orchestrator

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/{workflow_id}/run")
def run_workflow(workflow_id: str, files: dict | None = None):
    """
    Execute a saved workflow (Agent) end-to-end.

    files: optional {role: file_name} — upload new Excel/CSV and the same
           Agent runs against it using its saved column mappings.
    """
    result = orchestrator.run_workflow(workflow_id, files)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs")
def list_runs(limit: int = 20):
    return orchestrator.list_runs(limit)
