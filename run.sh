#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cleanup() { jobs -p | xargs -r kill 2>/dev/null || true; }
trap cleanup EXIT INT TERM
(cd "$ROOT/backend" && uv sync && uv run uvicorn app.main:app --reload --port 8000) &
(cd "$ROOT/frontend" && npm install && npm run dev) &
wait
