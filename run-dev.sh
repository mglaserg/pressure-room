#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cat <<MSG
Starting Pressure Room in DEVELOPMENT mode.
If you access this dev server through a remote hostname/IP, set:
  PRESSURE_ROOM_ALLOWED_DEV_ORIGINS=host-or-ip[,second-host]
Example:
  PRESSURE_ROOM_ALLOWED_DEV_ORIGINS=100.69.49.155 ./run-dev.sh
MSG

(
  cd "$ROOT/backend"
  uv sync
  uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &

(
  cd "$ROOT/frontend"
  npm install
  npm run dev
) &

wait
