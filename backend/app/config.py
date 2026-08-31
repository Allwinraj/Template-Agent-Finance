"""Nexus 2.0 — application configuration loaded from .env"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# --- LLM provider selection ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()

# --- OpenRouter ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "liquid/lfm-2.5-2.6b:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("OPENROUTER_FALLBACK_MODELS", "inclusionai/ling-3.0-flash-fin:free,nvidia/nemotron-3.5-lightning:free").split(",")
    if m.strip()
]

# --- SAP AI Core ---
AICORE_API_URL = os.getenv("AICORE_API_URL") or os.getenv("SAP_AICORE_BASE_URL", "")
XSUAA_URL = os.getenv("XSUAA_URL") or os.getenv("SAP_AICORE_AUTH_URL", "")
XSUAA_CLIENT_ID = os.getenv("XSUAA_CLIENT_ID") or os.getenv("SAP_AICORE_CLIENT_ID", "")
XSUAA_CLIENT_SECRET = os.getenv("XSUAA_CLIENT_SECRET") or os.getenv("SAP_AICORE_CLIENT_SECRET", "")
AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP") or os.getenv("SAP_AICORE_RESOURCE_GROUP", "default")
AICORE_GPT41_DEPLOYMENT_ID = os.getenv("AICORE_GPT41_DEPLOYMENT_ID", "d7cec98f1a47f4f3")
AICORE_DEPLOYMENT_ID = os.getenv("AICORE_DEPLOYMENT_ID") or AICORE_GPT41_DEPLOYMENT_ID
AICORE_OPENAI_API_VERSION = os.getenv("AICORE_OPENAI_API_VERSION", "2024-12-01-preview")
SAP_AICORE_MODEL = os.getenv("SAP_AICORE_MODEL", "gpt-4.1")

# Aliases for backward compatibility
SAP_AICORE_BASE_URL = AICORE_API_URL
SAP_AICORE_AUTH_URL = XSUAA_URL
SAP_AICORE_CLIENT_ID = XSUAA_CLIENT_ID
SAP_AICORE_CLIENT_SECRET = XSUAA_CLIENT_SECRET
SAP_AICORE_RESOURCE_GROUP = AICORE_RESOURCE_GROUP
SAP_AICORE_DEPLOYMENT_URL = os.getenv("SAP_AICORE_DEPLOYMENT_URL", "")

# --- Server ---
NEXUS_HOST = os.getenv("NEXUS_HOST", "127.0.0.1")
NEXUS_PORT = int(os.getenv("NEXUS_PORT", "8000"))
NEXUS_CORS_ORIGINS = os.getenv("NEXUS_CORS_ORIGINS", "http://localhost:3000").split(",")

# --- Storage ---
DATA_DIR = Path(os.getenv("NEXUS_DATA_DIR", "../data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = (Path(__file__).resolve().parent.parent / DATA_DIR).resolve()
STORE_DIR = DATA_DIR / "store"
SAMPLES_DIR = DATA_DIR / "samples"
UPLOADS_DIR = DATA_DIR / "uploads"

for _d in (DATA_DIR, STORE_DIR, SAMPLES_DIR, UPLOADS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def llm_provider() -> str:
    """Return the active LLM provider: 'openrouter' or 'sap_ai_core'."""
    return LLM_PROVIDER if LLM_PROVIDER in ("openrouter", "sap_ai_core") else "openrouter"


def openrouter_configured() -> bool:
    """True when an OpenRouter API key is present."""
    return bool(OPENROUTER_API_KEY and not OPENROUTER_API_KEY.startswith("sk-or-v1-your"))


def aicore_configured() -> bool:
    """True when SAP AI Core credentials are present in .env."""
    has_api = bool(AICORE_API_URL or SAP_AICORE_DEPLOYMENT_URL)
    has_auth = bool(XSUAA_URL)
    has_creds = bool(XSUAA_CLIENT_ID and XSUAA_CLIENT_SECRET)
    has_deploy = bool(AICORE_GPT41_DEPLOYMENT_ID or AICORE_DEPLOYMENT_ID or SAP_AICORE_DEPLOYMENT_URL)
    return bool(has_api and has_auth and has_creds and has_deploy)
