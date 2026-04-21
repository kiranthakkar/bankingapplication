#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "Missing .venv/bin/uvicorn. Create the virtual environment and install requirements first." >&2
  exit 1
fi

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

RELOAD_FLAG=""
if [[ "${APP_RELOAD:-true}" == "true" ]]; then
  RELOAD_FLAG="--reload"
fi

exec ".venv/bin/uvicorn" main:app $RELOAD_FLAG --host "$HOST" --port "$PORT"
