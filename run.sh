#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Pressure Room API (production)..."
(
  cd "$ROOT/backend"
  uv sync
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
) &

API_PID=$!

echo "Building Pressure Room web app..."
(
  cd "$ROOT/frontend"
  npm install
  npm run build
  npm run start
) &
WEB_PID=$!

echo "Pressure Room production processes started."
echo "API PID: $API_PID"
echo "Web PID: $WEB_PID"
echo "Open port 3000 (or your reverse-proxy URL) in the browser."

wait
