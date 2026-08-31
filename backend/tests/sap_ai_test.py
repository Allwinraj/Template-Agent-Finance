#!/usr/bin/env python3
"""
================================================================================
  NEXUS 2.0 -- SAP AI Core Diagnostics and Hello World Inference Test
================================================================================

This script tests your SAP AI Core connection end-to-end:
  1. Loads credentials from backend/.env
  2. Tests OAuth2 token acquisition from SAP XSUAA
  3. Tests direct Hello World chat completion against the deployment URL
  4. Tests full integration through Nexus 2.0 application routing layer

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
from typing import Optional

# -----------------------------------------------------------------------------
# 1. Resolve Environment and Paths
# -----------------------------------------------------------------------------
SCRIPT_FILE = Path(__file__).resolve()
# Find Template_agent root
CURRENT = SCRIPT_FILE.parent
while CURRENT.name and CURRENT.name != "Template_agent" and CURRENT.parent != CURRENT:
    CURRENT = CURRENT.parent

PROJECT_ROOT = CURRENT if CURRENT.name == "Template_agent" else SCRIPT_FILE.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend" if (PROJECT_ROOT / "backend").exists() else SCRIPT_FILE.parent

# Add backend directory to Python sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Try loading .env with priority given to backend/.env
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
# 2. Extract Credentials
# -----------------------------------------------------------------------------
AUTH_URL = os.getenv("SAP_AICORE_AUTH_URL", "").strip()
BASE_URL = os.getenv("SAP_AICORE_BASE_URL", "").strip()
CLIENT_ID = os.getenv("SAP_AICORE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("SAP_AICORE_CLIENT_SECRET", "").strip()
RESOURCE_GROUP = os.getenv("SAP_AICORE_RESOURCE_GROUP", "default").strip() or "default"
DEPLOYMENT_URL = os.getenv("SAP_AICORE_DEPLOYMENT_URL", "").strip()
MODEL = os.getenv("SAP_AICORE_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
ACTIVE_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip()


def mask(val: str, show_start: int = 4, show_end: int = 4) -> str:
    """Mask sensitive string for display."""
    if not val:
        return "<NOT SET>"
    if len(val) <= show_start + show_end:
        return "***"
    return f"{val[:show_start]}...{val[-show_end:]}"


print("\n" + "=" * 70)
print("  SAP AI CORE CONFIGURATION SUMMARY")
print("=" * 70)
print(f"  * LLM_PROVIDER in .env     : {ACTIVE_PROVIDER}")
print(f"  * SAP_AICORE_AUTH_URL      : {AUTH_URL or '(fallback to BASE_URL)'}")
print(f"  * SAP_AICORE_BASE_URL      : {BASE_URL or '(optional if DEPLOYMENT_URL set)'}")
print(f"  * SAP_AICORE_CLIENT_ID     : {mask(CLIENT_ID, 6, 4)}")
print(f"  * SAP_AICORE_CLIENT_SECRET : {mask(CLIENT_SECRET, 3, 3)}")
print(f"  * SAP_AICORE_RESOURCE_GROUP: {RESOURCE_GROUP}")
print(f"  * SAP_AICORE_DEPLOYMENT_URL: {DEPLOYMENT_URL or '(fallback to BASE_URL)'}")
print(f"  * SAP_AICORE_MODEL         : {MODEL}")
print("=" * 70 + "\n")


# -----------------------------------------------------------------------------
# 3. Test Step 1: OAuth Authentication
# -----------------------------------------------------------------------------
def test_step_1_oauth() -> Optional[str]:
    print("[TEST 1/3] Testing SAP XSUAA OAuth2 Token Fetch...")
    
    target_auth = AUTH_URL or BASE_URL
    if not target_auth:
        print("  [FAIL] Neither SAP_AICORE_AUTH_URL nor SAP_AICORE_BASE_URL is configured in .env")
        return None
    if not CLIENT_ID or not CLIENT_SECRET:
        print("  [FAIL] SAP_AICORE_CLIENT_ID and/or SAP_AICORE_CLIENT_SECRET is missing in .env")
        return None

    # Normalization
    if not target_auth.endswith("/oauth/token") and "authentication" in target_auth:
        target_auth = f"{target_auth.rstrip('/')}/oauth/token"
    elif not target_auth.endswith("/oauth/token"):
        target_auth = f"{target_auth.rstrip('/')}/oauth/token"

    print(f"  -> Sending POST to: {target_auth}")
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            target_auth,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=30,
        )
        elapsed = time.perf_counter() - t0
        if resp.status_code != 200:
            print(f"  [FAIL] HTTP {resp.status_code} in {elapsed:.2f}s")
            print(f"  Response: {resp.text[:400]}")
            return None

        data = resp.json()
        token = data.get("access_token")
        if not token:
            print("  [FAIL] Response 200 OK but 'access_token' field not found in JSON.")
            print(f"  Payload: {data}")
            return None

        expires_in = data.get("expires_in", "unknown")
        token_type = data.get("token_type", "Bearer")
        print(f"  [PASS] Successfully obtained OAuth {token_type} token in {elapsed:.2f}s!")
        print(f"         Expires in: {expires_in}s | Token: {mask(token, 10, 8)}")
        return token
    except requests.exceptions.RequestException as exc:
        print(f"  [FAIL] Network or connection error: {exc}")
        return None


# -----------------------------------------------------------------------------
# 4. Test Step 2: Hello World Chat Completion
# -----------------------------------------------------------------------------
def test_step_2_inference(token: str) -> bool:
    print("\n[TEST 2/3] Testing 'Hello World' Chat Inference via SAP AI Core Deployment...")
    
    target_dep = DEPLOYMENT_URL or BASE_URL
    if not target_dep:
        print("  [FAIL] Neither SAP_AICORE_DEPLOYMENT_URL nor SAP_AICORE_BASE_URL is configured in .env")
        return False

    target_dep = target_dep.rstrip('/')
    if not target_dep.endswith("/chat/completions"):
        url = f"{target_dep}/chat/completions"
    else:
        url = target_dep

    headers = {
        "Authorization": f"Bearer {token}",
        "AI-Resource-Group": RESOURCE_GROUP,
        "Content-Type": "application/json",
    }
    
    messages = [
        {"role": "system", "content": "You are Nexus 2.0 finance operations assistant powered by SAP AI Core."},
        {"role": "user", "content": "Hello World! Confirm that SAP AI Core connection is active in 1-2 concise sentences."}
    ]
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 300,
    }

    print(f"  -> Sending inference POST to: {url}")
    print(f"  -> Resource Group: {RESOURCE_GROUP} | Model: {MODEL}")
    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        elapsed = time.perf_counter() - t0
        
        if resp.status_code != 200:
            print(f"  [FAIL] HTTP {resp.status_code} in {elapsed:.2f}s")
            print(f"  Response: {resp.text[:500]}")
            return False

        data = resp.json()
        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            print("  [FAIL] 'choices' array missing or empty in completion response.")
            print(f"  Response JSON: {data}")
            return False

        message = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        
        print(f"  [PASS] Received response in {elapsed:.2f}s!")
        print(f"         Prompt tokens: {usage.get('prompt_tokens', '?')} | Completion tokens: {usage.get('completion_tokens', '?')}")
        print("\n  " + "-" * 66)
        print(f"  [SAP AI Core Output]:\n  \"{message.strip()}\"")
        print("  " + "-" * 66)
        return True
    except requests.exceptions.RequestException as exc:
        print(f"  [FAIL] Inference request failed: {exc}")
        return False


# -----------------------------------------------------------------------------
# 5. Test Step 3: Nexus Application Routing Integration
# -----------------------------------------------------------------------------
def test_step_3_app_integration() -> bool:
    print("\n[TEST 3/3] Testing Full Nexus 2.0 Application Routing (app.llm layer)...")
    try:
        from app.llm import explain, suggest_workflow
        from app.config import aicore_configured

        print(f"  * app.config.aicore_configured() returned: {aicore_configured()}")
        
        # Test narrative explanation via app.llm
        prompt = "Summarize total variance: actual $88,000 vs budget $65,139 (+35% overrun on GL 530000)."
        print("  -> Invoking app.llm.explain(..., llm_provider='sap_ai_core')...")
        t0 = time.perf_counter()
        narrative = explain(prompt, llm_provider="sap_ai_core")
        elapsed = time.perf_counter() - t0
        
        print(f"  [PASS] Narrative generation completed in {elapsed:.2f}s!")
        print(f"         Output snippet: {narrative[:140]}...")
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
        print("  Check in .env: SAP_AICORE_AUTH_URL, SAP_AICORE_CLIENT_ID, SAP_AICORE_CLIENT_SECRET")
        print("=" * 70)
        sys.exit(1)

    inference_ok = test_step_2_inference(token)
    if not inference_ok:
        print("\n" + "=" * 70)
        print("  [RESULT] SAP AI Core Inference FAILED.")
        print("  Check in .env: SAP_AICORE_DEPLOYMENT_URL, SAP_AICORE_RESOURCE_GROUP, SAP_AICORE_MODEL")
        print("=" * 70)
        sys.exit(1)

    app_ok = test_step_3_app_integration()

    print("\n" + "=" * 70)
    if inference_ok and app_ok:
        print("  [SUCCESS] ALL SAP AI CORE TESTS PASSED!")
        print("  Nexus 2.0 is fully verified and connected to SAP AI Core.")
    else:
        print("  [WARNING] Direct inference succeeded, but app routing encountered issues.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()