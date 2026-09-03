#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  uv sync
  uv run streamlit run app.py
else
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  streamlit run app.py
fi
