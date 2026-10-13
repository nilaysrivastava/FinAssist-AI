#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR/frontend"
exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
