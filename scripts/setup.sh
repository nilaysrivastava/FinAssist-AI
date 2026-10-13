#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
command -v python3.11 >/dev/null || { echo "Install Python 3.11 before setup."; exit 1; }
command -v node >/dev/null || { echo "Install Node.js 24 before setup (see .nvmrc)."; exit 1; }
node -e 'if(Number(process.versions.node.split(".")[0])<24){console.error("Use Node.js 24 or newer; nvm install && nvm use");process.exit(1)}'
python3.11 -m venv "backend/.venv"
"backend/.venv/bin/python" -m pip install -r "backend/requirements.lock.txt"
if [[ ! -f "backend/.env" && -f "backend/.env.example" ]]; then cp "backend/.env.example" "backend/.env"; fi
if [[ ! -f "frontend/.env.local" && -f "frontend/.env.example" ]]; then cp "frontend/.env.example" "frontend/.env.local"; fi
"backend/.venv/bin/python" scripts/bootstrap_demo.py
npm ci --prefix "frontend"
echo "Dependencies ready. Set your key in backend/.env, then use scripts/run-backend.sh and scripts/run-frontend.sh in separate terminals."
