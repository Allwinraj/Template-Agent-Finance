"""
A5 Explain — turns trusted results into an evidence-backed report.

Configuration:
  report: {title, audience}
Behavior:
  - builds tables + summary from A4 output
  - calls the LLM (SAP AI Core) for a narrative explanation
  - every figure links to source evidence refs
"""
from app.agents.base import BaseAgent
from app.llm import explain as llm_explain


class A5Explain(BaseAgent):
    id = "A5"
    name = "Explain"
    description = "Generates evidence-backed reports and explanations."
    version = "v2"

    def config_schema(self) -> dict:
        return {"report.title": "str", "report.audience": "str"}

    def run(self, config: dict, payload: dict, context: dict) -> dict:
        report_cfg = config.get("report", {})
        title = report_cfg.get("title", "Workflow Results")
        summary = payload.get("summary", {})

        # Generic, config-driven tables — columns come from the data itself
        # (comparison keys + calculation results), never hardcoded domain names.
        compared_rows = payload.get("compared_rows", [])
        exceptions = payload.get("exceptions", [])
        calc_keys = sorted({k for c in compared_rows for k in (c.get("calc_results") or {})})

        def flatten_row(c):
            """Top-level join keys + measure values + flattened calc results + status."""
            base = {k: v for k, v in c.items()
                    if k not in ("calc_results", "rule_results", "actions", "evidence")}
            for k in calc_keys:
                base[k] = (c.get("calc_results") or {}).get(k)
            return base

        row_keys = list(flatten_row(compared_rows[0]).keys()) if compared_rows else []
        compared_table = [flatten_row(c) for c in compared_rows]
        exception_rows = [
            {
                **{k: (e.get("row") or {}).get(k) for k in row_keys
                   if k in (e.get("row") or {})},
                "reason": e.get("reason") or e.get("status"),
                "source": f"{(e.get('row') or {}).get('_source_file')}:{(e.get('row') or {}).get('_source_row')}",
            }
            for e in exceptions
        ]
        matches_table = [
            {
                "left_ref": m["evidence"]["left_ref"],
                "right_ref": m["evidence"]["right_ref"],
                "amount": (m.get("left") or {}).get("amount"),
                "score": m.get("score"),
                "status": m.get("status"),
            }
            for m in payload.get("validated_matches", [])
        ]

        # Prefer A4 executive (legend + reasons); else build from rows
        compared_rows = payload.get("compared_rows", [])
        executive_summary = payload.get("executive") or {}
        if not executive_summary:
            status_counts = {}
            for c in compared_rows:
                s = c.get("status") or "unknown"
                status_counts[s] = status_counts.get(s, 0) + 1
            attention = sorted(
                [c for c in compared_rows if c.get("status") in ("review", "exception", "notable")],
                key=lambda c: abs(float((c.get("calc_results") or {}).get("variance") or 0)),
                reverse=True,
            )[:10]
            top_attention = [
                {
                    "gl_account": c.get("gl_account"),
                    "cost_center": c.get("cost_center"),
                    "fiscal_period": c.get("fiscal_period"),
                    "variance": (c.get("calc_results") or {}).get("variance"),
                    "variance_pct": (c.get("calc_results") or {}).get("variance_percentage"),
                    "status": c.get("status"),
                }
                for c in attention
            ]
            executive_summary = {
                "total_compared": summary.get("compared", len(compared_rows)),
                "status_breakdown": status_counts,
                "total_variance": summary.get("total_variance", 0),
                "needs_attention": sum(status_counts.get(s, 0) for s in ("review", "exception", "notable")),
                "top_attention": top_attention,
            }
        status_counts = executive_summary.get("status_breakdown") or {}
        top_attention = executive_summary.get("top_attention") or []

        # LLM narrative via the configured provider (OpenRouter or SAP AI Core)
        prompt = (
            f"Write a short finance summary for '{title}'. "
            f"Stats: {summary}. "
            f"Status breakdown: {status_counts}. "
            f"Top exceptions: {exception_rows[:5]}. "
            f"Rows needing attention (biggest variance): {top_attention[:5]}. "
            f"Compared rows (variance): {compared_table[:8]}. "
            "Explain what needs human attention and why. 3-5 sentences."
        )
        try:
            narrative = llm_explain(prompt, llm_provider=context.get("llm_provider"))
        except Exception as exc:  # noqa: BLE001
            narrative = f"Report generated without LLM narrative ({exc})."

        # Render the user-requested outputs (from the design's output_spec, which
        # mirrors the 'Output:' bullets of the use case). Content is driven by the
        # config: each block's 'source' decides what data it shows.
        #   source: 'summary' | 'results.<id>' | 'exceptions' | 'compared_rows'
        # render types: kpi | table | exceptions | narrative
        def metric_stats(source_key):
            """Aggregate one calc result across all compared rows."""
            vals = [float((c.get("calc_results") or {}).get(source_key) or 0)
                    for c in compared_rows
                    if (c.get("calc_results") or {}).get(source_key) is not None]
            if not vals:
                return {"count": 0}
            return {
                "count": len(vals),
                "total": round(sum(vals), 2),
                "average": round(sum(vals) / len(vals), 2),
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
            }

        def block_table(block):
            block_render = str(block.get("render") or "table")
            source = str(block.get("source") or "")
            if block_render == "exceptions" or source == "exceptions":
                return list(exception_rows[0].keys()) if exception_rows else [], exception_rows
            if source.startswith("results."):
                metric = source.split(".", 1)[1]
                cols = [k for k in row_keys if k not in calc_keys and k != "status"] + [metric, "status"]
                return cols, [{**{k: r.get(k) for k in cols if k != metric},
                               metric: r.get(metric)} for r in compared_table]
            return list(compared_table[0].keys()) if compared_table else [], compared_table

        outputs = []
        for block in (config.get("output_spec") or []):
            render = block.get("render", "table")
            source = str(block.get("source") or "")
            entry = {
                "id": block.get("id"),
                "title": block.get("title"),
                "render": render,
                "description": block.get("description", ""),
                "source": source or None,
            }
            if render == "kpi":
                if source.startswith("results."):
                    entry["data"] = metric_stats(source.split(".", 1)[1])
                else:
                    entry["data"] = {
                        k: summary.get(k) for k in ("compared", "on_track", "notable",
                                                    "review", "exception", "total_variance")
                        if summary.get(k) is not None
                    } or summary
            elif render == "exceptions":
                entry["columns"], entry["rows"] = (
                    (list(exception_rows[0].keys()), exception_rows) if exception_rows else ([], []))
            elif render == "table":
                entry["columns"], entry["rows"] = block_table(block)
            elif render == "narrative":
                block_prompt = (
                    f"Write a finance narrative for the report section '{block.get('title')}'. "
                    f"What this section should explain: {block.get('description') or 'the key results'}. "
                    f"Stats: {summary}. Attention rows: {top_attention[:5]}. "
                    "3-4 sentences, reference the numbers."
                )
                try:
                    entry["text"] = llm_explain(block_prompt, llm_provider=context.get("llm_provider"))
                except Exception as exc:  # noqa: BLE001
                    entry["text"] = narrative
            outputs.append(entry)

        return {
            "report": {
                "title": title,
                "audience": report_cfg.get("audience", "finance_operations"),
                "summary": summary,
                "executive_summary": executive_summary,
                "outputs": outputs,
                "narrative": narrative,
                "tables": {
                    "matches": matches_table,
                    "exceptions": exception_rows,
                    "compared": compared_table,
                },
                "generated_at": self.now(),
            }
        }
