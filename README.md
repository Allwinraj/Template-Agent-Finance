# Nexus 2.0 — Finance Operations Agent Platform

## What This Is

Nexus 2.0 is a configuration-driven finance agent platform. A user describes a finance use case, the LLM designs an agent pipeline with calculation and rule bindings, the user tweaks the configuration in the wizard, and the platform executes the workflow end-to-end with full audit lineage.

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+ and npm
- **Git**
- **OpenRouter API key** (free tier works) — get one at https://openrouter.ai/keys
- *(Optional)* **SAP AI Core** credentials if you want to use SAP as the LLM provider instead of OpenRouter

## Quick Start

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd Template_agent
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=liquid/lfm-2.5-2.6b:free
OPENROUTER_FALLBACK_MODELS=inclusionai/ling-3.0-flash-fin:free,nvidia/nemotron-3.5-lightning:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Leave `LLM_PROVIDER=openrouter` unless you have SAP AI Core configured.

### 4. Run the backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at **http://localhost:8000**

API docs: **http://localhost:8000/docs**

### 5. Run the frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:3000**

### 6. Open the app

Visit **http://localhost:3000**

- Landing page → **Enter the Platform** → Sign in with the demo account
- Then go to **Create Agent** to build a new workflow

## Project Structure

```
backend/
  app/
    api/             # FastAPI routes
    agents/          # A1–A6 agent implementations
    engines/         # Calculation engine + Rule engine
    llm/             # OpenRouter + SAP AI Core clients
    services/        # Orchestrator, registry, audit
    config.py        # Environment config
    main.py          # FastAPI app entrypoint
    storage.py       # JSON file persistence
  .env.example       # Environment template

frontend/
  src/
    pages/           # React pages (Landing, SignIn, Dashboard, CreateAgent, AgentChat, AgentLibrary)
    data/            # Mock data / agent catalog
    styles/          # Global CSS
  package.json
```

## How It Works

1. **Describe** — User types a finance use case in natural language
2. **Add Data** — Upload Excel/CSV files; backend profiles columns and sample rows
3. **Pipeline** — LLM designs the agent flow (A1→A6), selects calculations and rules from the engine library, returns a JSON config
4. **Configure** — User can tweak calculation bindings, rule parameters, output format, and thresholds via the wizard
5. **Create** — Config is saved to the registry as a published workflow
6. **Run** — Orchestrator executes agents in sequence: A1→A2→A3→A4→A5→A6, passing JSON payloads between them

## LLM Provider

Two providers are supported:

| Provider | Env var | Notes |
|---|---|---|
| OpenRouter | `LLM_PROVIDER=openrouter` | Free models with auto-fallback. Default. |
| SAP AI Core | `LLM_PROVIDER=sap_ai_core` | Requires `SAP_AICORE_*` env vars |

Both providers share the same prompt contract, JSON recovery logic, and normalization pipeline.

## Engine Library

Calculators and rules are versioned Python functions:

- **Calculation engine**: `backend/app/engines/calculation_engine.py`
- **Rule engine**: `backend/app/engines/rule_engine.py`

The LLM prompt includes the full catalog so it picks only valid engine names and versions.

## Data Storage

Workflows, runs, and audit events are stored in JSON files under `backend/data/`. For production use, replace `storage.py` with a real database.

## Troubleshooting

| Issue | Fix |
|---|---|
| Backend won't start — port 8000 in use | Change port: `uvicorn app.main:app --port 8001` |
| Frontend won't start — port 3000 in use | `PORT=3001 npm run dev` |
| LLM pipeline design is slow | Primary model is `liquid/lfm-2.5-2.6b:free` (fastest). Falls back automatically if slow. |
| LLM returns invalid JSON | The platform retries up to 3 times with correction messages. If it still fails, a deterministic mock template is used. |
| "workflow not found" after creation | OneDrive sync may have altered the JSON store. Set `NEXUS_DATA_DIR` to a folder outside OneDrive. |

## License

Internal use only.
