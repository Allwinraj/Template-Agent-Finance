from __future__ import annotations

"""Audit & Lineage Service — append-only event log (README §3C)."""
from datetime import datetime, timezone

from app import storage


def record(
    event_type: str,
    run_id: str,
    actor_id: str,
    workflow_id: str = "",
    agent_id: str = "",
    capability_id: str = "",
    input_refs: list | None = None,
    output: dict | None = None,
) -> dict:
    event = {
        "event_id": f"evt-{storage.load('audit_events').__len__() + 1:05d}",
        "event_type": event_type,
        "run_id": run_id,
        "correlation_id": run_id,
        "actor_type": "service" if not agent_id else "agent",
        "actor_id": actor_id,
        "workflow_id": workflow_id,
        "agent_id": agent_id,
        "capability_id": capability_id,
        "input_refs": input_refs or [],
        "output": output or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return storage.append("audit_events", event)


def events_for_run(run_id: str) -> list:
    return storage.find("audit_events", lambda e: e.get("run_id") == run_id)


def all_events(limit: int = 100) -> list:
    events = storage.load("audit_events")
    return events[-limit:]