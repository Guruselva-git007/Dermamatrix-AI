#!/usr/bin/env bash
# Fast, read-only presentation preflight for the local Flask + MySQL stack.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "$script_dir/.." && pwd)"
project_dir="$(cd "$backend_dir/.." && pwd)"
git_bin="/usr/bin/git"
curl_bin="/usr/bin/curl"
app_port="${DERMAMATRIX_PORT:-8000}"
health_url="${DERMAMATRIX_HEALTH_URL:-http://127.0.0.1:$app_port/api/health}"
registry_url="${DERMAMATRIX_REGISTRY_URL:-http://127.0.0.1:$app_port/api/model-registry}"
weights_path="$backend_dir/models/ham10000_resnet34_research.ptw"

fail() {
  echo "DermaMatrix preflight failed: $*" >&2
  exit 1
}

[[ -f "$project_dir/frontend/index.html" && -f "$project_dir/frontend/app.js" ]] || fail "frontend files are missing from $project_dir."
[[ -x "$project_dir/.venv/bin/python" || -x "$project_dir/.ml-venv/bin/python" ]] || fail "project Python environment is missing."
[[ -f "$backend_dir/.env" ]] || fail "local backend configuration is missing."
[[ -f "$weights_path" ]] || fail "required Skin research weight is missing."

git_root="$($git_bin -C "$project_dir" rev-parse --show-toplevel 2>/dev/null)" || fail "the project is not inside its Git workspace."
branch="$($git_bin -C "$project_dir" branch --show-current)"
[[ "$branch" == "main" ]] || fail "expected Git branch main, found ${branch:-detached HEAD}."
[[ -z "$($git_bin -C "$project_dir" status --porcelain)" ]] || fail "working tree is not clean; review changes before presenting."
[[ "$($git_bin -C "$project_dir" rev-parse HEAD)" == "$($git_bin -C "$project_dir" rev-parse origin/main)" ]] || fail "local HEAD is not synchronized with origin/main."

if ! response="$($curl_bin --fail --silent --show-error --max-time 8 "$health_url")"; then
  echo "DermaMatrix is not responding at $health_url." >&2
  echo "Start it with: $project_dir/Start DermaMatrix.command" >&2
  exit 1
fi

if [[ "$response" != *'"status":"ok"'* || "$response" != *'"database":"mysql-connected"'* ]]; then
  echo "DermaMatrix responded, but the local stack is not fully ready:" >&2
  echo "$response" >&2
  exit 1
fi

registry="$($curl_bin --fail --silent --show-error --max-time 8 "$registry_url")" || fail "model registry is not reachable at $registry_url."
[[ "$registry" == *'"capabilities"'* ]] || fail "model registry response is incomplete."

listener_pids="$(/usr/sbin/lsof -nP -t -iTCP:"$app_port" -sTCP:LISTEN 2>/dev/null | /usr/bin/sort -u)"
[[ -n "$listener_pids" ]] || fail "no loopback listener was found on port $app_port."
listener_in_workspace=false
while IFS= read -r pid; do
  cwd="$(/usr/sbin/lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | /usr/bin/sed -n 's/^n//p')"
  if [[ "$cwd" == "$backend_dir" ]]; then
    listener_in_workspace=true
    break
  fi
done <<< "$listener_pids"
[[ "$listener_in_workspace" == true ]] || fail "the listener on port $app_port is not running from $backend_dir."

echo "DermaMatrix presentation preflight passed: main is clean and synchronized; local API, MySQL, registry, Skin weight, and canonical listener are ready."
