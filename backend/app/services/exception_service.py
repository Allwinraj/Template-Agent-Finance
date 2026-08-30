from __future__ import annotations

"""Exception Service — durable work items for human review (README §3B)."""
from datetime import datetime, timezone

from app import storage


def create(data: dict) -> dict:
    """Create an exception, deduplicated by business_key + run_id."""
    existing = storage.find_one(
        "exceptions",
        lambda e: e.get("business_key") == data.get("business_key")
        and e.get("run_id") == data.get("run_id"),
    )
    if existing:
        return existing  # idempotent: no duplicate tasks on retry

    exc = {
        **data,
        "exception_id": f"exc-{len(storage.load('exceptions')) + 10001}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return storage.insert("exceptions", exc)


def list_open(queue: str | None = None) -> list:
    items = storage.find("exceptions", lambda e: e.get("status") not in ("resolved", "rejected", "cancelled"))
    if queue:
        items = [e for e in items if e.get("owner_queue") == queue]
    return items


def decide(exception_id: str, decision: str, comment: str = "", decided_by: str = "") -> dict | None:
    """Record a human decision: accept / reject / correct / request_information."""
    exc = storage.find_one("exceptions", lambda e: e.get("exception_id") == exception_id)
    if not exc:
        return None
    new_status = {
        "accept": "resolved",
        "reject": "rejected",
        "correct": "resolved",
        "request_information": "waiting_for_information",
    }.get(decision, "in_review")
    updated = storage.update(
        exc["id"],
        {
            "status": new_status,
            "decision": decision,
            "decision_comment": comment,
            "decided_by": decided_by,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    audit_service.record(
        "human_decision",
        run_id=exc.get("run_id", ""),
        actor_id=decided_by or "reviewer",
        agent_id="A6",
        capability_id="exception_decision",
        output={"exception_id": exception_id, "decision": decision},
    )
    return updated


# imported late to avoid circular import
from app.services import audit_service  # noqa: E402