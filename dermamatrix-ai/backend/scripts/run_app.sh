#!/usr/bin/env bash
# Start the DermaMatrix API with the project's virtual environment and Gunicorn.
# By default this also makes sure the isolated local MySQL service is ready.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "$script_dir/.." && pwd)"
project_dir="$(cd "$backend_dir/.." && pwd)"

if [[ -x "$project_dir/.venv/bin/python" ]]; then
  python_bin="$project_dir/.venv/bin/python"
elif [[ -x "$project_dir/.ml-venv/bin/python" ]]; then
  python_bin="$project_dir/.ml-venv/bin/python"
else
  echo "No project virtual environment was found." >&2
  echo "Create one with: python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt" >&2
  exit 1
fi

if [[ "${DERMAMATRIX_START_MYSQL:-true}" == "true" ]]; then
  bash "$script_dir/run_local_mysql.sh"
fi

if ! "$python_bin" -c "import flask, gunicorn, pymysql" >/dev/null 2>&1; then
  echo "Required Python packages are missing from $python_bin." >&2
  echo "Install them with: $python_bin -m pip install -r backend/requirements.txt" >&2
  exit 1
fi

app_port="${DERMAMATRIX_PORT:-8000}"
web_workers="${DERMAMATRIX_WEB_CONCURRENCY:-1}"
if ! [[ "$web_workers" =~ ^[1-9][0-9]*$ ]]; then
  echo "DERMAMATRIX_WEB_CONCURRENCY must be a positive whole number." >&2
  exit 1
fi

# A single worker is the deliberate default: it avoids loading the optional ML
# model more than once on a presentation laptop.  Bind to loopback so a local
# demo is never exposed to the surrounding network by accident.
echo "Starting DermaMatrix at http://127.0.0.1:$app_port with Gunicorn ($web_workers worker(s))"
exec "$python_bin" -m gunicorn \
  --chdir "$backend_dir" \
  --bind "127.0.0.1:$app_port" \
  --workers "$web_workers" \
  --timeout 120 \
  --access-logfile - \
  app:app
