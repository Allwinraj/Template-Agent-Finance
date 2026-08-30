from __future__ import annotations

"""
Workflow Orchestrator — deterministic agent sequencing (README §5).

Runs the configured agent chain in order, passing structured JSON payloads
between agents, recording audit events and run state at every transition.

Run states: created → running → waiting_for_human → completed / failed
"""
import logging
import uuid
from datetime import datetime, timezone

from app.agents.a1_capture import A1Capture
from app.agents.a2_harmonize import A2Harmonize
from app.agents.a3_match import A3Match
from app.agents.a4_validate import A4Validate
from app.agents.a5_explain import A5Explain
from app.agents.a6_coordinate import A6Coordinate
from app.agents.ids import normalize_agent_list
from app.services import audit_service
from app.storage import insert, find_one, update, load

logger = logging.getLogger("nexus.orchestrator")

AGENT_REGISTRY = {
    "A1": A1Capture(),
    "A2": A2Harmonize(),
    "A3": A3Match(),
    "A4": A4Validate(),
    "A5": A5Explain(),
    "A6": A6Coordinate(),
}


def run_workflow(workflow_id: str, files: dict | None = None) -> dict:
    """
    Execute a published (or draft/test) workflow end-to-end.

    files: optional {role: file_name} — upload new Excel/CSV and the same
           Agent runs against it using its saved column mappings.
    """
    wf = find_one("workflows", lambda w: w["workflow_id"] == workflow_id)
    if not wf:
        return {"error": (f"workflow not found: {workflow_id}. "
                          "If this agent was just created, the data store may have been "
                          "altered by cloud sync (OneDrive) — reload the Agent Library and retry, "
                          "or set NEXUS_DATA_DIR to a folder outside OneDrive.")}

    config = wf["config"]
    raw_agent_ids = config.get("agents", ["A1", "A2", "A3", "A4", "A5", "A6"])
    agent_ids, unknown_agents = normalize_agent_list(raw_agent_ids)
    logger.info("[run] %s — agents requested: %s → normalized: %s%s",
                workflow_id, raw_agent_ids, agent_ids,
                f" (UNKNOWN, skipped: {unknown_agents})" if unknown_agents else "")
    if not agent_ids:
        return {"error": f"workflow {workflow_id} has no valid agents configured (raw: {raw_agent_ids})"}

    run_id = f"run-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
    run = {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "workflow_name": wf["name"],
        "state": "running",
        "steps": [],
        "files": files or {},
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
    }
    run = insert("runs", run)
    audit_service.record("workflow_started", run_id, "orchestrator", workflow_id,
                         capability_id=f"{workflow_id}:v{wf.get('version', 1)}")

    payload = {"uploaded_paths": files or {}}
    context = {"run_id": run_id, "workflow_id": workflow_id, "llm_provider": (config.get("llm_provider") or "openrouter")}

    try:
        for agent_id in agent_ids:
            agent = AGENT_REGISTRY.get(agent_id)
            if agent is None:
                raise ValueError(f"unknown agent {agent_id}")
            agent_config = _agent_config(config, agent_id)
            logger.info("[run] %s → %s %s starting…", run_id, agent_id, agent.name)
            t_agent = datetime.now(timezone.utc)
            output = agent.run(agent_config, payload, context)
            payload = {**payload, **output}
            logger.info("[run] %s → %s %s completed in %.1fs — %s",
                        run_id, agent_id, agent.name,
                        (datetime.now(timezone.utc) - t_agent).total_seconds(),
                        _summarize(output))
            step = {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "status": "completed",
                "at": datetime.now(timezone.utc).isoformat(),
                "output_summary": _summarize(output),
            }
            run["steps"].append(step)
            update("runs", run["id"], {"steps": run["steps"]})
            audit_service.record(
                f"agent_{agent_id.lower()}_completed", run_id, agent_id.lower(),
                workflow_id, agent_id=agent_id,
                output=_summarize(output),
            )

            # A6 may create review tasks → run moves to waiting_for_human
            if agent_id == "A6" and output.get("tasks_created", 0) > 0:
                run["state"] = "waiting_for_human"

        final_state = "waiting_for_human" if run["state"] == "waiting_for_human" else "completed"
        # compact compared rows for the chat/report UI
        compared_rows = [
            {
                "gl_account": c.get("gl_account"),
                "cost_center": c.get("cost_center"),
                "fiscal_period": c.get("fiscal_period"),
                "actual": c.get("actual"),
                "budget": c.get("budget"),
                "calc_results": c.get("calc_results", {}),
                "actions": c.get("actions", []),
                "status": c.get("status"),
                "evidence": c.get("evidence", {}),
            }
            for c in payload.get("compared_rows", [])
        ]
        update("runs", run["id"], {
            "state": final_state,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "result": {
                "summary": payload.get("summary", {}),
                "executive": payload.get("executive", {}),
                "report": payload.get("report", {}),
                "review_tasks": payload.get("review_tasks", []),
                "compared_rows": compared_rows,
                "exceptions": payload.get("exceptions", []),
            },
        })
        audit_service.record("workflow_completed", run_id, "orchestrator", workflow_id,
                             output={"state": final_state})
        return find_one("runs", lambda r: r["run_id"] == run_id)

    except Exception as exc:  # noqa: BLE001
        logger.exception("[run] %s FAILED: %s", run_id, exc)
        update("runs", run["id"], {
            "state": "failed",
            "error": str(exc),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        audit_service.record("workflow_failed", run_id, "orchestrator", workflow_id,
                             output={"error": str(exc)})
        return find_one("runs", lambda r: r["run_id"] == run_id)


def _agent_config(config: dict, agent_id: str) -> dict:
    """Split the workflow config into the slice each agent needs."""
    keys = {
        "A1": ["sources"],
        "A2": ["sources"],
        "A3": ["matching"],
        "A4": ["calculations", "rules", "comparison", "settings", "calculation_policy"],
        "A5": ["report", "output_spec"],
        "A6": ["routing"],
    }.get(agent_id, [])
    return {k: config[k] for k in keys if k in config}


def _summarize(output: dict) -> dict:
    """Small, JSON-safe summary of an agent output (for audit + UI)."""
    summary = {}
    for key, value in output.items():
        if isinstance(value, dict) and "row_count" in value:
            summary[key] = {k: value[k] for k in ("row_count", "file", "file_hash") if k in value}
        elif isinstance(value, (str, int, float, bool)):
            summary[key] = value
        elif isinstance(value, list) and len(value) <= 5:
            summary[key] = value
        elif isinstance(value, dict) and key in ("summary", "stats"):
            summary[key] = value
        elif key == "report":
            summary[key] = {"title": value.get("title"), "narrative": value.get("narrative", "")[:200]}
    return summary


def get_run(run_id: str) -> dict | None:
    return find_one("runs", lambda r: r["run_id"] == run_id)


def list_runs(limit: int = 20) -> list:
    return load("runs")[-limit:]
