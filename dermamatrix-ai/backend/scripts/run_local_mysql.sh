#!/usr/bin/env bash
# Start an isolated MySQL instance for this local college project.
# It does not modify or depend on the system MySQL service.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "$script_dir/.." && pwd)"
mysql_bin="${MYSQLD_BIN:-/usr/local/mysql/bin/mysqld}"
mysql_client="${MYSQL_BIN:-/opt/homebrew/bin/mysql}"
data_dir="$backend_dir/.local-mysql/data"
socket_path="/tmp/dermamatrix-ai-mysql.sock"
pid_path="$backend_dir/.local-mysql/mysql.pid"
log_path="$backend_dir/.local-mysql/mysql.log"
port="${DERMAMATRIX_MYSQL_PORT:-3307}"

if [[ ! -f "$backend_dir/.env" ]]; then
  echo "Create $backend_dir/.env with MYSQL_PASSWORD before starting local MySQL." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$backend_dir/.env"
set +a
app_password="${MYSQL_PASSWORD:?MYSQL_PASSWORD is required in backend/.env}"
sql_password="${app_password//\'/\\\'}"

if [[ ! -x "$mysql_bin" || ! -x "$mysql_client" ]]; then
  echo "MySQL binaries were not found. Install MySQL Community Server first." >&2
  exit 1
fi

mkdir -p "$backend_dir/.local-mysql"
if [[ ! -d "$data_dir/mysql" ]]; then
  "$mysql_bin" --no-defaults --initialize-insecure --datadir="$data_dir"
fi

if [[ -f "$pid_path" ]] && kill -0 "$(cat "$pid_path")" 2>/dev/null; then
  echo "DermaMatrix local MySQL is already running on port $port."
else
  rm -f "$socket_path" "$pid_path"
  "$mysql_bin" --no-defaults --datadir="$data_dir" --socket="$socket_path" --pid-file="$pid_path" --port="$port" --mysqlx-port=33061 --bind-address=127.0.0.1 --log-error="$log_path" --skip-name-resolve --daemonize
fi

# The app's MYSQL_* settings are loaded above, but MySQL's CLI also treats some
# similarly named environment values as client options. Clear them for the root
# bootstrap connection so an app host/port cannot corrupt the socket protocol.
mysql_root=(env -u MYSQL_HOST -u MYSQL_PORT -u MYSQL_USER -u MYSQL_PASSWORD -u MYSQL_DATABASE "$mysql_client" --no-defaults --protocol=SOCKET --socket="$socket_path" -u root)
for _ in {1..30}; do
  if "${mysql_root[@]}" -e "SELECT 1" >/dev/null 2>&1; then
    "${mysql_root[@]}" <<SQL
CREATE DATABASE IF NOT EXISTS dermamatrix_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'dermamatrix_app'@'127.0.0.1' IDENTIFIED BY '${sql_password}';
CREATE USER IF NOT EXISTS 'dermamatrix_app'@'localhost' IDENTIFIED BY '${sql_password}';
ALTER USER 'dermamatrix_app'@'127.0.0.1' IDENTIFIED BY '${sql_password}';
ALTER USER 'dermamatrix_app'@'localhost' IDENTIFIED BY '${sql_password}';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON dermamatrix_ai.* TO 'dermamatrix_app'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON dermamatrix_ai.* TO 'dermamatrix_app'@'localhost';
FLUSH PRIVILEGES;
SQL
    echo "DermaMatrix local MySQL is ready on 127.0.0.1:$port."
    exit 0
  fi
  sleep 1
done

echo "MySQL did not become ready. See $log_path" >&2
exit 1
