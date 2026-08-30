"""
End-to-end tests for Nexus 2.0.

Run:  python -m pytest backend/data/test_e2e.py -v
      (or)  python backend/data/test_e2e.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import orchestrator, registry
from app.services import audit_service, exception_service
from app.engines import calculation_engine as ce
from app.engines import rule_engine as re_
from app.main import seed_default_workflow


def test_calculation_engine():
    """Calculators produce correct values."""
    assert ce.amount_difference(a=100.50, b=99.00) == 1.5
    assert ce.date_difference(date_1="2026-08-01", date_2="2026-08-03") == 2
    assert ce.match_score(amount_diff=0, date_diff=0, ref_match=True) == 100.0
    assert ce.match_score(amount_diff=50, date_diff=5, ref_match=False) < 100.0
    assert ce.calculate_percentage(numerator=25, denominator=100) == 25.0
    assert ce.calculate_percentage(numerator=10, denominator=0) is None
    print("  [PASS] calculation_engine")


def test_rule_engine():
    """Rules evaluate correctly with parameters."""
    row = {"difference": 0.5, "confidence": 0.9, "reference": "INV-001"}
    assert re_.evaluate("tolerance_check", row, {"tolerance": 1.0})["passed"] is True
    assert re_.evaluate("tolerance_check", row, {"tolerance": 0.1})["passed"] is False
    assert re_.evaluate("low_confidence_review", row, {"threshold": 0.8})["passed"] is True
    assert re_.evaluate("low_confidence_review", row, {"threshold": 0.95})["passed"] is False
    assert re_.evaluate("required_field", row, {"fields": ["reference"]})["passed"] is True
    assert re_.evaluate("required_field", row, {"fields": ["missing_field"]})["passed"] is False
    print("  [PASS] rule_engine")


def test_rule_chain():
    """evaluate_chain runs multiple rules and aggregates."""
    row = {"difference": 0.5, "confidence": 0.9, "reference": "INV-001"}
    rules = [
        {"id": "tolerance_check", "params": {"tolerance": 1.0}},
        {"id": "low_confidence_review", "params": {"threshold": 0.8}},
    ]
    outcome = re_.evaluate_chain(rules, row, {})
    assert outcome["passed"] is True
    assert len(outcome["results"]) == 2
    print("  [PASS] rule_chain")


def test_seed_and_run():
    """Seed the default workflow and run it end-to-end."""
    seed_default_workflow()
    wfs = registry.list_all()
    assert len(wfs) >= 1
    wf = wfs[0]
    assert wf["status"] == "published"

    result = orchestrator.run_workflow(wf["workflow_id"])
    assert result["state"] in ("completed", "waiting_for_human")
    assert len(result["steps"]) == 6
    assert [s["agent_id"] for s in result["steps"]] == ["A1", "A2", "A3", "A4", "A5", "A6"]

    summary = result["result"]["summary"]
    assert summary["matched"] > 0
    assert summary["exceptions"] >= 1  # the duplicate + unmatched rows
    print(f"  [PASS] seed_and_run (matched={summary['matched']}, exceptions={summary['exceptions']})")


def test_audit_trail():
    """Audit events are recorded for the run."""
    events = audit_service.all_events(limit=50)
    assert any(e["event_type"] == "workflow_started" for e in events)
    assert any(e["event_type"] == "workflow_completed" for e in events)
    print("  [PASS] audit_trail")


def test_exceptions():
    """Exception service creates and deduplicates review tasks."""
    exc = exception_service.create({
        "business_key": "test-key-1",
        "run_id": "test-run",
        "type": "unmatched_record",
        "severity": "medium",
        "status": "assigned",
        "owner_queue": "finance_operations",
        "assigned_to": "reviewer-17",
        "reason": "test exception",
        "proposed_action": "review",
        "evidence": ["file.csv:1"],
    })
    assert exc["exception_id"].startswith("exc-")

    # duplicate should return same record
    exc2 = exception_service.create({
        "business_key": "test-key-1",
        "run_id": "test-run",
        "type": "unmatched_record",
        "severity": "medium",
        "status": "assigned",
        "owner_queue": "finance_operations",
        "assigned_to": "reviewer-17",
        "reason": "test exception",
        "proposed_action": "review",
        "evidence": ["file.csv:1"],
    })
    assert exc["id"] == exc2["id"]
    print("  [PASS] exceptions")


def test_agents_list():
    """All six agents are registered with capability cards."""
    from app.services.orchestrator import AGENT_REGISTRY
    assert set(AGENT_REGISTRY.keys()) == {"A1", "A2", "A3", "A4", "A5", "A6"}
    for agent in AGENT_REGISTRY.values():
        card = agent.card()
        assert "id" in card and "name" in card and "config_schema" in card
    print("  [PASS] agents_list")


if __name__ == "__main__":
    print("Running Nexus 2.0 end-to-end tests...")
    test_calculation_engine()
    test_rule_engine()
    test_rule_chain()
    test_seed_and_run()
    test_audit_trail()
    test_exceptions()
    test_agents_list()
    print("\n[PASS] All tests passed!")
