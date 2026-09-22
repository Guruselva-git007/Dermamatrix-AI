#!/usr/bin/env bash
# Fast, read-only check for the local Flask + MySQL stack.
set -euo pipefail

app_port="${DERMAMATRIX_PORT:-8000}"
health_url="${DERMAMATRIX_HEALTH_URL:-http://127.0.0.1:$app_port/api/health}"

if ! response="$(curl --fail --silent --show-error --max-time 8 "$health_url")"; then
  echo "DermaMatrix is not responding at $health_url." >&2
  echo "Start it with: DERMAMATRIX_PORT=$app_port bash backend/scripts/run_app.sh" >&2
  exit 1
fi

if [[ "$response" != *'"status":"ok"'* || "$response" != *'"database":"mysql-connected"'* ]]; then
  echo "DermaMatrix responded, but the local stack is not fully ready:" >&2
  echo "$response" >&2
  exit 1
fi

echo "DermaMatrix local stack is ready: Flask API and MySQL are connected."
