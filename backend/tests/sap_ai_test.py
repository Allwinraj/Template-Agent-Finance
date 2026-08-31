#!/usr/bin/env python3
"""
================================================================================
  NEXUS 2.0 -- SAP AI Core Multi-Model & GPT-4.1 Diagnostic Test
================================================================================

This test:
  1. Loads credentials from backend/.env matching .env.example
  2. Authenticates via XSUAA to get an OAuth2 bearer token
  3. Tests inference across all configured models (GPT-4.1 primary, GPT-4o, etc.)
  4. Tests full Nexus 2.0 application routing layer (app.llm)

Usage:
  python tests/sap_ai_test.py
  python backend/tests/sap_ai_test.py
"""
from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

# -----------------------------------------------------------------------------
# 1. Resolve Environment & Paths
# -----------------------------------------------------------------------------
SCRIPT_FILE = Path(__file__).resolve()
CURRENT = SCRIPT_FILE.parent
while CURRENT.name and CURRENT.name != "Template_agent" and CURRENT.parent != CURRENT:
    CURRENT = CURRENT.parent

PROJECT_ROOT = CURRENT if CURRENT.name == "Template_agent" else SCRIPT_FILE.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend" if (PROJECT_ROOT / "backend").exists() else SCRIPT_FILE.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    candidates = [
        BACKEND_DIR / ".env",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "backend" / ".env",
        Path.cwd() / "backend" / ".env",
        Path.cwd() / ".env",
    ]
    env_loaded = False
    for p in candidates:
        if p.exists() and p.is_file():
            load_dotenv(p, override=True)
            print(f"[Config] Loaded .env from: {p.resolve()}")
            env_loaded = True
            break
    if not env_loaded:
        print("[Config] Warning: No .env file found in standard locations. Using existing os.environ.")
except ImportError:
    print("[Config] Notice: python-dotenv not installed. Using system environment variables.")

try:
    import requests
except ImportError:
    print("\n[ERROR] 'requests' package is missing. Install with: pip install requests")
    sys.exit(1)


# -----------------------------------------------------------------------------
# 2. Base Credentials from .env (Matching .env.example)
# -----------------------------------------------------------------------------
AICORE_API_URL = os.getenv("AICORE_API_URL") or os.getenv("SAP_AICORE_BASE_URL", "")
_AICORE_DEPLOY_ID = os.getenv("AICORE_DEPLOYMENT_ID") or os.getenv("SAP_AICORE_DEPLOYMENT_URL", "")
AICORE_RG = os.getenv("AICORE_RESOURCE_GROUP") or os.getenv("SAP_AICORE_RESOURCE_GROUP", "default")
XSUAA_URL = os.getenv("XSUAA_URL") or os.getenv("SAP_AICORE_AUTH_URL", "")
XSUAA_CLIENT_ID = os.getenv("XSUAA_CLIENT_ID") or os.getenv("SAP_AICORE_CLIENT_ID", "")
XSUAA_CLIENT_SECRET = os.getenv("XSUAA_CLIENT_SECRET") or os.getenv("SAP_AICORE_CLIENT_SECRET", "")
OPENAI_API_VERSION = os.getenv("AICORE_OPENAI_API_VERSION", "2024-12-01-preview")
ACTIVE_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip()

# Model Registry configuration
MODELS = {
    "gpt41": {
        "label": "gpt-4.1 (Nexus Primary Engine)",
        "deploy_id": os.getenv("AICORE_GPT41_DEPLOYMENT_ID", "d7cec98f1a47f4f3"),
        "format": "openai",
        "api_version": OPENAI_API_VERSION,
    },
    "gpt4o": {
        "label": "gpt-4o",
        "deploy_id": os.getenv("AICORE_GPT40_DEPLOYMENT_ID", "db87ce5524bf96d9"),
        "format": "openai",
        "api_version": OPENAI_API_VERSION,
    },
    "gpt4o_mini": {
        "label": "gpt-4o-mini",
        "deploy_id": os.getenv("AICORE_GPT40_MINI_DEPLOYMENT_ID", "dfe7e04bfb45b361"),
        "format": "openai",
        "api_version": OPENAI_API_VERSION,
    },
    "gpt55": {
        "label": "gpt-5.5",
        "deploy_id": os.getenv("AICORE_GPT55_DEPLOYMENT_ID", "dcad171471db5a4c"),
        "format": "openai",
        "api_version": OPENAI_API_VERSION,
    },
    "claude": {
        "label": "claude-4.7-opus",
        "deploy_id": os.getenv("AICORE_CLAUDE_DEPLOYMENT_ID", _AICORE_DEPLOY_ID if "claude" in str(_AICORE_DEPLOY_ID).lower() else ""),
        "format": "anthropic",
    },
}


def mask(val: str, show_start: int = 4, show_end: int = 4) -> str:
    """Mask sensitive string for display."""
    if not val:
        return "<NOT SET>"
    if len(val) <= show_start + show_end:
        return "***"
    return f"{val[:show_start]}...{val[-show_end:]}"


print("\n" + "=" * 75)
print("  SAP AI CORE CONFIGURATION CHECK (.env vs .env.example)")
print("=" * 75)
print(f"  * LLM_PROVIDER in .env           : {ACTIVE_PROVIDER}")
print(f"  * AICORE_API_URL                 : {AICORE_API_URL or '<NOT SET>'}")
print(f"  * XSUAA_URL                      : {XSUAA_URL or '<NOT SET>'}")
print(f"  * XSUAA_CLIENT_ID                : {mask(XSUAA_CLIENT_ID, 6, 4)}")
print(f"  * XSUAA_CLIENT_SECRET            : {mask(XSUAA_CLIENT_SECRET, 3, 3)}")
print(f"  * AICORE_RESOURCE_GROUP          : {AICORE_RG}")
print(f"  * AICORE_OPENAI_API_VERSION      : {OPENAI_API_VERSION}")
print(f"  * AICORE_GPT41_DEPLOYMENT_ID     : {MODELS['gpt41']['deploy_id']}")
print(f"  * AICORE_GPT40_DEPLOYMENT_ID     : {MODELS['gpt4o']['deploy_id']}")
print(f"  * AICORE_GPT40_MINI_DEPLOYMENT_ID: {MODELS['gpt4o_mini']['deploy_id']}")
print(f"  * AICORE_GPT55_DEPLOYMENT_ID     : {MODELS['gpt55']['deploy_id']}")
print("=" * 75 + "\n")


# -----------------------------------------------------------------------------
# 3. Test Step 1: XSUAA Token Fetch
# -----------------------------------------------------------------------------
def test_step_1_oauth() -> Optional[str]:
    print("[TEST 1/3] Fetching XSUAA OAuth2 Token...")
    
    if not XSUAA_URL:
        print("  [FAIL] XSUAA_URL is not configured in .env")
        return None
    if not XSUAA_CLIENT_ID or not XSUAA_CLIENT_SECRET:
        print("  [FAIL] XSUAA_CLIENT_ID and/or XSUAA_CLIENT_SECRET is missing in .env")
        return None

    token_url = XSUAA_URL.rstrip('/')
    if not token_url.endswith("/oauth/token"):
        token_url = f"{token_url}/oauth/token"

    print(f"  -> POST {token_url}")
    t0 = time.perf_counter()
    try:
        token_response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": XSUAA_CLIENT_ID,
                "client_secret": XSUAA_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )
        elapsed = time.perf_counter() - t0
        if token_response.status_code != 200:
            print(f"  [FAIL] HTTP {token_response.status_code} in {elapsed:.2f}s")
            print(f"  Response: {token_response.text[:300]}")
            return None

        token = token_response.json().get("access_token")
        if not token:
            print("  [FAIL] 'access_token' missing in XSUAA response.")
            return None

        print(f"  [PASS] Successfully obtained OAuth Bearer token in {elapsed:.2f}s!")
        print(f"         Token: {mask(token, 10, 8)}")
        return token
    except requests.exceptions.RequestException as exc:
        print(f"  [FAIL] Network error connecting to XSUAA: {exc}")
        return None


# -----------------------------------------------------------------------------
# 4. Test Step 2: Multi-Model Inference (with focus on GPT-4.1)
# -----------------------------------------------------------------------------
def test_all_models(token: str) -> bool:
    print("\n[TEST 2/3] Testing Inference Across Model Deployments...")
    
    if not AICORE_API_URL:
        print("  [FAIL] AICORE_API_URL is missing in .env")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": AICORE_RG,
        "Content-Type": "application/json",
    }

    gpt41_success = False

    for key, config in MODELS.items():
        print(f"\n--- Testing {config['label']} (ID: {config.get('deploy_id') or 'N/A'}) ---")
        
        if not config.get("deploy_id"):
            print("  [Skipped] No deployment ID configured.")
            continue

        try:
            if config["format"] == "openai":
                url = f"{AICORE_API_URL.rstrip('/')}/v2/inference/deployments/{config['deploy_id']}/chat/completions?api-version={config['api_version']}"
                payload = {
                    "messages": [{"role": "user", "content": "Say 'Hello World! Model operational.' in one sentence."}],
                    "max_tokens": 60,
                    "temperature": 0.2,
                }
            elif config["format"] == "anthropic":
                url = f"{AICORE_API_URL.rstrip('/')}/v2/inference/deployments/{config['deploy_id']}/invoke"
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 60,
                    "messages": [{"role": "user", "content": "Say 'Hello World! Model operational.' in one sentence."}]
                }
            else:
                print(f"  [Skipped] Unknown format '{config['format']}'")
                continue

            t0 = time.perf_counter()
            response = requests.post(url, headers=headers, json=payload, timeout=30.0)
            elapsed = time.perf_counter() - t0
            response.raise_for_status()
            result = response.json()
            
            if config["format"] == "openai":
                content = result["choices"][0]["message"]["content"].strip()
                usage = result.get("usage", {})
                print(f"  [PASS] {config['label']} responded in {elapsed:.2f}s!")
                print(f"         Prompt tokens: {usage.get('prompt_tokens', '?')} | Completion tokens: {usage.get('completion_tokens', '?')}")
                print(f"  Response: \"{content}\"")
                if key == "gpt41":
                    gpt41_success = True
            else:
                content = result["content"][0]["text"].strip()
                print(f"  [PASS] {config['label']} responded in {elapsed:.2f}s!")
                print(f"  Response: \"{content}\"")

        except Exception as e:
            print(f"  [FAIL] {config['label']} failed: {str(e)}")

    return gpt41_success


# -----------------------------------------------------------------------------
# 5. Test Step 3: Full Nexus Application Routing
# -----------------------------------------------------------------------------
def test_step_3_app_integration() -> bool:
    print("\n[TEST 3/3] Testing Full Nexus 2.0 Application Routing (app.llm layer)...")
    try:
        from app.llm import explain, suggest_workflow
        from app.config import aicore_configured

        print(f"  * app.config.aicore_configured() returned: {aicore_configured()}")
        
        # Test narrative explanation via app.llm with GPT-4.1
        prompt = "Summarize total variance: actual $88,000 vs budget $65,139 (+35% overrun on GL 530000)."
        print("  -> Invoking app.llm.explain(..., llm_provider='sap_ai_core')...")
        t0 = time.perf_counter()
        narrative = explain(prompt, llm_provider="sap_ai_core")
        elapsed = time.perf_counter() - t0
        
        print(f"  [PASS] Narrative generation completed in {elapsed:.2f}s!")
        print(f"         Output snippet: {narrative[:160]}...")
        return True
    except Exception as exc:
        print(f"  [FAIL] Application routing test error: {exc}")
        return False


# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
def main():
    token = test_step_1_oauth()
    if not token:
        print("\n" + "=" * 75)
        print("  [RESULT] SAP AI Core Authentication FAILED.")
        print("  Check in .env: XSUAA_URL, XSUAA_CLIENT_ID, XSUAA_CLIENT_SECRET")
        print("=" * 75)
        sys.exit(1)

    inference_ok = test_all_models(token)
    if not inference_ok:
        print("\n" + "=" * 75)
        print("  [RESULT] Primary GPT-4.1 Inference FAILED.")
        print("  Check in .env: AICORE_API_URL, AICORE_GPT41_DEPLOYMENT_ID, AICORE_RESOURCE_GROUP")
        print("=" * 75)
        sys.exit(1)

    app_ok = test_step_3_app_integration()

    print("\n" + "=" * 75)
    if inference_ok and app_ok:
        print("  [SUCCESS] ALL SAP AI CORE GPT-4.1 TESTS PASSED!")
        print("  Nexus 2.0 is fully verified and matching .env.example with GPT-4.1.")
    else:
        print("  [WARNING] Direct inference succeeded, but app routing encountered issues.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()




# ============================================================
# Nexus 2.0 — Backend environment variables
# Copy this file to .env and fill in your values.
# ============================================================

# --- LLM provider: "openrouter" (default) or "sap_ai_core" ---
LLM_PROVIDER=openrouter

# --- OpenRouter (default) ---
# Sign up free at https://openrouter.ai → Keys. Primary model is the fastest free model.
# Fallback models are tried automatically if the primary fails (comma-separated).
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=liquid/lfm-2.5-2.6b:free
OPENROUTER_FALLBACK_MODELS=inclusionai/ling-3.0-flash-fin:free,nvidia/nemotron-3.5-lightning:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# --- SAP AI Core (set LLM_PROVIDER=sap_ai_core to use) ---
AICORE_API_URL=https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
XSUAA_URL=https://your-subaccount.authentication.eu10.hana.ondemand.com
XSUAA_CLIENT_ID=your-client-id
XSUAA_CLIENT_SECRET=your-client-secret
AICORE_RESOURCE_GROUP=default
AICORE_OPENAI_API_VERSION=2024-12-01-preview

# Model Deployment IDs (GPT-4.1 is the primary model used by Nexus 2.0)
AICORE_GPT41_DEPLOYMENT_ID=d7cec98f1a47f4f3
AICORE_GPT40_DEPLOYMENT_ID=db87ce5524bf96d9
AICORE_GPT40_MINI_DEPLOYMENT_ID=dfe7e04bfb45b361
AICORE_GPT55_DEPLOYMENT_ID=dcad171471db5a4c
AICORE_DEPLOYMENT_ID=
SAP_AICORE_MODEL=gpt-4.1



# --- Server ---
NEXUS_HOST=127.0.0.1
NEXUS_PORT=8000
NEXUS_CORS_ORIGINS=http://localhost:3000

# --- Storage ---
NEXUS_DATA_DIR=../data
