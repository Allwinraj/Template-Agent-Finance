"""Nexus 2.0 — FastAPI application entrypoint."""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s: %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import NEXUS_CORS_ORIGINS, UPLOADS_DIR
from app.api.agents import router as agents_router
from app.api.workflows import router as workflows_router
from app.api.registry import router as registry_router
from app.api.llm_routes import router as llm_router
from app.api.dashboard import router as dashboard_router
from app.api.exceptions import router as exceptions_router
from app.api.engines import router as engines_router
from app.services import registry as registry_service
from app.config import aicore_configured, OPENROUTER_MODEL, OPENROUTER_FALLBACK_MODELS, openrouter_configured

logging.getLogger("nexus").info("[llm] provider startup — openrouter_configured=%s, model=%s (fallbacks: %s)",
    openrouter_configured(), OPENROUTER_MODEL, ", ".join(OPENROUTER_FALLBACK_MODELS))

app = FastAPI(
    title="Nexus 2.0 — Configurable Finance Operations Agent Platform",
    description="Six reusable agents (A1–A6) + orchestrator + rule/calculation engines.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=NEXUS_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

app.include_router(agents_router)
app.include_router(workflows_router)
app.include_router(registry_router)
app.include_router(llm_router)
app.include_router(dashboard_router)
app.include_router(exceptions_router)
app.include_router(engines_router, prefix="/api")


@app.get("/")
def root():
    return {
        "platform": "Nexus 2.0",
        "status": "running",
        "llm": "SAP AI Core" if aicore_configured() else "mock fallback",
        "endpoints": {
            "agents": "/agents",
            "workflows": "/workflows",
            "registry": "/registry/workflows",
            "llm": "/llm/suggest-workflow",
            "dashboard": "/dashboard/kpis",
            "exceptions": "/exceptions",
            "engines": "/api/calculators",
            "docs": "/docs",
        },
    }


def seed_default_workflow():
    """Create a default Bank-to-GL workflow if none exists."""
    if not registry_service.list_all():
        registry_service.create_draft(
            name="Bank-to-GL Reconciliation",
            description="Match bank statement lines to GL entries and review differences.",
            config={
                "agents": ["A1", "A2", "A3", "A4", "A5", "A6"],
                "sources": [
                    {"role": "bank_statement", "file": "bank_statement.csv", "required_fields": ["Value Date", "Amount", "Reference"], "field_mappings": {"Value Date": "transaction_date", "Amount": "amount", "Reference": "reference", "Description": "description"}},
                    {"role": "gl_export", "file": "sap_gl_export.csv", "required_fields": ["Posting Date", "Amount in LC", "Assignment"], "field_mappings": {"Posting Date": "transaction_date", "Amount in LC": "amount", "Assignment": "reference", "Document Number": "document_no"}},
                ],
                "matching": {"keys": ["amount", "reference"], "date_tolerance_days": 3, "amount_tolerance": 1.0},
                "calculations": [
                    {"id": "calc_amount_diff", "calculator": "amount_difference", "input_mapping": {"a": "amount", "b": "matched_amount"}},
                    {"id": "calc_date_diff", "calculator": "date_difference", "input_mapping": {"date_1": "transaction_date", "date_2": "gl_posting_date"}},
                ],
                "rules": [{"id": "tolerance_check", "params": {"tolerance": 1.0, "field": "amount_diff"}}, {"id": "low_confidence_review", "params": {"threshold": 0.8}}],
                "routing": {"unmatched": "finance_operations", "high_value": "controller", "high_value_threshold": 100000},
                "report": {"title": "Bank-to-GL Reconciliation Report", "audience": "finance_operations"},
            },
            created_by="admin",
        )
        wfs = registry_service.list_all()
        if wfs:
            registry_service.transition(wfs[0]["workflow_id"], "published", "controller_1")


seed_default_workflow()