import os
import requests

# 1. Base Credentials (Ensure these are exported in your environment)
AICORE_API_URL = os.getenv("AICORE_API_URL")
_AICORE_DEPLOY_ID = os.getenv("AICORE_DEPLOYMENT_ID") 
AICORE_RG = os.getenv("AICORE_RESOURCE_GROUP", "default")
XSUAA_URL = os.getenv("XSUAA_URL")
XSUAA_CLIENT_ID = os.getenv("XSUAA_CLIENT_ID")
XSUAA_CLIENT_SECRET = os.getenv("XSUAA_CLIENT_SECRET")

# 2. Model Registry configuration
MODELS = {
    "claude": {
        "label": "claude-4.7-opus",
        "deploy_id": _AICORE_DEPLOY_ID,
        "format": "anthropic",
    },
    "gpt55": {
        "label": "gpt-5.5",
        "deploy_id": os.getenv("AICORE_GPT55_DEPLOYMENT_ID", "dcad171471db5a4c"),
        "format": "openai",
        "api_version": os.getenv("AICORE_OPENAI_API_VERSION", "2024-12-01-preview"),
    },
    "gpt4o_mini": {
        "label": "gpt-4o-mini",
        "deploy_id": os.getenv("AICORE_GPT40_MINI_DEPLOYMENT_ID", "dfe7e04bfb45b361"),
        "format": "openai",
        "api_version": os.getenv("AICORE_OPENAI_API_VERSION", "2024-12-01-preview"),
    },
    "gpt41": {
        "label": "gpt-4.1",
        "deploy_id": os.getenv("AICORE_GPT41_DEPLOYMENT_ID", "d7cec98f1a47f4f3"),
        "format": "openai",
        "api_version": os.getenv("AICORE_OPENAI_API_VERSION", "2024-12-01-preview"),
    },
    "gpt4o": {
        "label": "gpt-4o",
        "deploy_id": os.getenv("AICORE_GPT40_DEPLOYMENT_ID", "db87ce5524bf96d9"),
        "format": "openai",
        "api_version": os.getenv("AICORE_OPENAI_API_VERSION", "2024-12-01-preview"),
    }
}

def test_all_models():
    print("Fetching XSUAA Token...")
    token_response = requests.post(
        f"{XSUAA_URL}/oauth/token",
        data={"grant_type": "client_credentials", "client_id": XSUAA_CLIENT_ID, "client_secret": XSUAA_CLIENT_SECRET},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15.0
    )
    token_response.raise_for_status()
    headers = {
        "Authorization": f"Bearer {token_response.json()['access_token']}",
        "AI-Resource-Group": AICORE_RG,
        "Content-Type": "application/json"
    }

    # Iterate through every model configuration
    for key, config in MODELS.items():
        print(f"\n--- Testing {config['label']} (ID: {config.get('deploy_id')}) ---")
        
        if not config.get("deploy_id"):
            print("Skipped: No deployment ID configured.")
            continue

        try:
            # Route logic based on API format 
            if config["format"] == "openai":
                url = f"{AICORE_API_URL}/v2/inference/deployments/{config['deploy_id']}/chat/completions?api-version={config['api_version']}"
                payload = {
                    "messages": [{"role": "user", "content": "Say 'Hello World' in one short sentence."}],
                    "max_tokens": 50
                }
            elif config["format"] == "anthropic":
                url = f"{AICORE_API_URL}/v2/inference/deployments/{config['deploy_id']}/invoke"
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 50,
                    "messages": [{"role": "user", "content": "Say 'Hello World' in one short sentence."}]
                }
            else:
                print(f"Skipped: Unknown format '{config['format']}'")
                continue

            response = requests.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            
            # Parse response structure depending on format
            if config["format"] == "openai":
                print(f"Response: {result['choices'][0]['message']['content']}")
            else:
                print(f"Response: {result['content'][0]['text']}")

        except Exception as e:
            print(f"Failed: {str(e)}")

if __name__ == "__main__":
    test_all_models()
