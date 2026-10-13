#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR/backend"
[[ -x .venv/bin/python ]] || { echo "Run bash scripts/setup.sh from the repository root first."; exit 1; }
[[ -f app/data/kb_index.json ]] || .venv/bin/python -m app.ingest
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
