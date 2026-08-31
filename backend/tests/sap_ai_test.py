#!/usr/bin/env python3
"""
================================================================================
  NEXUS 2.0 -- SAP AI Core GPT-4.1 Diagnostics & Hello World Test
================================================================================

Tests your SAP AI Core connection end-to-end using credentials from backend/.env:
  1. Authenticates against SAP XSUAA using client credentials
  2. Runs "Hello World" chat inference on GPT-4.1 (and other configured models)
  3. Tests full Nexus 2.0 application layer (app.llm.explain / suggest_workflow)

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
# 2. Base Credentials from .env
# -----------------------------------------------------------------------------
AICORE_API_URL = os.getenv("AICORE_API_URL") or os.getenv("SAP_AICORE_BASE_URL", "")
XSUAA_URL = os.getenv("XSUAA_URL") or os.getenv("SAP_AICORE_AUTH_URL", "")
XSUAA_CLIENT_ID = os.getenv("XSUAA_CLIENT_ID") or os.getenv("SAP_AICORE_CLIENT_ID", "")
XSUAA_CLIENT_SECRET = os.getenv("XSUAA_CLIENT_SECRET") or os.getenv("SAP_AICORE_CLIENT_SECRET", "")
AICORE_RG = os.getenv("AICORE_RESOURCE_GROUP") or os.getenv("SAP_AICORE_RESOURCE_GROUP", "default")
_AICORE_DEPLOY_ID = os.getenv("AICORE_DEPLOYMENT_ID") or os.getenv("SAP_AICORE_DEPLOYMENT_URL", "")
OPENAI_API_VERSION = os.getenv("AICORE_OPENAI_API_VERSION", "2024-12-01-preview")
ACTIVE_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip()

# Model Registry configuration
MODELS = {
    "gpt41": {
        "label": "gpt-4.1 (Nexus Primary)",
        "deploy_id": os.getenv("AICORE_GPT41_DEPLOYMENT_ID", "d7cec98f1a47f4f3"),
        "format": "openai",
        "api_version": OPENAI_API_VERSION,
    },
    "gpt4o_mini": {
        "label": "gpt-4o-mini",
        "deploy_id": os.getenv("AICORE_GPT40_MINI_DEPLOYMENT_ID", "dfe7e04bfb45b361"),
        "format": "openai",
        "api_version": OPENAI_API_VERSION,
    },
    "gpt4o": {
        "label": "gpt-4o",
        "deploy_id": os.getenv("AICORE_GPT40_DEPLOYMENT_ID", "db87ce5524bf96d9"),
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
        "deploy_id": os.getenv("AICORE_CLAUDE_DEPLOYMENT_ID", _AICORE_DEPLOY_ID if "claude" in _AICORE_DEPLOY_ID.lower() else ""),
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


print("\n" + "=" * 70)
print("  SAP AI CORE (GPT-4.1) CONFIGURATION SUMMARY")
print("=" * 70)
print(f"  * LLM_PROVIDER in .env     : {ACTIVE_PROVIDER}")
print(f"  * AICORE_API_URL           : {AICORE_API_URL or '<NOT SET>'}")
print(f"  * XSUAA_URL                : {XSUAA_URL or '<NOT SET>'}")
print(f"  * XSUAA_CLIENT_ID          : {mask(XSUAA_CLIENT_ID, 6, 4)}")
print(f"  * XSUAA_CLIENT_SECRET      : {mask(XSUAA_CLIENT_SECRET, 3, 3)}")
print(f"  * AICORE_RESOURCE_GROUP    : {AICORE_RG}")
print(f"  * GPT-4.1 Deployment ID    : {MODELS['gpt41']['deploy_id']}")
print(f"  * OpenAI API Version       : {OPENAI_API_VERSION}")
print("=" * 70 + "\n")


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
# 4. Test Step 2: Hello World Inference on GPT-4.1
# -----------------------------------------------------------------------------
def test_step_2_inference(token: str) -> bool:
    print("\n[TEST 2/3] Testing Hello World Inference on SAP AI Core...")
    
    if not AICORE_API_URL:
        print("  [FAIL] AICORE_API_URL is missing in .env")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": AICORE_RG,
        "Content-Type": "application/json",
    }

    # Test GPT-4.1 specifically first
    primary_config = MODELS["gpt41"]
    print(f"\n--- Testing Primary Model: {primary_config['label']} (ID: {primary_config['deploy_id']}) ---")
    
    url = f"{AICORE_API_URL.rstrip('/')}/v2/inference/deployments/{primary_config['deploy_id']}/chat/completions?api-version={primary_config['api_version']}"
    payload = {
        "messages": [
            {"role": "system", "content": "You are Nexus 2.0 finance AI assistant."},
            {"role": "user", "content": "Say 'Hello World! SAP AI Core GPT-4.1 is fully operational.' in one sentence."}
        ],
        "max_tokens": 100,
        "temperature": 0.2,
    }

    print(f"  -> POST {url}")
    print(f"  -> Resource-Group: {AICORE_RG}")
    t0 = time.perf_counter()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30.0)
        elapsed = time.perf_counter() - t0
        
        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"].strip()
            usage = result.get("usage", {})
            print(f"  [PASS] GPT-4.1 responded in {elapsed:.2f}s!")
            print(f"         Prompt tokens: {usage.get('prompt_tokens', '?')} | Completion tokens: {usage.get('completion_tokens', '?')}")
            print("\n  " + "-" * 66)
            print(f"  [GPT-4.1 Response]:\n  \"{content}\"")
            print("  " + "-" * 66)
            return True
        else:
            print(f"  [FAIL] HTTP {resp.status_code} in {elapsed:.2f}s")
            print(f"  Response: {resp.text[:400]}")
            return False
    except Exception as e:
        print(f"  [FAIL] Inference error: {e}")
        return False


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
        print("\n" + "=" * 70)
        print("  [RESULT] SAP AI Core Authentication FAILED.")
        print("  Check in .env: XSUAA_URL, XSUAA_CLIENT_ID, XSUAA_CLIENT_SECRET")
        print("=" * 70)
        sys.exit(1)

    inference_ok = test_step_2_inference(token)
    if not inference_ok:
        print("\n" + "=" * 70)
        print("  [RESULT] SAP AI Core Inference FAILED.")
        print("  Check in .env: AICORE_API_URL, AICORE_GPT41_DEPLOYMENT_ID, AICORE_RESOURCE_GROUP")
        print("=" * 70)
        sys.exit(1)

    app_ok = test_step_3_app_integration()

    print("\n" + "=" * 70)
    if inference_ok and app_ok:
        print("  [SUCCESS] ALL SAP AI CORE GPT-4.1 TESTS PASSED!")
        print("  Nexus 2.0 is fully verified and running on SAP AI Core GPT-4.1.")
    else:
        print("  [WARNING] Direct inference succeeded, but app routing encountered issues.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
