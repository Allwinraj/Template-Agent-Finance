"""
A6 Coordinate — routes exceptions to human review queues.

Configuration:
  routing: {unmatched: queue, high_value: queue, ...}
Behavior:
  - creates review tasks for exceptions (deduplicated by business key)
  - assigns queue/severity, records notifications
  - collects human decisions (via API) and returns them to the orchestrator
"""
import uuid

from app.agents.base import BaseAgent
from app.services import exception_service


class A6Coordinate(BaseAgent):
    id = "A6"
    name = "Coordinate"
    description = "Creates review tasks, routes to queues, collects human decisions."
    version = "v2"

    def config_schema(self) -> dict:
        return {"routing": "{exception_type: queue_name}"}

    def run(self, config: dict, payload: dict, context: dict) -> dict:
        routing = config.get("routing", {})
        run_id = context.get("run_id", "unknown")
        workflow_id = context.get("workflow_id", "unknown")
        tasks = []

        for exc in payload.get("exceptions", []):
            row = exc.get("row") or {}
            high_value = abs(float(row.get("amount") or 0)) > float(routing.get("high_value_threshold", 100000))
            queue = routing.get("high_value" if high_value else "unmatched", "finance_operations")
            business_key = f"{workflow_id}:{row.get('company_code', '1000')}:{row.get('_source_file')}:{row.get('_source_row')}"

            record = exception_service.create(
                {
                    "business_key": business_key,
                    "run_id": run_id,
                    "type": "unmatched_record",
                    "severity": "high" if high_value else "medium",
                    "status": "assigned",
                    "owner_queue": queue,
                    "assigned_to": "reviewer-17",
                    "reason": f"No counterpart found for {row.get('reference')} (amount {row.get('amount')})",
                    "proposed_action": "Review and accept, reject, or correct",
                    "evidence": [f"{row.get('_source_file')}:{row.get('_source_row')}"],
                }
            )
            tasks.append(record)

        # also route flagged compared rows (budget-style)
        for c in payload.get("compared_rows", []):
            if c.get("status") == "requires_review":
                business_key = f"{workflow_id}:{c.get('company_code', '1000')}:{c.get('_source_file')}:{c.get('_source_row')}"
                record = exception_service.create(
                    {
                        "business_key": business_key,
                        "run_id": run_id,
                        "type": "rule_exception",
                        "severity": "medium",
                        "status": "assigned",
                        "owner_queue": routing.get("unmatched", "finance_operations"),
                        "assigned_to": "reviewer-17",
                        "reason": "; ".join(
                            r.get("detail", "") for r in c.get("rule_results", []) if not r.get("passed")
                        ) or "flagged by rules",
                        "proposed_action": "Review variance",
                        "evidence": [f"{c.get('_source_file')}:{c.get('_source_row')}"],
                    }
                )
                tasks.append(record)

        return {
            "review_tasks": tasks,
            "tasks_created": len(tasks),
            "queues": sorted({t["owner_queue"] for t in tasks}),
        }