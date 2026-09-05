#!/usr/bin/env bash
# Start the DermaMatrix API with the project's virtual environment.
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

if ! "$python_bin" -c "import flask, pymysql" >/dev/null 2>&1; then
  echo "Required Python packages are missing from $python_bin." >&2
  echo "Install them with: $python_bin -m pip install -r backend/requirements.txt" >&2
  exit 1
fi

echo "Starting DermaMatrix at http://127.0.0.1:8000"
exec "$python_bin" "$backend_dir/app.py"
