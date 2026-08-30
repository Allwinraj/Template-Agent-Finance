# Nexus 2.0 — Frontend

A classy, elite React front end for the **Configurable Finance Operations Agent Platform**, built with Vite + React Router. All backend values are currently **hardcoded** in `src/data/mockData.js` — swap them for real API calls later.

## Run it

```bash
npm install
npm run dev        # → http://localhost:3000
```

Production build:

```bash
npm run build
npm run preview
```

> Note: if `npm` is blocked by PowerShell execution policy, use `npm.cmd` or run from cmd.exe. If `node` is not on PATH, prefix with `set PATH=C:\Program Files\nodejs;%PATH%`.

## Pages

| Route | Description |
|---|---|
| `/` | Animated landing — particle constellation, orbs, "How it works", **six agents explained in plain English**, trust lifecycle |
| `/signin` | Split-panel sign-in with static labels (no overlap), demo accounts |
| `/app` | **Welcome Dashboard** — agents live status, donut chart, match-rate bars, platform services health, activity feed |
| `/app/create-agent` | **Create Agent wizard** (per README): Describe → Nexus suggests → Select agents → Configure → Rules & Calculations → Test → Submit for approval |
| `/app/users` | User management — table + Add User form (role, company-code access) |
| `/app/settings` | Placeholder shell with tabs (Profile, Platform, Audit Policy, Notifications) — no content yet |

## Demo credentials (hardcoded)

| Role | Email | Password |
|---|---|---|
| Finance Admin | `admin@nexus.io` | `admin123` |
| Finance Reviewer | `reviewer@nexus.io` | `review123` |

Auth is simulated in `src/App.jsx` (sessionStorage). Replace `signIn`/`signOut` with your real auth API when ready.

## The six agents (plain-English)

| Agent | What it does |
|---|---|
| **A1 Capture** 📥 | Reads bank statements, SAP exports, Excel, CSV and PDF files |
| **A2 Harmonize** 🔄 | Converts different formats/column names into one standard finance format |
| **A3 Match** 🔗 | Automatically matches bank lines to GL entries, invoices to POs |
| **A4 Validate** 🛡️ | Applies your rules and tolerances, recommends an outcome |
| **A5 Explain** 📊 | Creates reports and shows the evidence behind every number |
| **A6 Coordinate** 🧭 | Sends anything unusual to the right person for review |

## Where to connect the backend later

- `src/data/mockData.js` — replace each export with API calls (agents, services, KPIs, users, rules, calculations)
- `src/pages/SignIn.jsx` — replace `DEMO_USERS` + `setTimeout` with a real `POST /auth/login`
- `src/App.jsx` — replace sessionStorage auth with token-based auth
- `src/pages/CreateAgent.jsx` — wire the wizard steps to the Configuration Registry APIs (`POST /registry/...`)

## Design system

- Theme: **Obsidian · Violet · Cyan** (royal, elite aesthetic)
- Fonts: Playfair Display (display), Inter (body), JetBrains Mono (data)
- Global tokens & animation library: `src/styles/global.css`