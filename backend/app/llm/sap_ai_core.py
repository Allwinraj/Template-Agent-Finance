"""
SAP AI Core LLM client.

Uses the Generative AI Hub (OpenAI-compatible chat completions) through a
SAP AI Core deployment. When credentials are missing in .env, falls back to
deterministic mock responses so the whole platform works offline.
"""
from __future__ import annotations

import json
import logging
import time

import requests

from app.config import (
    SAP_AICORE_AUTH_URL,
    SAP_AICORE_CLIENT_ID,
    SAP_AICORE_CLIENT_SECRET,
    SAP_AICORE_DEPLOYMENT_URL,
    SAP_AICORE_MODEL,
    SAP_AICORE_RESOURCE_GROUP,
    aicore_configured,
)

logger = logging.getLogger("nexus.llm.sap_ai_core")

_token_cache: dict = {"token": None, "expires": 0}

_last_model_used: str | None = None

SYSTEM_WORKFLOW = (
    "OUTPUT RULE: JSON ONLY. No markdown, no code fences, no preamble, no explanation, no thinking process. "
    "If you output non-JSON text, the system will retry and your response will be wasted.\n\n"
    "You design finance workflow configs for Nexus 2.0. Six reusable agents: "
    "A1 Capture, A2 Harmonize, A3 Match, A4 Validate, A5 Explain, A6 Coordinate. "
    "Canonical fields: transaction_date, amount, currency, reference, description, "
    "company_code, gl_account, cost_center, fiscal_period, vendor, employee_id, category, document_no. "
    "Available calculators: subtract_values, add_values, multiply_values, divide_values, calculate_sum, "
    "calculate_count, calculate_percentage, amount_difference, date_difference, match_score, "
    "calculate_variance, calculate_variance_percentage, calculate_materiality, calculate_aging_days, "
    "calculate_fx_conversion, calculate_reconciliation_difference. "
    "Available rules: tolerance_check, material_variance, low_confidence_review, "
    "required_field, duplicate_check, zero_budget_exception. "
    "\n\n"
    "The user description has three sections: Description (what to do), Input (data files), Output (expected results). "
    "Use ALL three. Every Output bullet MUST map to a calculation, rule, or report block. "
    "\n\n"
    "Return JSON with these keys: "
    "name, description, agents (A1..A6 subset), sources (list of {role, file, field_mappings}), "
    "comparison {left_role, right_role, keys} (only when two datasets are compared), "
    "calculations (list of {id, calculator, version, used_by:'A4', scope, input_mapping, output_mapping:{result:'results.<id>'}, depends_on:[]}), "
    "rules (list of {id, version, params}), settings (object), settings_schema (list of {key, label, type, default, unit, description}), "
    "output_spec (list of {id, title, render:'kpi'|'table'|'exceptions'|'narrative', description, source}), "
    "routing, report {title, audience}, agent_configs, explanation. "
    "\n\n"
    "RULES: "
    "- calculations: one or more steps PER output bullet needing computed values. depends_on required ([] if none). "
    "Bind inputs to source columns using exact uploaded column names with the file's role prefix (e.g. 'source_a.Amount'). "
    "Chain via results.<step_id>. "
    "- rules: enforce exceptions the outputs require. "
    "- settings_schema: 2-5 tuning knobs for THIS use case, keys must match rule/calculator params. "
    "- output_spec: one entry per Output bullet, in order. "
    "- sources: cover EVERY uploaded file with {role, file, field_mappings}. "
)


def _get_token() -> str:
    """Fetch an OAuth token from SAP XSUAA (cached until expiry)."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires"]:
        return _token_cache["token"]

    resp = requests.post(
        SAP_AICORE_AUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": SAP_AICORE_CLIENT_ID,
            "client_secret": SAP_AICORE_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires"] = time.time() + int(data.get("expires_in", 3600)) - 60
    return _token_cache["token"]


def _chat_remote(messages: list, temperature: float) -> str:
    """OpenAI-compatible chat completion through the AI Core deployment."""
    token = _get_token()
    url = f"{SAP_AICORE_DEPLOYMENT_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": SAP_AICORE_RESOURCE_GROUP,
        "Content-Type": "application/json",
    }
    payload = {
        "model": SAP_AICORE_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 3000,
    }
    r = requests.post(url, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    global _last_model_used
    _last_model_used = SAP_AICORE_MODEL
    return data["choices"][0]["message"]["content"]


def chat(messages: list, temperature: float = 0.2) -> str:
    """
    Chat completion via SAP AI Core (OpenAI-compatible).
    Falls back to mock_chat() when credentials are not configured or on error.
    """
    if aicore_configured():
        try:
            return _chat_remote(messages, temperature)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            print(f"[llm] SAP AI Core call failed, using mock fallback: {exc}")
    return mock_chat(messages)


def mock_chat(messages: list) -> str:
    """Deterministic offline fallback used when SAP AI Core is not configured."""
    lowered = (messages[-1]["content"] if messages else "").lower()

    if "suggest" in lowered or "workflow" in lowered:
        return json.dumps(
            {
                "name": "Bank-to-GL Reconciliation",
                "description": "Match bank statement lines to GL entries and review differences.",
                "agents": ["A1", "A2", "A3", "A4", "A5", "A6"],
                "sources": [
                    {
                        "role": "bank_statement",
                        "field_mappings": {
                            "Value Date": "transaction_date",
                            "Amount": "amount",
                            "Reference": "reference",
                            "Description": "description",
                        },
                    },
                    {
                        "role": "gl_export",
                        "field_mappings": {
                            "Posting Date": "transaction_date",
                            "Amount in LC": "amount",
                            "Assignment": "reference",
                            "Document Number": "document_no",
                        },
                    },
                ],
                "matching": {
                    "keys": ["amount", "reference"],
                    "date_tolerance_days": 3,
                    "amount_tolerance": 1.0,
                },
                "calculations": [
                    {
                        "id": "calc_amount_diff",
                        "calculator": "amount_difference",
                        "input_mapping": {"a": "amount", "b": "matched_amount"},
                    },
                    {
                        "id": "calc_date_diff",
                        "calculator": "date_difference",
                        "input_mapping": {"date_1": "transaction_date", "date_2": "gl_posting_date"},
                    },
                ],
                "rules": [
                    {"id": "tolerance_check", "params": {"tolerance": 1.0}},
                    {"id": "low_confidence_review", "params": {"threshold": 0.8}},
                ],
                "routing": {"unmatched": "finance_operations", "high_value": "controller"},
            },
            indent=2,
        )

    # Generic explanation fallback
    return (
        "Summary (mock LLM — SAP AI Core not configured): the workflow processed the "
        "configured records, applied the bound rules and calculations, and produced an "
        "evidence-backed result. Configure SAP_AICORE_* in backend/.env for live LLM output."
    )


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else parts[0]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response that may contain preamble/postamble text."""
    cleaned = _strip_code_fence(text)
    start = cleaned.find("{")
    if start == -1:
        return cleaned
    depth = 0
    end = -1
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return cleaned
    return cleaned[start : end + 1]


def _is_number(value) -> bool:
    """Structural check: does this sample value parse as a number?"""
    if value is None or isinstance(value, bool):
        return False
    try:
        float(str(value).replace(",", "").strip())
        return True
    except (ValueError, TypeError):
        return False


def _numeric_columns(profile: dict) -> list:
    """Columns whose sample values are numeric (pure structure, no vocabulary)."""
    cols = list(profile.get("columns") or [])
    samples = profile.get("sample_rows") or []
    numeric = []
    for col in cols:
        vals = [r.get(col) for r in samples if r.get(col) not in (None, "")]
        if vals and all(_is_number(v) for v in vals):
            numeric.append(col)
    return numeric


def _mechanical_mappings(columns: list) -> dict:
    """
    Generic hint mapping: column name → normalized key (strip, lower, underscores).
    Purely mechanical — no domain dictionary. A2 falls back to same-name columns
    anyway; the LLM and the config page are the real mapping authority.
    """
    import re
    return {c: re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_") for c in columns}


def _derive_sources(existing: list, file_profiles: list) -> list:
    """Build sources {role, file, field_mappings} from uploaded profiles (generic)."""
    by_role = {s.get("role"): s for s in existing if isinstance(s, dict) and s.get("role")}
    sources = []
    for p in file_profiles:
        role = p.get("role") or f"source_{len(sources)}"
        prev = by_role.get(role, {})
        mappings = prev.get("field_mappings") or _mechanical_mappings(p.get("columns") or [])
        sources.append({
            "role": role,
            "file": p.get("file"),
            "label": prev.get("label") or p.get("file"),
            "required_fields": prev.get("required_fields") or [],
            "field_mappings": mappings,
        })
    return sources


def _normalize_config(config: dict, file_profiles: list | None = None) -> dict:
    """
    Use-case-agnostic sanity pass on any LLM-designed workflow config:
      - agent references → canonical IDs ("A1 Capture" → "A1"),
      - calculation steps' used_by → canonical IDs,
      - if 'sources' is missing/empty, derive them generically from the
        uploaded file profiles so A1 always has data to read.
      - normalize calculation key aliases
      - seed generic settings/settings_schema/output_spec if missing
    """
    from app.agents.ids import normalize_agent_id, normalize_agent_list

    if isinstance(config.get("agents"), list):
        ids, unknown = normalize_agent_list(config["agents"])
        if unknown:
            logger.warning("[llm] non-standard agent references normalized/dropped: %s", unknown)
        config["agents"] = ids

    for step in config.get("calculations") or []:
        aid = normalize_agent_id(step.get("used_by"))
        if aid:
            step["used_by"] = aid
        elif step.get("used_by"):
            logger.warning("[llm] calc step %s has unrecognized used_by %r — defaulting to A4", step.get("id"), step.get("used_by"))
            step["used_by"] = "A4"

    # A4 reads the pipeline from 'calculations' — normalize legacy aliases
    calcs = config.get("calculations") or config.get("calculation_pipeline") or config.get("calculation_steps") or []
    config["calculations"] = calcs
    if not calcs:
        logger.warning("[llm] NO calculation steps designed — rules referencing results.* will not fire")

    # generic, configurable magnitude tiers so A4 can produce interpretable statuses
    settings = config.get("settings") or {}
    settings.setdefault("materiality", 5000)
    settings.setdefault("on_track_pct", 5)
    settings.setdefault("review_pct", 10)
    config["settings"] = settings

    # settings_schema: tuning knobs tailored to the use case (LLM-provided),
    # with a generic fallback so the config page always has something to render.
    schema = config.get("settings_schema")
    if not isinstance(schema, list) or not schema:
        schema = [
            {"key": "materiality", "label": "Materiality threshold", "type": "number",
             "default": settings.get("materiality", 5000), "unit": "USD",
             "description": "Variances above this amount are flagged as material exceptions"},
            {"key": "on_track_pct", "label": "On-track band", "type": "number",
             "default": settings.get("on_track_pct", 5), "unit": "%",
             "description": "Variance percentage below this is on track"},
            {"key": "review_pct", "label": "Review threshold", "type": "number",
             "default": settings.get("review_pct", 10), "unit": "%",
             "description": "Variance percentage at or above this needs finance review"},
        ]
        logger.info("[llm] settings_schema missing → using generic fallback schema")
    # seed settings defaults from schema for any keys the LLM forgot
    for item in schema:
        k = item.get("key")
        if k and k not in settings and item.get("default") is not None:
            settings[k] = item["default"]

    config["settings_schema"] = schema
    config["settings"] = settings

    # output_spec: the report blocks the user asked for in the 'Output:' section.
    # Validate the LLM list; fall back to a generic structure-derived set.
    spec = config.get("output_spec")
    valid_renders = {"kpi", "table", "exceptions", "narrative"}
    if isinstance(spec, list) and spec:
        cleaned = []
        for i, b in enumerate(spec):
            if not isinstance(b, dict):
                continue
            render = str(b.get("render") or "table").lower()
            if render not in valid_renders:
                render = "table"
            cleaned.append({
                "id": str(b.get("id") or f"output_{i + 1}"),
                "title": str(b.get("title") or b.get("id") or f"Output {i + 1}"),
                "render": render,
                "description": str(b.get("description") or ""),
                "source": b.get("source") or "",
            })
        config["output_spec"] = cleaned
        logger.info("[llm] output_spec: %s", [(b["id"], b["render"]) for b in cleaned])
    else:
        fallback = [{"id": "summary_kpis", "title": "Key figures", "render": "kpi", "description": "Headline counts and totals", "source": "summary"}]
        if config.get("comparison"):
            fallback.append({"id": "compared_table", "title": "Compared rows", "render": "table", "description": "Row-level results per aligned record", "source": "compared_rows"})
        fallback.append({"id": "exceptions", "title": "Exceptions", "render": "exceptions", "description": "Rows that failed rules or could not be matched", "source": "exceptions"})
        fallback.append({"id": "narrative", "title": "Narrative", "render": "narrative", "description": "Written explanation of the results", "source": "llm"})
        config["output_spec"] = fallback
        logger.info("[llm] output_spec missing → generic fallback (%d blocks)", len(fallback))
    config["report"] = {**(config.get("report") or {}), "output_spec": config["output_spec"]}

    # sources must never be empty — derive from profiles if the LLM omitted them
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        config["sources"] = _derive_sources(config.get("sources") or [], file_profiles or [])
        logger.info("[llm] sources missing/empty → derived %d source(s) from uploaded profiles",
                    len(config["sources"]))
    # mirror sources into agent_configs.A1 if absent
    agent_configs = config.get("agent_configs")
    if isinstance(agent_configs, dict):
        a1 = agent_configs.get("A1")
        if not isinstance(a1, dict) or not a1.get("sources"):
            agent_configs["A1"] = {**(a1 or {}), "sources": config["sources"]}
        # A4 needs calculations/rules/comparison/settings under the keys it reads
        a4 = agent_configs.get("A4")
        if not isinstance(a4, dict):
            a4 = {}
        for k in ("calculations", "rules", "comparison", "settings"):
            if not a4.get(k) and config.get(k):
                a4[k] = config[k]
        agent_configs["A4"] = a4

    return config


def suggest_workflow(description: str, file_profiles: list, engine_library: dict | None = None) -> dict:
    """
    Ask SAP AI Core to design a workflow configuration from a use-case description,
    uploaded file profiles, and the engine library (calculators + rules).
    Falls back to the data-driven deterministic template when not configured or on error.
    """
    library = engine_library or {}
    if not aicore_configured():
        logger.warning("[llm] SAP_AICORE credentials not configured → using data-driven MOCK fallback workflow")
        return _normalize_config(mock_chat([{"role": "user", "content": "suggest workflow"}]), file_profiles)

    system_prompt = SYSTEM_WORKFLOW
    if library:
        system_prompt += (
            "\n\nENGINE LIBRARY — you MUST choose calculators and rules ONLY from this catalog, "
            "using the exact names and versions given:\n"
            + json.dumps(library, indent=2)
            + "\nEach calculation step MUST include: id, calculator (from library), version "
            "(library version), used_by (an agent ID like 'A4'), scope, input_mapping (bind each calculator input to a source "
            "column from the uploaded files using the file's role prefix, e.g. 'source_a.Amount', or to a prior "
            "step output as 'results.<id>'), output_mapping ({\"result\": \"results.<id>\"}), depends_on."
            + "\nALSO include: a top-level 'sources' list of {role, file, field_mappings: {source_column: canonical_field}} "
            "covering EVERY uploaded file (use the roles from the profiles), and an 'explanation' field: "
            "2-4 sentences for a finance user explaining WHY this pipeline (agents, calculations, rules) solves "
            "their described use case, referencing their actual columns."
            + "\nALSO include a 'settings_schema' list tailored to THIS use case — the tuning knobs a finance user "
            "should control. Each item: {key, label, type: 'number'|'select'|'text', default, unit (optional), "
            "description}. Use keys that match the rule/calculator params you chose (e.g. materiality, "
            "on_track_pct, review_pct, tolerance, aging_days). 2-5 items. And seed the top-level 'settings' "
            "object with the default value for each key."
        )

    user_payload = json.dumps(
        {"use_case_description": description, "files": file_profiles}, indent=2
    )
    logger.info("[llm] calling SAP AI Core model=%s (profiles=%d, calculators=%d, rules=%d)…",
                SAP_AICORE_MODEL, len(file_profiles),
                len(library.get("calculators", [])), len(library.get("rules", [])))
    t0 = time.perf_counter()
    last_error = None
    content = ""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": (
            f"Design a workflow for this use case:\n{description}\n\n"
            f"Uploaded file profiles (use these exact column names in input_mapping):\n"
            f"{user_payload}"
        )},
    ]
    for attempt in (1, 2, 3):
        try:
            content = chat(messages, temperature=0.2)
            logger.info("[llm] SAP AI Core responded in %.1fs (%d chars) — parsing JSON…",
                        time.perf_counter() - t0, len(content))
            config = json.loads(_extract_json(content))
            config.setdefault("source", "sap_ai_core")
            config["model"] = _last_model_used or SAP_AICORE_MODEL
            config = _normalize_config(config, file_profiles)
            logger.info("[llm] JSON parsed OK — title=%r, agents=%s", config.get("title"), config.get("agents"))
            return config
        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning("[llm] attempt %d: SAP AI Core reply was NOT valid JSON (%s). Reply head: %.300s", attempt, exc, content)
            if attempt < 3:
                correction = (
                    "Your previous response was not valid JSON. "
                    f"It started with: {content[:200]}. "
                    "Output ONLY valid JSON. No markdown. No explanation. "
                    "The JSON must include all required keys: name, description, agents, sources, "
                    "calculations, rules, settings, settings_schema, output_spec, routing, report, "
                    "agent_configs, explanation."
                )
                messages.append({"role": "user", "content": correction})
                continue
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            logger.error("[llm] SAP AI Core suggest_workflow FAILED after %.1fs (%s) → using data-driven mock fallback",
                         time.perf_counter() - t0, exc)
            return _normalize_config(mock_chat([{"role": "user", "content": "suggest workflow"}]), file_profiles)

    logger.error("[llm] SAP AI Core reply invalid JSON after %d attempts (%s) → falling back to data-driven mock template", 3, last_error)
    return _normalize_config(mock_chat([{"role": "user", "content": "suggest workflow"}]), file_profiles)


def explain(prompt: str) -> str:
    """A5-style explanation via SAP AI Core (or mock)."""
    if aicore_configured():
        try:
            return chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are Nexus A5, a finance report writer. Explain results clearly "
                            "for finance users, referencing evidence ids where given. Be concise."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[llm] SAP AI Core explain failed, using mock fallback: %s", exc)
    return (
        "Summary (mock LLM — SAP AI Core not configured): the workflow processed the "
        "configured records, applied the bound rules and calculations, and produced an "
        "evidence-backed result. Configure SAP_AICORE_* in backend/.env for live LLM output."
    )