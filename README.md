# FinAssist AI

A finance-support demo derived from the agentic chatbot. Includes demo login, hybrid retrieval, customer-record tools, safety checks, memory, human approval and explicit confirmation before email summaries.

## Stack and layout

FastAPI, Groq, local JSON retrieval, React, TypeScript, Tailwind, Vite.

- `backend/`: Python backend, `requirements.txt` for direct imports, and `requirements.lock.txt` for the captured environment.
- `frontend/`: browser frontend, with exact npm dependency versions in `package-lock.json`.
- `scripts/`: repeatable setup and separate backend/frontend launch commands.

Only synthetic demo seeds are included. User registrations, conversations, email records, tickets and memory are local runtime data.

## Clone and install

Prerequisites: Git, Python 3.11 (local environments captured with 3.11.15 where applicable), Node.js 24 and npm. `.python-version` and `.nvmrc` record the intended runtimes. For a private repository, authenticate with GitHub first (`gh auth login`) or use an authorized SSH key.

```bash
git clone https://github.com/nilaysrivastava/FinAssist-AI.git
cd FinAssist-AI
# If nvm is installed:
nvm install
nvm use
bash scripts/setup.sh
```

If Node.js 24 is already installed, omit the two `nvm` commands. Setup recreates the virtual environment and installs dependencies from both lockfiles. It creates local environment files only when they do not exist, and demo bootstrap never replaces existing runtime records.

## Configure

Set `GROQ_API_KEY` in `backend/.env`, configure `GROQ_MODEL` and `GROQ_GUARD_MODEL`, and replace `APP_SECRET`. The code reads `APP_SECRET`, not `JWT_SECRET`. The frontend supports `VITE_API_BASE_URL` and the fallback `VITE_API_BASE`.

Edit `backend/.env` after setup. `.env.example` contains placeholders; real keys and local secrets are deliberately excluded from Git. Your existing local `.env` files were retained on the laptop during cleanup.

## Run

Use two terminals, each starting in the repository root:

```bash
# Terminal 1
bash scripts/run-backend.sh
```

```bash
# Terminal 2
bash scripts/run-frontend.sh
```

Open **http://127.0.0.1:5173**. API documentation is at **http://127.0.0.1:8000/docs**. Stop each process with Ctrl+C. The launch scripts enforce the expected frontend port and avoid backend reload loops while JSON state is changing.

Quick API check:

```bash
curl --fail http://127.0.0.1:8000/api/health
```

Run projects one at a time: they share ports 8000 and 5173. For remote deployment or different ports, update both the frontend API setting and backend CORS configuration where applicable.

## Verify and rebuild

```bash
npm run build --prefix frontend
backend/.venv/bin/python -m pip check
```

`requirements.lock.txt` records the installed package versions captured during backup. It includes transitive packages from this laptop; use `requirements.txt` if you intentionally want to resolve a smaller fresh environment, then check behavior before updating the locks. Native packages may need platform-specific wheels.

## Local data and future storage cleanup

Git stores source code, lockfiles, configuration examples and project inputs/demo seeds. It excludes installed dependencies, build output, caches, real `.env` files, uploads, local databases, and live conversation/account state. These private/local files were retained during cleanup. Preserve them separately if you later remove the complete project folder.

It is safe to remove `node_modules/`, virtual environments and `dist/` when the project is stopped; `bash scripts/setup.sh` reinstalls the dependencies. Keep source, lockfiles, `.env`, project inputs and local records. Avoid `docker compose down -v` if you need existing PostgreSQL data.

## Troubleshooting

- **Node/Vite engine or crypto errors:** switch to Node.js 24 before reinstalling with `npm ci`.
- **Missing Python module:** use the interpreter in this project's `.venv` and rerun setup.
- **API authentication/model errors:** check the configured provider key and model availability; no paid model requests are made by setup.
- **Browser cannot reach API:** start the backend first and confirm port 8000 and the configured API URL/CORS origin.
- **Port already in use:** stop another project's servers before launching this one.

## Demo accounts

Setup seeds synthetic demo data only when runtime files are missing. Existing local accounts remain intact.

- Customer: `aarav.customer@finassist-demo.com` / `Customer@123` (created by application startup).
- Employee: `meera.employee@finassist-demo.com` / `Employee@123`.

To re-index edited knowledge sources, run `cd backend` followed by `.venv/bin/python -m app.ingest`. The index is derived from the versioned knowledge-source files.
