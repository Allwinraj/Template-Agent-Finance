"""Routes: dashboard KPIs, agent health, activity feed."""
from fastapi import APIRouter

from app.services import orchestrator
from app.services.orchestrator import AGENT_REGISTRY
from app.storage import load

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis")
def kpis():
    runs = load("runs")
    completed = [r for r in runs if r.get("state") == "completed"]
    waiting = [r for r in runs if r.get("state") == "waiting_for_human"]
    failed = [r for r in runs if r.get("state") == "failed"]

    total_matches = sum(
        (r.get("result", {}).get("summary", {}).get("matched", 0)) for r in completed
    )
    total_exceptions = sum(
        (r.get("result", {}).get("summary", {}).get("exceptions", 0)) for r in completed
    )

    return {
        "kpis": [
            {"id": "runs", "label": "Workflow runs", "value": len(runs), "icon": "▶"},
            {"id": "matched", "label": "Records matched", "value": total_matches, "icon": "🔗"},
            {"id": "exceptions", "label": "Exceptions open", "value": len(load("exceptions")), "icon": "⚠"},
            {"id": "waiting", "label": "Awaiting review", "value": len(waiting), "icon": "🧭"},
        ],
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "status": "healthy",
                "version": a.version,
                "simple": a.description,
            }
            for a in AGENT_REGISTRY.values()
        ],
        "services": [
            {"name": "Orchestrator", "status": "healthy", "detail": "running", "version": "v1"},
            {"name": "Rule Engine", "status": "healthy", "detail": "6 rules registered", "version": "v1"},
            {"name": "Calculation Engine", "status": "healthy", "detail": "7 calculators", "version": "v1"},
            {"name": "Audit Service", "status": "healthy", "detail": f"{len(load('audit_events'))} events", "version": "v1"},
        ],
        "activity": _activity(),
    }


def _activity():
    events = load("audit_events")[-10:]
    return [
        {
            "icon": "▶" if e["event_type"] == "workflow_started" else
                  "✓" if e["event_type"].endswith("completed") else
                  "⚠" if e["event_type"] == "workflow_failed" else "📝",
            "text": f"{e['event_type']} — {e.get('agent_id', 'orchestrator')}",
            "at": e.get("created_at", "")[-12:],
            "tone": "ok" if e["event_type"].endswith("completed") else "warn" if "fail" in e["event_type"] else "ok",
        }
        for e in reversed(events)
    ]
