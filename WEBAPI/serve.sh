#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9000}"

cd "$PROJECT_ROOT"

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn is not installed. Install dependencies with: pip install -r WEBAPI/requirements.txt" >&2
  exit 1
fi

# Kill existing process on the port if any
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
fi

echo "Starting Script Runner WEBAPI at ${HOST}:${PORT} (dashboard available at http://${HOST}:${PORT})"
exec uvicorn WEBAPI.api:app --host "$HOST" --port "$PORT"
