#!/usr/bin/env python3
"""
================================================================================
  NEXUS 2.0 -- SAP AI Core Diagnostic & Auto-Discovery Test
================================================================================

This script:
  1. Authenticates against SAP XSUAA using your client credentials
  2. Queries SAP AI Core to DISCOVER all active deployments in your instance
  3. Tests "Hello World" inference against your deployment
  4. Tests full Nexus application routing

Usage:
  python tests/sap_ai_test.py
  python backend/tests/sap_ai_test.py
"""
from __future__ import annotations

import os
import sys
import time
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

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


def extract_base_api_url() -> str:
    """Extract root AI_API_URL (e.g., https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com)."""
    for url in (BASE_URL, DEPLOYMENT_URL):
        if url and "hana.ondemand.com" in url:
            match = re.search(r"(https://[a-zA-Z0-9.\-]+hana\.ondemand\.com)", url)
            if match:
                return match.group(1)
        elif url and url.startswith("http"):
            parts = url.split("/")
            if len(parts) >= 3:
                return f"{parts[0]}//{parts[2]}"
    return ""


API_BASE = extract_base_api_url()

print("\n" + "=" * 70)
print("  SAP AI CORE CONFIGURATION SUMMARY")
print("=" * 70)
print(f"  * LLM_PROVIDER in .env     : {ACTIVE_PROVIDER}")
print(f"  * SAP_AICORE_AUTH_URL      : {AUTH_URL or '(fallback to BASE_URL)'}")
print(f"  * SAP_AICORE_BASE_URL      : {BASE_URL or '(derived: ' + (API_BASE or 'none') + ')'}")
print(f"  * SAP_AICORE_CLIENT_ID     : {mask(CLIENT_ID, 6, 4)}")
print(f"  * SAP_AICORE_CLIENT_SECRET : {mask(CLIENT_SECRET, 3, 3)}")
print(f"  * SAP_AICORE_RESOURCE_GROUP: {RESOURCE_GROUP}")
print(f"  * SAP_AICORE_DEPLOYMENT_URL: {DEPLOYMENT_URL or '<NOT SET>'}")
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

    if not target_auth.endswith("/oauth/token"):
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
            return None

        expires_in = data.get("expires_in", "unknown")
        token_type = data.get("token_type", "Bearer")
        print(f"  [PASS] Successfully obtained OAuth {token_type} token in {elapsed:.2f}s!")
        print(f"         Expires in: {expires_in}s | Token: {mask(token, 10, 8)}")
        return token
    except requests.exceptions.RequestException as exc:
        print(f"  [FAIL] Network error: {exc}")
        return None


# -----------------------------------------------------------------------------
# 4. Auto-Discovery: List Active Deployments from SAP AI Core
# -----------------------------------------------------------------------------
def discover_deployments(token: str) -> List[Dict[str, Any]]:
    print("\n[Discovery] Scanning SAP AI Core for active deployments...")
    base = API_BASE or BASE_URL or "https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com"
    base = base.rstrip('/')
    
    # Try multiple resource groups (the configured one, 'default', and wildcards)
    rgs_to_try = [RESOURCE_GROUP]
    if "default" not in rgs_to_try:
        rgs_to_try.append("default")
    
    endpoints = [
        f"{base}/v2/lm/deployments",
        f"{base}/v2/inference/deployments",
    ]
    
    found_deployments = []
    
    for rg in rgs_to_try:
        headers = {
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": rg,
            "Content-Type": "application/json",
        }
        for ep in endpoints:
            try:
                r = requests.get(ep, headers=headers, timeout=20)
                if r.status_code == 200:
                    items = r.json().get("resources") or r.json().get("deployments") or []
                    for item in items:
                        dep_id = item.get("id") or item.get("deploymentId") or item.get("deployment_id")
                        status = item.get("status") or item.get("state")
                        model_name = (item.get("details", {}).get("resources", {}).get("model", {}).get("name") or 
                                      item.get("modelName") or item.get("scenarioId") or item.get("configurationName") or "LLM")
                        dep_url = item.get("deploymentUrl") or item.get("targetUrl") or f"{base}/v2/inference/deployments/{dep_id}"
                        found_deployments.append({
                            "id": dep_id,
                            "status": status,
                            "model": model_name,
                            "resource_group": rg,
                            "url": dep_url,
                            "raw": item
                        })
                    if found_deployments:
                        break
            except Exception:
                pass
        if found_deployments:
            break

    if found_deployments:
        print(f"  [Found {len(found_deployments)} deployment(s) in SAP AI Core]:")
        for idx, d in enumerate(found_deployments, start=1):
            is_running = str(d['status']).upper() in ('RUNNING', 'ACTIVE', 'READY')
            marker = "[OK]" if is_running else "[WARN]"
            print(f"    {idx}. {marker} ID: {d['id']} | Model: {d['model']} | Status: {d['status']} | ResourceGroup: {d['resource_group']}")
            print(f"       Inference Base: {d['url']}")
    else:
        print("  [Info] Could not auto-list deployments via /v2/lm/deployments. (May require specific AI-Resource-Group permissions).")

    return found_deployments


# -----------------------------------------------------------------------------
# 5. Test Step 2: "Hello World" Chat Completion with Candidate URLs
# -----------------------------------------------------------------------------
def build_candidate_urls(discovered: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    candidates = []
    
    # 1. User's explicit configured URL
    raw_dep = DEPLOYMENT_URL or BASE_URL
    if raw_dep:
        raw_dep = raw_dep.rstrip('/')
        
        # If user entered just a deployment ID e.g. "d12345678"
        if not raw_dep.startswith("http") and API_BASE:
            candidates.append({
                "url": f"{API_BASE}/v2/inference/deployments/{raw_dep}/chat/completions",
                "rg": RESOURCE_GROUP,
                "label": "Constructed from Deployment ID + API Base",
            })
        
        # If user entered full URL ending with /v2/inference/deployments/xxxxx
        if not raw_dep.endswith("/chat/completions"):
            candidates.append({
                "url": f"{raw_dep}/chat/completions",
                "rg": RESOURCE_GROUP,
                "label": "User DEPLOYMENT_URL + /chat/completions",
            })
        else:
            candidates.append({
                "url": raw_dep,
                "rg": RESOURCE_GROUP,
                "label": "User DEPLOYMENT_URL (as provided)",
            })

        # Try without /v2/inference if user put base URL + deployment ID
        if "/v2/inference/deployments/" not in raw_dep and raw_dep.startswith("http"):
            # Check if there's an ID at the end
            parts = raw_dep.split("/")
            if len(parts) > 3 and not parts[-1].startswith("v2"):
                dep_id = parts[-1]
                base_part = "/".join(parts[:-1])
                candidates.append({
                    "url": f"{base_part}/v2/inference/deployments/{dep_id}/chat/completions",
                    "rg": RESOURCE_GROUP,
                    "label": "Normalized with /v2/inference/deployments/{id}",
                })

    # 2. Add discovered running deployments
    for d in discovered:
        d_url = d['url'].rstrip('/')
        if not d_url.endswith("/chat/completions"):
            d_url = f"{d_url}/chat/completions"
        candidates.append({
            "url": d_url,
            "rg": d['resource_group'],
            "label": f"Discovered Deployment '{d['id']}' ({d['model']})",
        })

    # Deduplicate by (url, rg)
    seen = set()
    unique = []
    for c in candidates:
        key = (c["url"], c["rg"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def test_step_2_inference(token: str, discovered: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    print("\n[TEST 2/3] Testing 'Hello World' Chat Inference via SAP AI Core...")
    
    candidates = build_candidate_urls(discovered)
    if not candidates:
        print("  [FAIL] No candidate inference URLs found. Please check SAP_AICORE_DEPLOYMENT_URL in .env")
        return None

    messages = [
        {"role": "system", "content": "You are Nexus 2.0 finance operations assistant powered by SAP AI Core."},
        {"role": "user", "content": "Hello World! Confirm that SAP AI Core is operational for Nexus 2.0 in 1 sentence."}
    ]
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 300,
    }

    working_config = None

    for idx, cand in enumerate(candidates, start=1):
        target_url = cand["url"]
        rg = cand["rg"]
        label = cand["label"]
        
        print(f"\n  [Attempt {idx}/{len(candidates)}] {label}")
        print(f"  -> POST URL: {target_url}")
        print(f"  -> Resource-Group: {rg} | Model: {MODEL}")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": rg,
            "Content-Type": "application/json",
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(target_url, json=payload, headers=headers, timeout=60)
            elapsed = time.perf_counter() - t0
            
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices")
                if choices and isinstance(choices, list):
                    msg = choices[0].get("message", {}).get("content", "").strip()
                    usage = data.get("usage", {})
                    print(f"  [PASS] HTTP 200 OK in {elapsed:.2f}s!")
                    print(f"         Prompt tokens: {usage.get('prompt_tokens', '?')} | Completion tokens: {usage.get('completion_tokens', '?')}")
                    print("\n  " + "-" * 66)
                    print(f"  [SAP AI Core Response]:\n  \"{msg}\"")
                    print("  " + "-" * 66)
                    working_config = {"url": target_url, "rg": rg}
                    break
                else:
                    print(f"  [FAIL] HTTP 200 but unexpected JSON format: {data}")
            elif resp.status_code == 404:
                print(f"  [FAIL] HTTP 404 Resource not found in {elapsed:.2f}s.")
                print(f"         Body: {resp.text[:200]}")
            else:
                print(f"  [FAIL] HTTP {resp.status_code} in {elapsed:.2f}s.")
                print(f"         Body: {resp.text[:300]}")
        except Exception as exc:
            print(f"  [FAIL] Connection error: {exc}")

    if not working_config:
        print("\n  ====================================================================")
        print("  [DIAGNOSTIC HELP: Why HTTP 404 occurs in SAP AI Core]")
        print("  1. The DEPLOYMENT_URL format should be:")
        print("     https://api.ai.prod.<region>.aws.ml.hana.ondemand.com/v2/inference/deployments/<DEPLOYMENT_ID>")
        print("     (Make sure to include the deployment ID at the end, e.g. /v2/inference/deployments/d123456789)")
        print("  2. The RESOURCE_GROUP in .env must match the resource group where the deployment was created.")
        print("     Check your SAP AI Launchpad -> ML Operations -> Deployments to confirm.")
        print("  ====================================================================")
        return None

    return working_config


# -----------------------------------------------------------------------------
# 6. Test Step 3: Nexus Application Routing Integration
# -----------------------------------------------------------------------------
def test_step_3_app_integration(working_config: Dict[str, str]) -> bool:
    print("\n[TEST 3/3] Testing Full Nexus 2.0 Application Routing (app.llm layer)...")
    try:
        # If the working URL was corrected, set it temporarily for app test
        if working_config:
            clean_dep = working_config["url"]
            if clean_dep.endswith("/chat/completions"):
                clean_dep = clean_dep[:-len("/chat/completions")]
            os.environ["SAP_AICORE_DEPLOYMENT_URL"] = clean_dep
            os.environ["SAP_AICORE_RESOURCE_GROUP"] = working_config["rg"]

        from app.llm import explain, suggest_workflow
        from app.config import aicore_configured

        print(f"  * app.config.aicore_configured() returned: {aicore_configured()}")
        
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
        print("  Check in .env: SAP_AICORE_AUTH_URL, SAP_AICORE_CLIENT_ID, SAP_AICORE_CLIENT_SECRET")
        print("=" * 70)
        sys.exit(1)

    discovered = discover_deployments(token)
    working_config = test_step_2_inference(token, discovered)
    
    if not working_config:
        print("\n" + "=" * 70)
        print("  [RESULT] SAP AI Core Inference FAILED.")
        print("=" * 70)
        sys.exit(1)

    app_ok = test_step_3_app_integration(working_config)

    print("\n" + "=" * 70)
    if working_config and app_ok:
        print("  [SUCCESS] ALL SAP AI CORE TESTS PASSED!")
        print("  Nexus 2.0 is fully operational with SAP AI Core.")
        
        clean_dep = working_config["url"]
        if clean_dep.endswith("/chat/completions"):
            clean_dep = clean_dep[:-len("/chat/completions")]
        
        print("\n  Recommended .env settings based on this successful test:")
        print(f"    LLM_PROVIDER=sap_ai_core")
        print(f"    SAP_AICORE_RESOURCE_GROUP={working_config['rg']}")
        print(f"    SAP_AICORE_DEPLOYMENT_URL={clean_dep}")
        print(f"    SAP_AICORE_MODEL={MODEL}")
    else:
        print("  [WARNING] Direct inference succeeded, but app routing encountered issues.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()