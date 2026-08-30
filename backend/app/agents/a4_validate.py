from __future__ import annotations

"""
A4 Validate — applies the configured rule chain and calculation pipeline,
then recommends an interpretable outcome.

Supports two modes:
  1. match mode   — validates A3 matches + unmatched rows (bank-to-GL style)
  2. compare mode — joins two canonical datasets on comparison_keys and runs
                    the calculation pipeline per joined row (budget-vs-actual etc.)

Compare-mode status tiers (use-case agnostic, threshold-driven via settings):
  on_track  — |var%| < on_track_pct (default 5%) — no action needed
  notable   — on_track_pct <= |var%| < review_pct (default 10%) — glance
  review    — |var%| >= review_pct OR a soft rule failed — finance review
  exception — hard rule fired (material, zero-budget, missing pair) — action

Configuration:
  comparison: {left_role, right_role, keys: [...]}
  calculations: [{id, calculator, input_mapping, output_mapping, depends_on}]
  rules: [{id, params}]
  settings: {materiality, on_track_pct, review_pct, ...}
"""
from app.agents.base import BaseAgent
from app.engines import calculation_engine as ce
from app.engines import rule_engine as re_


def _status_reason(row: dict) -> str:
    """Human-readable why this row got its status (for the attention list)."""
    actions = row.get("actions") or []
    if actions:
        bits = [a.get("detail") or a.get("status") or a.get("rule") for a in actions if a]
        if bits:
            return "; ".join(str(b) for b in bits if b)
    cr = row.get("calc_results") or {}
    pct = cr.get("variance_percentage")
    var = cr.get("variance")
    if pct is not None:
        return f"|variance| {abs(float(pct)):.2f}% (amount {var})"
    if var is not None:
        return f"variance amount {var}"
    return row.get("status") or ""


class A4Validate(BaseAgent):
    id = "A4"
    name = "Validate"
    description = "Runs calculation pipelines and rule chains, recommends an outcome."
    version = "v3"

    def config_schema(self) -> dict:
        return {
            "comparison": "{left_role, right_role, keys}",
            "calculations": "list of {id, calculator, input_mapping, output_mapping, depends_on}",
            "rules": "list of {id, params}",
            "settings": "{materiality, on_track_pct, review_pct, ...}",
        }

    def run(self, config: dict, payload: dict, context: dict) -> dict:
        pipeline = config.get("calculations", [])
        rules = config.get("rules", [])
        settings = config.get("settings", {})
        comparison = config.get("comparison")

        context = {**(context or {}), "settings": settings, "calculation_policy": config.get("calculation_policy") or {}}

        if comparison:
            return self._run_compare(comparison, pipeline, rules, payload, context, settings)
        return self._run_match(pipeline, rules, payload, context)

    # ------------------------------------------------------------------
    # Compare mode
    # ------------------------------------------------------------------

    def _run_compare(self, comparison, pipeline, rules, payload, context, settings) -> dict:
        left_role = comparison.get("left_role", "actuals")
        right_role = comparison.get("right_role", "budget")
        keys = comparison.get("keys", [])

        canonical = payload.get("canonical", {})
        left_rows = canonical.get(left_role, {}).get("rows", [])
        right_rows = canonical.get(right_role, {}).get("rows", [])

        def key_of(row):
            return tuple(str(row.get(k)) for k in keys)

        right_by_key = {key_of(r): r for r in right_rows}

        compared, exceptions = [], []
        for left in left_rows:
            right = right_by_key.get(key_of(left))
            if right is None:
                exceptions.append({
                    "role": left_role,
                    "row": left,
                    "status": "exception",
                    "reason": f"No matching {right_role} record for {dict(zip(keys, key_of(left)))}",
                })
                continue

            joined = {
                **{k: left.get(k) for k in keys},
                left_role: left,
                right_role: right,
            }
            results = ce.run_pipeline(pipeline, joined, context) if pipeline else {}
            rule_context = {**context, "results": results}
            rule_outcome = (
                re_.evaluate_chain(rules, joined, rule_context)
                if rules
                else {"passed": True, "results": [], "actions": []}
            )

            status = self._compare_status(results, rule_outcome, settings)
            compared.append({
                **{k: left.get(k) for k in keys},
                "actual": left.get("amount"),
                "budget": right.get("amount"),
                "calc_results": results,
                "rule_results": rule_outcome.get("results", []),
                "actions": rule_outcome.get("actions", []),
                "status": status,
                "evidence": {
                    "actual_ref": f"{left.get('_source_file')}:{left.get('_source_row')}",
                    "budget_ref": f"{right.get('_source_file')}:{right.get('_source_row')}",
                },
            })

        # right-side rows with no left match
        left_keys = {key_of(l) for l in left_rows}
        for right in right_rows:
            if key_of(right) not in left_keys:
                exceptions.append({
                    "role": right_role,
                    "row": right,
                    "status": "exception",
                    "reason": f"No matching {left_role} for {dict(zip(keys, key_of(right)))}",
                })

        material = [
            c for c in compared
            if any(a.get("status") == "material_exception" for a in c.get("actions", []))
        ]
        zero_budget = [
            c for c in compared
            if any(a.get("status") == "zero_budget_exception" for a in c.get("actions", []))
        ]

        bd = {
            "on_track": sum(1 for c in compared if c["status"] == "on_track"),
            "notable": sum(1 for c in compared if c["status"] == "notable"),
            "review": sum(1 for c in compared if c["status"] == "review"),
            "exception": sum(1 for c in compared if c["status"] == "exception"),
        }
        total_var = round(
            sum(float(c.get("calc_results", {}).get("variance") or 0) for c in compared), 2
        )
        summary = {
            "compared": len(compared),
            "status_breakdown": bd,
            "on_track": bd["on_track"],
            "notable": bd["notable"],
            "review": bd["review"],
            "exception": bd["exception"],
            "matched": bd["on_track"],  # legacy alias
            "requires_review": bd["review"] + bd["exception"],
            "needs_attention": bd["review"] + bd["exception"] + bd["notable"],
            "material_exceptions": len(material),
            "zero_budget_exceptions": len(zero_budget),
            "exceptions": len(exceptions),
            "total_variance": total_var,
        }

        attention = []
        for c in compared:
            if c.get("status") in ("review", "exception", "notable"):
                cr = c.get("calc_results") or {}
                attention.append({
                    **{k: c.get(k) for k in (
                        "gl_account", "cost_center", "fiscal_period",
                        "actual", "budget", "status",
                    )},
                    "variance": cr.get("variance"),
                    "variance_pct": cr.get("variance_percentage"),
                    "reason": _status_reason(c),
                })
        attention.sort(key=lambda r: abs(float(r.get("variance") or 0)), reverse=True)

        executive = {
            "total_compared": len(compared),
            "needs_attention": summary["needs_attention"],
            "status_breakdown": bd,
            "total_variance": total_var,
            "thresholds": {
                "on_track_pct": float((settings or {}).get("on_track_pct", 5) or 5),
                "review_pct": float((settings or {}).get("review_pct", 10) or 10),
                "materiality": float((settings or {}).get("materiality", 0) or 0),
            },
            "top_attention": attention[:10],
            "legend": {
                "on_track": "Variance within acceptable band (default |var%| < 5%) — no action needed",
                "notable": "Moderate variance (default 5–10%) — worth a glance, not urgent",
                "review": "Large variance (default |var%| ≥ 10%) or a soft rule failed — finance should review",
                "exception": "Hard rule fired (e.g. material amount, zero-budget spend, missing pair) — action required",
            },
        }

        return {
            "compared_rows": compared,
            "exceptions": exceptions,
            "material_rows": material,
            "zero_budget_rows": zero_budget,
            "summary": summary,
            "executive": executive,
            "lineage": context.get("lineage", []),
        }

    @staticmethod
    def _compare_status(results: dict, rule_outcome: dict, settings: dict) -> str:
        """Map rule outcome + variance magnitude to an interpretable status."""
        for a in rule_outcome.get("actions", []) or []:
            if a.get("severity") == "high" or a.get("status") in (
                "zero_budget_exception", "material_exception",
            ):
                return "exception"
        if rule_outcome.get("passed") is False:
            return "review"

        # Prefer any percentage-like calc result (not hard-coded to one name)
        pct = results.get("variance_percentage")
        if pct is None:
            for k, v in (results or {}).items():
                if v is None:
                    continue
                lk = str(k).lower()
                if "percent" in lk or lk.endswith("_pct") or lk.endswith("pct"):
                    pct = v
                    break

        if pct is None:
            var = None
            for k, v in (results or {}).items():
                if v is None:
                    continue
                lk = str(k).lower()
                if "variance" in lk or lk in ("difference", "diff", "amount_diff"):
                    var = abs(float(v))
                    break
            if var is None:
                var = abs(float((results or {}).get("variance") or 0))
            materiality = float((settings or {}).get("materiality", 0) or 0)
            if materiality and var >= materiality:
                return "review"
            return "on_track" if var == 0 else "notable"

        pct = abs(float(pct))
        review_pct = float((settings or {}).get("review_pct", 10) or 10)
        on_track_pct = float((settings or {}).get("on_track_pct", 5) or 5)
        if pct >= review_pct:
            return "review"
        if pct >= on_track_pct:
            return "notable"
        return "on_track"

    # ------------------------------------------------------------------
    # Match mode
    # ------------------------------------------------------------------

    def _run_match(self, pipeline, rules, payload, context) -> dict:
        validated = []

        for m in payload.get("matches", []):
            row = {
                "amount_diff": m.get("amount_diff", 0),
                "date_diff": m.get("date_diff", 0),
                "score": m.get("score", 0),
                "confidence": min(
                    (m.get("left") or {}).get("_confidence", 1.0),
                    (m.get("right") or {}).get("_confidence", 1.0),
                ),
                "amount": (m.get("left") or {}).get("amount"),
            }
            results = ce.run_pipeline(pipeline, row, context) if pipeline else {}
            rule_outcome = (
                re_.evaluate_chain(rules, {**row, **results}, context)
                if rules
                else {"passed": True, "results": [], "actions": []}
            )
            status = self._recommend(rule_outcome, m.get("score", 0))
            validated.append({
                **m,
                "calc_results": results,
                "rule_results": rule_outcome["results"],
                "status": status,
            })

        exceptions = []
        for role, rows in (payload.get("unmatched") or {}).items():
            for row in rows:
                results = ce.run_pipeline(pipeline, row, context) if pipeline else {}
                rule_outcome = (
                    re_.evaluate_chain(rules, {**row, **results}, context)
                    if rules
                    else {"passed": True, "results": [], "actions": []}
                )
                exceptions.append({
                    "role": role,
                    "row": row,
                    "calc_results": results,
                    "rule_results": rule_outcome["results"],
                    "status": "exception",
                })

        compared = []
        for role, source in (payload.get("canonical") or {}).items():
            for row in source.get("rows", []):
                results = ce.run_pipeline(pipeline, row, context) if pipeline else {}
                rule_outcome = (
                    re_.evaluate_chain(rules, {**row, **results}, context)
                    if rules
                    else {"passed": True, "results": [], "actions": []}
                )
                status = self._recommend(rule_outcome, 100.0)
                compared.append({
                    **row,
                    "calc_results": results,
                    "rule_results": rule_outcome["results"],
                    "status": status,
                })

        summary = {
            "matched": sum(1 for v in validated if v["status"] == "matched"),
            "requires_review": sum(1 for v in validated if v["status"] == "requires_review"),
            "exceptions": len(exceptions),
            "compared": len(compared),
            "compared_flagged": sum(1 for c in compared if c["status"] != "matched"),
        }

        return {
            "validated_matches": validated,
            "exceptions": exceptions,
            "compared_rows": compared,
            "summary": summary,
            "lineage": context.get("lineage", []),
        }

    @staticmethod
    def _recommend(rule_outcome: dict, score: float) -> str:
        if rule_outcome.get("passed") is False:
            return "requires_review"
        if score and score < 95:
            return "requires_review"
        return "matched"
