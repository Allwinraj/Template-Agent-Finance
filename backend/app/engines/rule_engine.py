from __future__ import annotations

"""
Rule Engine — reusable, parameterized rules with declarative pipelines.

Rules are generic and take their parameters from the workflow config, so
thresholds/fields are changeable from the UI without code changes.

Features (README §7):
  - params may reference settings: {"threshold": "settings.materiality"}
  - rules consume source fields, calculation outputs (results.X), and
    earlier rule results (rule_results.X)
  - structured outputs: {status, action, queue, severity}
  - rule_pipeline: declarative steps with depends_on + condition + output
"""
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Param resolution: params like "settings.materiality" resolve from context
# ---------------------------------------------------------------------------


def _resolve_param(value, context: dict):
    """Resolve a param value; strings like 'settings.X' come from context."""
    if isinstance(value, str) and value.startswith("settings."):
        return (context or {}).get("settings", {}).get(value.split(".", 1)[1])
    if isinstance(value, str) and value.startswith("results."):
        return (context or {}).get("results", {}).get(value.split(".", 1)[1])
    return value


def _get_field(row: dict, context: dict, key):
    """Resolve a field: results.X, rule_results.X.Y, nested a.b, or plain."""
    if not isinstance(key, str):
        return key
    parts = key.split(".")
    if parts[0] == "results" and len(parts) >= 2:
        return (context or {}).get("results", {}).get(".".join(parts[1:]))
    if parts[0] == "rule_results" and len(parts) >= 3:
        rr = (context or {}).get("rule_results", {}).get(parts[1], {})
        return rr.get(".".join(parts[2:])) if len(parts) == 3 else rr.get(parts[2])
    if key in (row or {}):
        return row[key]
    cur = row
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


# ---------------------------------------------------------------------------
# Rule implementations. Each receives (row, params, context) -> outcome dict.
# All are deterministic and versioned.
# ---------------------------------------------------------------------------


def _tolerance_check(row, params, context):
    field = params.get("field", "difference")
    diff = abs(float(_get_field(row, context, field) or 0))
    tol = float(_resolve_param(params.get("tolerance", 1.0), context) or 1.0)
    return {
        "rule": "tolerance_check",
        "passed": diff <= tol,
        "detail": f"|{field}| {diff:.2f} vs tolerance {tol:.2f}",
    }


def _material_variance(row, params, context):
    field = params.get("field", "results.variance")
    value = abs(float(_get_field(row, context, field) or 0))
    threshold = float(_resolve_param(params.get("threshold", 10000), context) or 0)
    passed = value <= threshold
    return {
        "rule": "material_variance",
        "passed": passed,
        "detail": f"|{field}| {value:.2f} vs materiality {threshold:.2f}",
        "output": {} if passed else {"status": "material_exception", "severity": "high"},
    }


def _low_confidence(row, params, context):
    threshold = float(_resolve_param(params.get("threshold", 0.8), context) or 0.8)
    confidence = float(row.get("confidence", row.get("_confidence", 1.0)) or 0)
    return {
        "rule": "low_confidence_review",
        "passed": confidence >= threshold,
        "detail": f"confidence {confidence:.2f} vs {threshold}",
    }


def _required_field(row, params, context):
    fields = params.get("fields", [])
    missing = [f for f in fields if row.get(f) in (None, "", "—")]
    return {
        "rule": "required_field",
        "passed": not missing,
        "detail": f"missing: {missing}" if missing else "all present",
    }


def _duplicate_check(row, params, context):
    keys = params.get("keys", ["reference"])
    key = tuple(str(row.get(f)) for f in keys)
    seen = context.setdefault("_seen", set())
    if key in seen:
        return {"rule": "duplicate_check", "passed": False, "detail": f"duplicate {key}"}
    seen.add(key)
    return {"rule": "duplicate_check", "passed": True, "detail": "unique"}


def _zero_budget(row, params, context):
    budget_field = params.get("budget_field", "budget.amount")
    actual_field = params.get("actual_field", "actuals.amount")
    budget = float(_get_field(row, context, budget_field) or 0)
    actual = float(_get_field(row, context, actual_field) or 0)
    passed = not (budget == 0 and actual != 0)
    return {
        "rule": "zero_budget_exception",
        "passed": passed,
        "detail": "zero budget with actual spend" if not passed else "ok",
        "output": {} if passed else {"status": "zero_budget_exception", "severity": "medium"},
    }


# Registry: name -> metadata (MCP-style typed tools)
RULES: dict = {
    "tolerance_check": {
        "fn": _tolerance_check, "version": 2, "category": "matching",
        "desc": "Passes when |difference| <= tolerance",
        "params": {"tolerance": 1.0, "field": "difference"},
    },
    "material_variance": {
        "fn": _material_variance, "version": 3, "category": "accounting_control",
        "desc": "Flags variance above materiality threshold",
        "params": {"threshold": "settings.materiality", "field": "results.variance"},
    },
    "low_confidence_review": {
        "fn": _low_confidence, "version": 1, "category": "data_quality",
        "desc": "Routes low-confidence records to review",
        "params": {"threshold": 0.8},
    },
    "required_field": {
        "fn": _required_field, "version": 1, "category": "data_quality",
        "desc": "Fails when required fields are missing",
        "params": {"fields": []},
    },
    "duplicate_check": {
        "fn": _duplicate_check, "version": 1, "category": "data_quality",
        "desc": "Flags duplicate keys in dataset",
        "params": {"keys": ["reference"]},
    },
    "zero_budget_exception": {
        "fn": _zero_budget, "version": 1, "category": "accounting_control",
        "desc": "Flags actuals against a zero budget",
        "params": {"budget_field": "budget.amount", "actual_field": "actuals.amount"},
    },
}


def list_rules() -> list:
    """MCP-style rule listing for the UI."""
    return [
        {
            "name": name,
            "version": meta["version"],
            "category": meta["category"],
            "description": meta["desc"],
            "params": meta["params"],
        }
        for name, meta in sorted(RULES.items())
    ]


def evaluate(rule_id: str, row: dict, params: dict, context: dict | None = None) -> dict:
    """Evaluate one rule against a row with parameters from workflow config."""
    if rule_id not in RULES:
        return {"rule": rule_id, "passed": None, "detail": f"unknown rule {rule_id}"}
    meta = RULES[rule_id]
    merged = {**meta["params"], **(params or {})}
    return meta["fn"](row, merged, context or {})


def evaluate_chain(rules: list, row: dict, context: dict | None = None) -> dict:
    """
    Run a chain of rules; returns {passed, results, actions}.
    A failed rule means the row needs review or is an exception.
    Rule outputs (status/action/queue) are collected into 'actions'.
    """
    context = dict(context or {})
    context.setdefault("rule_results", {})
    outcomes = []
    actions = []
    for rule in rules:
        rule_id = rule["id"] if isinstance(rule, dict) else rule
        params = rule.get("params", {}) if isinstance(rule, dict) else {}
        if rule_id not in RULES:
            outcomes.append({"rule": rule_id, "passed": None, "detail": "unknown rule"})
            continue
        meta = RULES[rule_id]
        merged = {**meta["params"], **(params or {})}
        outcome = meta["fn"](row, merged, context)
        outcomes.append(outcome)
        context["rule_results"][rule_id] = outcome
        if not outcome.get("passed", True) and outcome.get("output"):
            actions.append({"rule": rule_id, **outcome["output"]})
    return {
        "passed": all(o["passed"] for o in outcomes if o["passed"] is not None),
        "results": outcomes,
        "actions": actions,
    }


# ---------------------------------------------------------------------------
# Declarative rule pipeline (README §7 chained rules)
# ---------------------------------------------------------------------------

OPERATORS = {
    "equals": lambda a, b: a == b,
    "not_equals": lambda a, b: a != b,
    "greater_than": lambda a, b: a is not None and b is not None and a > b,
    "less_than": lambda a, b: a is not None and b is not None and a < b,
    "greater_than_or_equal": lambda a, b: a is not None and b is not None and a >= b,
    "less_than_or_equal": lambda a, b: a is not None and b is not None and a <= b,
    "between": lambda a, b: a is not None and isinstance(b, (list, tuple)) and b[0] <= a <= b[1],
    "is_empty": lambda a, b: a in (None, "", []),
    "is_not_empty": lambda a, b: a not in (None, "", []),
    "contains": lambda a, b: a is not None and b in a,
    "in_list": lambda a, b: a in (b or []),
}


def _evaluate_condition(condition: dict, row: dict, context: dict) -> bool:
    field = condition.get("field")
    operator = condition.get("operator", "equals")
    value = _resolve_param(condition.get("value"), context)
    actual = _get_field(row, context, field)
    fn = OPERATORS.get(operator)
    if fn is None:
        raise ValueError(f"Unknown rule operator: {operator}")
    try:
        return bool(fn(actual, value))
    except TypeError:
        return False


def run_rule_pipeline(pipeline: list, row: dict, context: dict | None = None) -> dict:
    """
    Execute a declarative rule pipeline with depends_on DAG.

    Each step: {id, depends_on, condition: {field, operator, value}, output: {...}}
    When the condition is TRUE, the step's output is emitted as an action.
    Returns {passed, results, actions}.
    """
    from app.engines.calculation_engine import _topological_order

    context = dict(context or {})
    context.setdefault("rule_results", {})
    results, actions = [], []

    for step in _topological_order(pipeline):
        step_id = step["id"]
        condition = step.get("condition", {})
        triggered = _evaluate_condition(condition, row, context) if condition else True
        output = step.get("output", {}) if triggered else {}
        outcome = {
            "rule": step_id,
            "passed": not triggered,  # triggered condition = rule fired = needs attention
            "triggered": triggered,
            "detail": f"condition {condition.get('field')} {condition.get('operator')} {condition.get('value')}",
            "output": output,
        }
        results.append(outcome)
        context["rule_results"][step_id] = outcome
        if triggered and output:
            actions.append({"rule": step_id, **output})

    return {
        "passed": not any(r["triggered"] for r in results),
        "results": results,
        "actions": actions,
    }