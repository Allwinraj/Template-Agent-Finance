from __future__ import annotations

"""
Calculation Engine — versioned, typed calculators with DAG pipelines.

Calculators are generic: they receive values resolved from the workflow's
input_mapping (which binds canonical field names to calculator inputs).
Changing the mapping in the UI changes behavior without code changes.

Pipeline features (README §8):
  - depends_on DAG with topological execution + cycle detection
  - field resolution: results.X, settings.X, dataset.X, nested a.b, plain X
  - output_mapping: results.<name>
  - lineage: every result records calculator, version, inputs_used, depends_on
"""
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Calculator implementations. Each takes plain keyword args resolved from the
# workflow config's input_mapping. All are deterministic and versioned.
# ---------------------------------------------------------------------------


def subtract_values(*, value_1: float, value_2: float, context: dict | None = None) -> float:
    """value_1 - value_2"""
    return round(float(value_1 or 0) - float(value_2 or 0), _decimal_places(context))


def add_values(*, value_1: float, value_2: float, context: dict | None = None) -> float:
    """value_1 + value_2"""
    return round(float(value_1 or 0) + float(value_2 or 0), _decimal_places(context))


def multiply_values(*, value_1: float, value_2: float, context: dict | None = None) -> float:
    """value_1 * value_2"""
    return round(float(value_1 or 0) * float(value_2 or 0), _decimal_places(context))


def divide_values(*, numerator: float, denominator: float, context: dict | None = None):
    """numerator / denominator (None-safe)."""
    policy = (context or {}).get("calculation_policy") or {}
    zero_mode = policy.get("zero_denominator", "create_exception")
    try:
        denom = float(denominator)
        if denom == 0:
            if zero_mode == "return_null":
                return None
            if zero_mode == "skip":
                return None
            return None
        return round(float(numerator) / denom, _decimal_places(context))
    except (TypeError, ZeroDivisionError):
        return None


def _as_list(values):
    """Normalize an aggregation input: accept a list, a scalar, or None."""
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        return list(values)
    return [values]  # scalar — treat as a single-value list


def calculate_sum(*, values, context: dict | None = None) -> float:
    """Sum a list of numbers (a scalar is treated as a single value)."""
    return round(sum(float(v or 0) for v in _as_list(values)), _decimal_places(context))


def calculate_count(*, values) -> int:
    """Count non-empty values (a scalar counts as 1)."""
    return sum(1 for v in _as_list(values) if v not in (None, ""))


def calculate_percentage(*, numerator: float, denominator: float, context: dict | None = None):
    """numerator / denominator * 100 (None-safe)."""
    policy = (context or {}).get("calculation_policy") or {}
    zero_mode = policy.get("zero_denominator", "create_exception")
    try:
        denom = float(denominator)
        if denom == 0:
            if zero_mode == "return_null":
                return None
            if zero_mode == "skip":
                return None
            return None
        return round(float(numerator) / denom * 100, _decimal_places(context))
    except (TypeError, ZeroDivisionError):
        return None


def amount_difference(*, a: float, b: float, context: dict | None = None) -> float:
    """Absolute difference between two amounts."""
    return round(abs(float(a or 0) - float(b or 0)), _decimal_places(context))


def date_difference(*, date_1, date_2):
    """Days between two dates (absolute)."""
    d1 = _to_date(date_1)
    d2 = _to_date(date_2)
    if d1 is None or d2 is None:
        return None
    return abs((d1 - d2).days)


def match_score(*, amount_diff: float = 0.0, date_diff: int = 0, ref_match: bool = True, context: dict | None = None) -> float:
    """Weighted 0-100 score from amount, date and reference similarity."""
    score = 100.0
    score -= min(abs(float(amount_diff or 0)) / 100.0, 30)   # up to -30
    score -= min(abs(int(date_diff or 0)) * 2, 20)           # up to -20
    if not ref_match:
        score -= 20
    return max(0.0, round(score, _decimal_places(context)))


def calculate_variance(*, actual: float, budget: float, context: dict | None = None) -> float:
    """actual - budget (signed)."""
    return round(float(actual or 0) - float(budget or 0), _decimal_places(context))


def calculate_variance_percentage(*, variance: float, budget: float, context: dict | None = None):
    """variance / budget * 100 (None-safe)."""
    return calculate_percentage(numerator=variance, denominator=budget, context=context)


def calculate_materiality(*, variance: float, threshold: float, context: dict | None = None) -> bool:
    """True when |variance| exceeds the materiality threshold."""
    return abs(float(variance or 0)) > float(threshold or 0)


def calculate_aging_days(*, transaction_date, current_date=None):
    """Days between transaction_date and current_date (default: today)."""
    d1 = _to_date(transaction_date)
    if d1 is None:
        return None
    d2 = _to_date(current_date) if current_date else date.today()
    if d2 is None:
        return None
    return (d2 - d1).days


def calculate_fx_conversion(*, amount: float, rate: float, context: dict | None = None) -> float:
    """amount * fx rate."""
    return round(float(amount or 0) * float(rate or 1), _decimal_places(context))


def calculate_reconciliation_difference(*, bank_total: float, gl_total: float, context: dict | None = None) -> float:
    """bank_total - gl_total (signed)."""
    return round(float(bank_total or 0) - float(gl_total or 0), _decimal_places(context))


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _decimal_places(context: dict | None) -> int:
    policy = (context or {}).get("calculation_policy") or {}
    try:
        return int(policy.get("decimal_places", 2))
    except (TypeError, ValueError):
        return 2


# Registry: name -> metadata (MCP-style typed tools)
CALCULATORS: dict = {
    "subtract_values": {
        "fn": subtract_values, "version": 1, "category": "arithmetic",
        "desc": "value_1 - value_2", "inputs": ["value_1", "value_2"],
        "allowed_agents": ["A3", "A4"],
    },
    "add_values": {
        "fn": add_values, "version": 1, "category": "arithmetic",
        "desc": "value_1 + value_2", "inputs": ["value_1", "value_2"],
        "allowed_agents": ["A3", "A4"],
    },
    "multiply_values": {
        "fn": multiply_values, "version": 1, "category": "arithmetic",
        "desc": "value_1 * value_2", "inputs": ["value_1", "value_2"],
        "allowed_agents": ["A3", "A4"],
    },
    "divide_values": {
        "fn": divide_values, "version": 1, "category": "arithmetic",
        "desc": "numerator / denominator (None-safe)", "inputs": ["numerator", "denominator"],
        "allowed_agents": ["A3", "A4"],
    },
    "calculate_sum": {
        "fn": calculate_sum, "version": 1, "category": "aggregate",
        "desc": "Sum a list of values", "inputs": ["values"],
        "allowed_agents": ["A4"],
    },
    "calculate_count": {
        "fn": calculate_count, "version": 1, "category": "aggregate",
        "desc": "Count non-empty values", "inputs": ["values"],
        "allowed_agents": ["A1", "A4"],
    },
    "calculate_percentage": {
        "fn": calculate_percentage, "version": 1, "category": "finance_calculation",
        "desc": "numerator / denominator * 100", "inputs": ["numerator", "denominator"],
        "allowed_agents": ["A3", "A4"],
    },
    "amount_difference": {
        "fn": amount_difference, "version": 1, "category": "matching",
        "desc": "Absolute difference between two amounts", "inputs": ["a", "b"],
        "allowed_agents": ["A3", "A4"],
    },
    "date_difference": {
        "fn": date_difference, "version": 1, "category": "matching",
        "desc": "Days between two dates", "inputs": ["date_1", "date_2"],
        "allowed_agents": ["A3", "A4"],
    },
    "match_score": {
        "fn": match_score, "version": 3, "category": "matching",
        "desc": "Weighted 0-100 score from amount/date/reference similarity",
        "inputs": ["amount_diff", "date_diff", "ref_match"],
        "allowed_agents": ["A3"],
    },
    "calculate_variance": {
        "fn": calculate_variance, "version": 1, "category": "finance_calculation",
        "desc": "actual - budget (signed)", "inputs": ["actual", "budget"],
        "allowed_agents": ["A4"],
    },
    "calculate_variance_percentage": {
        "fn": calculate_variance_percentage, "version": 1, "category": "finance_calculation",
        "desc": "variance / budget * 100", "inputs": ["variance", "budget"],
        "allowed_agents": ["A4"],
    },
    "calculate_materiality": {
        "fn": calculate_materiality, "version": 1, "category": "control",
        "desc": "|variance| > threshold", "inputs": ["variance", "threshold"],
        "allowed_agents": ["A4"],
    },
    "calculate_aging_days": {
        "fn": calculate_aging_days, "version": 1, "category": "finance_calculation",
        "desc": "Days between transaction_date and current_date", "inputs": ["transaction_date", "current_date"],
        "allowed_agents": ["A4", "A6"],
    },
    "calculate_fx_conversion": {
        "fn": calculate_fx_conversion, "version": 1, "category": "finance_calculation",
        "desc": "amount * fx rate", "inputs": ["amount", "rate"],
        "allowed_agents": ["A2", "A4"],
    },
    "calculate_reconciliation_difference": {
        "fn": calculate_reconciliation_difference, "version": 1, "category": "finance_calculation",
        "desc": "bank_total - gl_total (signed)", "inputs": ["bank_total", "gl_total"],
        "allowed_agents": ["A3", "A4"],
    },
}


def list_calculators() -> list:
    """MCP-style tool listing for the UI."""
    return [
        {
            "name": name,
            "version": meta["version"],
            "category": meta["category"],
            "description": meta["desc"],
            "inputs": meta["inputs"],
            "allowed_agents": meta["allowed_agents"],
        }
        for name, meta in sorted(CALCULATORS.items())
    ]


# ---------------------------------------------------------------------------
# Field resolution
# ---------------------------------------------------------------------------

def _resolve(row: dict, context: dict, key: str):
    """
    Resolve a value from the row, context, or dotted path.

    Supported paths:
      results.<calc_id>     -> context["results"][calc_id]
      settings.<key>        -> context["settings"][key]
      dataset.<field>       -> row[field]
      a.b.c                 -> nested dict lookup in row
      <field>               -> row[field], then context
    """
    if not isinstance(key, str):
        return key

    parts = key.split(".")
    results = (context or {}).get("results", {})
    settings = (context or {}).get("settings", {})

    if len(parts) >= 2 and parts[0] == "results":
        return results.get(".".join(parts[1:]))
    if len(parts) >= 2 and parts[0] == "settings":
        return settings.get(".".join(parts[1:]))
    if len(parts) >= 2 and parts[0] == "dataset":
        return _nested_get(row, parts[1:])
    if key in (row or {}):
        return row[key]
    if key in (context or {}):
        return context[key]
    # nested dict path in row (e.g. actual.amount)
    nested = _nested_get(row, parts)
    if nested is not None:
        return nested
    return None


def _nested_get(obj, parts):
    cur = obj
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def execute(calculator: str, input_mapping: dict, row: dict, context: dict | None = None):
    """
    Execute one calculator.

    input_mapping example: {"value_1": "actual.amount", "value_2": "budget.amount"}
    """
    if calculator not in CALCULATORS:
        raise ValueError(f"Unknown calculator: {calculator}")
    meta = CALCULATORS[calculator]
    kwargs = {}
    inputs_used = {}
    for input_name in meta["inputs"]:
        source = input_mapping.get(input_name, input_name)
        value = _resolve(row, context, source)
        kwargs[input_name] = value
        inputs_used[input_name] = {"source": source, "value": value}
    kwargs["context"] = context
    result = meta["fn"](**kwargs)
    return result, inputs_used


# ---------------------------------------------------------------------------
# DAG pipeline execution
# ---------------------------------------------------------------------------

def _topological_order(pipeline: list) -> list:
    """Order pipeline steps so dependencies run first. Raises on cycles."""
    ids = [s["id"] for s in pipeline]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate calculation step IDs in pipeline")

    id_set = set(ids)
    deps = {}
    for step in pipeline:
        d = [x for x in step.get("depends_on", []) if x in id_set]
        deps[step["id"]] = d
        for x in d:
            if x not in id_set:
                raise ValueError(f"Step {step['id']} depends on unknown step {x}")

    ordered, visited, visiting = [], set(), set()

    def visit(step_id):
        if step_id in visited:
            return
        if step_id in visiting:
            raise ValueError(f"Circular dependency detected involving '{step_id}'")
        visiting.add(step_id)
        for d in deps[step_id]:
            visit(d)
        visiting.remove(step_id)
        visited.add(step_id)
        ordered.append(step_id)

    for s in pipeline:
        visit(s["id"])

    by_id = {s["id"]: s for s in pipeline}
    return [by_id[i] for i in ordered]


def run_pipeline(pipeline: list, row: dict, context: dict | None = None) -> dict:
    """
    Execute a chained calculation pipeline with DAG dependencies.

    Later steps can reference earlier outputs via input_mapping paths like
    'results.variance'. Returns {calc_id: result} for all steps.

    Each step may declare:
      id, calculator, input_mapping, output_mapping, depends_on
    """
    context = dict(context or {})
    context.setdefault("results", {})
    lineage = context.setdefault("lineage", [])

    for step in _topological_order(pipeline):
        calc_id = step["id"]
        calc_name = step["calculator"]
        if calc_name not in CALCULATORS:
            raise ValueError(f"Unknown calculator in pipeline: {calc_name}")
        meta = CALCULATORS[calc_name]
        mapping = step.get("input_mapping", {})
        kwargs = {}
        inputs_used = {}
        for input_name in meta["inputs"]:
            source = mapping.get(input_name, input_name)
            value = _resolve(row, context, source)
            kwargs[input_name] = value
            inputs_used[input_name] = {"source": source, "value": value}
        # only pass context to calculators that declare it in their signature
        import inspect
        if "context" in inspect.signature(meta["fn"]).parameters:
            kwargs["context"] = context
        result = meta["fn"](**kwargs)
        context["results"][calc_id] = result

        # output_mapping: {"result": "results.variance"} -> also store under alias
        out_alias = (step.get("output_mapping") or {}).get("result")
        if out_alias and isinstance(out_alias, str) and out_alias.startswith("results."):
            context["results"][out_alias.split(".", 1)[1]] = result

        lineage.append({
            "calculation_id": calc_id,
            "calculator": calc_name,
            "calculator_version": meta["version"],
            "depends_on": step.get("depends_on", []),
            "inputs": inputs_used,
            "result": {"output": out_alias or f"results.{calc_id}", "value": result},
        })

    return context["results"]


def validate_pipeline(pipeline: list) -> list:
    """Validate a calculation pipeline config. Returns a list of errors."""
    errors = []
    ids = [s.get("id") for s in pipeline]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate calculation step IDs")
    id_set = set(ids)
    for step in pipeline:
        if step.get("calculator") not in CALCULATORS:
            errors.append(f"Step '{step.get('id')}': unknown calculator '{step.get('calculator')}'")
        for dep in step.get("depends_on", []):
            if dep not in id_set:
                errors.append(f"Step '{step.get('id')}': depends on unknown step '{dep}'")
    try:
        _topological_order(pipeline)
    except ValueError as exc:
        errors.append(str(exc))
    return errors