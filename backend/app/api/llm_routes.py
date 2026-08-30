from __future__ import annotations

"""Routes: LLM-powered workflow suggestion + data profiling.

The pipeline step now uses the configured LLM (OpenRouter or SAP AI Core)
via app.llm.suggest_workflow / app.llm.explain. Falls back to deterministic
mock responses when no LLM key is configured.
"""
import logging
import time

import pandas as pd
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.config import UPLOADS_DIR
from app.engines.calculation_engine import CALCULATORS
from app.engines.rule_engine import RULES
from app.llm import explain as llm_explain, suggest_workflow as llm_suggest_workflow

logger = logging.getLogger("nexus.llm_routes")

router = APIRouter(prefix="/llm", tags=["llm"])

DESCRIPTION = (
    "Analyze the uploaded data files, compare the datasets, compute meaningful "
    "differences or totals per aligned record, flag exceptions above configured "
    "thresholds, and produce a finance-style report with KPIs, tables, and narrative."
)


@router.get("/suggest-pipeline")
async def suggest_pipeline(use_case: str = "budget_vs_actual"):
    """
    Generate the workflow pipeline using the configured LLM.
    Falls back to a deterministic POC template when no LLM is configured or on error.
    """
    if use_case != "budget_vs_actual":
        logger.warning("[pipeline] unknown use case requested: %s", use_case)
        return {"error": f"unknown use case: {use_case}"}

    logger.info("[pipeline] >>> LLM pipeline design STARTED (use_case=%s)", use_case)
    t0 = time.perf_counter()
    try:
        config = llm_suggest_workflow(DESCRIPTION, [])
        elapsed = time.perf_counter() - t0
        logger.info("[pipeline] <<< LLM pipeline design FINISHED in %.1fs — title=%r, agents=%s, calc_steps=%s, rules=%s",
                    elapsed, config.get("title"), config.get("agents"),
                    len(config.get("calculation_pipeline") or []),
                    len(config.get("rules") or []))
        return config
    except Exception as exc:  # noqa: BLE001
        logger.exception("[pipeline] !!! pipeline design FAILED after %.1fs: %s", time.perf_counter() - t0, exc)
        raise


class DesignRequest(BaseModel):
    """Body for POST /llm/design-pipeline."""
    description: str = ""
    profiles: list = []
    llm_provider: str = "openrouter"


def _engine_library() -> dict:
    """Catalog of available calculators and rules (compact to reduce prompt size)."""
    return {
        "calculators": [
            {"name": name, "version": m["version"], "inputs": m["inputs"]}
            for name, m in sorted(CALCULATORS.items())
        ],
        "rules": [
            {"name": name, "version": m["version"], "params": m["params"]}
            for name, m in sorted(RULES.items())
        ],
    }


@router.post("/design-pipeline")
async def design_pipeline(req: DesignRequest):
    """
    Design the workflow pipeline from the use-case description + uploaded file
    profiles. The LLM is given the engine library and may only pick engines
    from it. Falls back to a data-driven deterministic template on error.
    """
    logger.info("[pipeline] >>> LLM pipeline design STARTED (profiles=%d, description=%d chars)",
                len(req.profiles), len(req.description))
    for p in req.profiles:
        logger.info("[pipeline]   file=%s role=%s rows=%s columns=%s",
                    p.get("file"), p.get("role"), p.get("row_count"), p.get("columns"))

    library = _engine_library()
    logger.info("[pipeline] engine library injected: %d calculators, %d rules",
                len(library["calculators"]), len(library["rules"]))

    t0 = time.perf_counter()
    try:
        config = llm_suggest_workflow(req.description or DESCRIPTION, req.profiles, engine_library=library, llm_provider=req.llm_provider)
        elapsed = time.perf_counter() - t0
        logger.info("[pipeline] <<< LLM pipeline design FINISHED in %.1fs — title=%r, agents=%s, "
                    "calc_steps=%s, rules=%s, source=%s, provider=%s",
                    elapsed, config.get("title"), config.get("agents"),
                    len(config.get("calculation_pipeline") or []),
                    len(config.get("rules") or []),
                    config.get("source", "llm"), req.llm_provider)
        for step in config.get("calculation_pipeline") or []:
            logger.info("[pipeline]   calc %s → %s v%s (mapping=%s)",
                        step.get("id"), step.get("calculator"), step.get("version"), step.get("input_mapping"))
        for rule in config.get("rules") or []:
            logger.info("[pipeline]   rule %s (params=%s)", rule.get("id"), rule.get("params"))
        return config
    except Exception as exc:  # noqa: BLE001
        logger.exception("[pipeline] !!! pipeline design FAILED after %.1fs: %s", time.perf_counter() - t0, exc)
        raise


@router.post("/profile-data")
async def profile_data(
    files: list[UploadFile] = File(...),
    description: str = Form(""),
):
    """
    Upload file(s) → read the actual columns and sample rows, detect the
    canonical mapping, and return a per-file profile.
    """
    profiles = []
    saved = {}
    errors = []

    logger.info("[profile] >>> data profiling STARTED for %d file(s)", len(files))
    for idx, f in enumerate(files, start=1):
        logger.info("[profile] step %d/%d — receiving %s…", idx, len(files), f.filename)
        try:
            content = await f.read()
            dest = UPLOADS_DIR / f.filename
            dest.write_bytes(content)
            saved[f.filename] = str(dest)
            logger.info("[profile] step %d/%d — saved %s (%d bytes) to uploads/",
                        idx, len(files), f.filename, len(content))

            if f.filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(dest)
            else:
                df = pd.read_csv(dest)

            role = "data"  # assigned after profiling via LLM/neutral fallback
            profiles.append({
                "file": f.filename,
                "role": role,
                "columns": list(df.columns),
                "sample_rows": df.head(3).replace({pd.NA: None}).to_dict(orient="records"),
                "row_count": len(df),
                "suggested_mappings": _suggest_mappings(list(df.columns)),
            })
            logger.info("[profile] step %d/%d — profiled %s → rows=%d, columns=%s",
                        idx, len(files), f.filename, len(df), list(df.columns))
        except Exception as exc:  # noqa: BLE001 — one bad file must not kill the upload
            logger.exception("[profile] step %d/%d — FAILED to profile %s: %s",
                             idx, len(files), f.filename, exc)
            errors.append({"file": f.filename, "error": f"{type(exc).__name__}: {exc}"})

    logger.info("[profile] <<< data profiling FINISHED — %d profile(s), %d error(s)",
                len(profiles), len(errors))
    return {"profiles": profiles, "saved": saved, "description": description, "errors": errors}


def _suggest_mappings(columns: list) -> dict:
    """
    Generic hint mapping: column name → normalized key (strip, lower, underscores).
    Purely mechanical — no domain dictionary. The LLM (at design time) and the
    user (in the config page) are the real mapping authority.
    """
    import re
    return {c: re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_") for c in columns}


@router.post("/suggest-workflow")
async def suggest_workflow(
    description: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """Upload files + describe the use case → LLM designs the workflow config."""
    logger.info("[workflow] >>> suggest-workflow STARTED (%d file(s))", len(files))
    file_profiles = []
    saved = {}

    for f in files:
        content = await f.read()
        dest = UPLOADS_DIR / f.filename
        dest.write_bytes(content)
        saved[f.filename] = str(dest)

        if f.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(dest)
        else:
            df = pd.read_csv(dest)

        file_profiles.append({
            "file": f.filename,
            "columns": list(df.columns),
            "sample_rows": df.head(3).to_dict(orient="records"),
            "row_count": len(df),
        })

    config = llm_suggest_workflow(description, file_profiles)
    logger.info("[workflow] <<< suggest-workflow FINISHED — title=%r, agents=%s", config.get("title"), config.get("agents"))
    return {"config": config, "files": file_profiles, "saved": saved}


@router.post("/explain")
def explain(prompt: str):
    """A5-style explanation via the configured LLM."""
    return {"narrative": llm_explain(prompt)}