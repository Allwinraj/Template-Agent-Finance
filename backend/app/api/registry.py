from __future__ import annotations

"""Routes: Configuration Registry — save, version, test, submit, publish Agents."""
from fastapi import APIRouter, HTTPException

from app.services import registry
from app.engines.calculation_engine import validate_pipeline

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/workflows")
def list_workflows(status: str | None = None):
    return registry.list_all(status)


@router.post("/workflows")
def create_workflow(payload: dict):
    """Create a new draft workflow (Agent)."""
    wf = registry.create_draft(
        name=payload.get("name", "Untitled"),
        description=payload.get("description", ""),
        config=payload.get("config", {}),
        created_by=payload.get("created_by", "admin"),
    )
    return wf


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    wf = registry.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow not found")
    return wf


@router.put("/workflows/{workflow_id}/configuration")
def update_configuration(workflow_id: str, config: dict):
    wf = registry.update_config(workflow_id, config)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow not found")
    return wf


@router.post("/workflows/{workflow_id}/validate")
def validate_workflow(workflow_id: str):
    """Validate references and dependencies (README §3D)."""
    wf = registry.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow not found")
    errors = _validate_config(wf["config"])
    calc_errors = _validate_calculations(wf["config"])
    errors.extend(calc_errors)
    return {"valid": not errors, "errors": errors}


@router.post("/workflows/{workflow_id}/submit-approval")
def submit_approval(workflow_id: str, approver: str = "controller_1"):
    wf = registry.transition(workflow_id, "pending_approval", approver)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow not found")
    return wf


@router.post("/workflows/{workflow_id}/publish")
def publish_workflow(workflow_id: str, approver: str = "controller_1"):
    wf = registry.transition(workflow_id, "published", approver)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow not found")
    return wf


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str):
    success = registry.delete(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {"status": "deleted", "workflow_id": workflow_id}



def _validate_config(config: dict) -> list:
    """Basic structural validation of a workflow config."""
    errors = []
    agents = config.get("agents", [])
    valid_agents = {"A1", "A2", "A3", "A4", "A5", "A6"}
    for a in agents:
        if a not in valid_agents:
            errors.append(f"unknown agent {a}")
    if not agents:
        errors.append("no agents selected")
    if not config.get("sources"):
        errors.append("no data sources configured")
    return errors


def _validate_calculations(config: dict) -> list:
    """Run calculation pipeline validation and return errors."""
    calcs = config.get("calculations") or []
    if not calcs:
        return []
    try:
        errors = validate_pipeline(calcs)
    except Exception as exc:
        return [f"calculation pipeline validation failed: {exc}"]
    return errors
