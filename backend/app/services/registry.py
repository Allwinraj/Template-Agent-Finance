from __future__ import annotations

"""
Configuration Registry — stores "Agents" (workflow configs) as versions.

Lifecycle per README §3D: Draft → Validated → Tested → Pending Approval
                          → Approved → Published → Superseded
"""
from datetime import datetime, timezone

from app import storage
from app.agents.ids import normalize_agent_list


def _normalize_config(config: dict) -> dict:
    """Normalize legacy config keys so the runtime always sees 'calculations'."""
    if not isinstance(config, dict):
        return config
    calcs = (
        config.get("calculations")
        or config.get("calculation_pipeline")
        or config.get("calculation_steps")
        or []
    )
    config["calculations"] = calcs
    for drop in ("calculation_pipeline", "calculation_steps"):
        config.pop(drop, None)
    return config


def create_draft(name: str, description: str, config: dict, created_by: str = "admin") -> dict:
    # Normalize agent references ("A1 Capture" → "A1") — use-case agnostic.
    if isinstance(config, dict) and config.get("agents"):
        ids, unknown = normalize_agent_list(config["agents"])
        if not ids and unknown:
            raise ValueError(f"no valid agents in {unknown} — use A1..A6 (e.g. 'A1' or 'A1 Capture')")
        config = {**config, "agents": ids}
    config = _normalize_config(config)
    existing_ids = {w.get("workflow_id") for w in storage.load("workflows")}
    n = len(existing_ids) + 1
    while f"wf-{n:04d}" in existing_ids:
        n += 1
    wf = {
        "workflow_id": f"wf-{n:04d}",
        "name": name,
        "description": description,
        "config": config,
        "version": 1,
        "status": "draft",
        "owner": created_by,
        "created_by": created_by,
        "approved_by": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "published_at": None,
    }
    return storage.insert("workflows", wf)


def update_config(workflow_id: str, config: dict) -> dict | None:
    wf = storage.find_one("workflows", lambda w: w["workflow_id"] == workflow_id)
    if not wf:
        return None
    config = _normalize_config(config)
    if wf["status"] == "published":
        # immutable published version → create next version as draft
        new = create_draft(
            wf["name"], wf["description"], config, created_by=wf.get("created_by", "admin")
        )
        new["workflow_id"] = f"{wf['workflow_id'].rsplit('-', 1)[0]}-{new['id']}"
        new["version"] = wf["version"] + 1
        new["status"] = "draft"
        storage.update("workflows", new["id"], new)
        return new
    wf = storage.update("workflows", wf["id"], {"config": config})
    return wf


def transition(workflow_id: str, new_status: str, approver: str = "") -> dict | None:
    wf = storage.find_one("workflows", lambda w: w["workflow_id"] == workflow_id)
    if not wf:
        return None
    patch = {"status": new_status}
    if new_status == "published":
        patch["approved_by"] = approver or "controller_1"
        patch["published_at"] = datetime.now(timezone.utc).isoformat()
    return storage.update("workflows", wf["id"], patch)


def get(workflow_id: str) -> dict | None:
    return storage.find_one("workflows", lambda w: w["workflow_id"] == workflow_id)


def list_all(status: str | None = None) -> list:
    items = storage.load("workflows")
    if status:
        items = [w for w in items if w.get("status") == status]
    return items


def published() -> list:
    return list_all(status="published")


def delete(workflow_id: str) -> bool:
    wf = storage.find_one("workflows", lambda w: w["workflow_id"] == workflow_id)
    if not wf:
        return False
    return storage.delete("workflows", wf["id"])
