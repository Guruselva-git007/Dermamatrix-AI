#!/bin/zsh
# Double-click this file in Finder to open DermaMatrix correctly.

set -u

APP_DIR="${0:A:h}"
INSTALLER="${APP_DIR}/scripts/install_macos_local_service.sh"
HEALTH_URL="http://127.0.0.1:8000/api/health"
APP_URL="http://127.0.0.1:8000/"

health_ready() {
  /usr/bin/curl --silent --show-error --connect-timeout 1 --max-time 2 "${HEALTH_URL}" | /usr/bin/grep -q '"service":"dermamatrix-api"'
}

if ! health_ready; then
  "${INSTALLER}" || {
    print -u2 "DermaMatrix could not start. See ~/Library/Logs/DermaMatrix/local-server-error.log"
    exit 1
  }
fi

for _ in {1..20}; do
  if health_ready; then
    /usr/bin/open "${APP_URL}"
    exit 0
  fi
  /bin/sleep 1
done

print -u2 "DermaMatrix did not become ready. See ~/Library/Logs/DermaMatrix/local-server-error.log"
exit 1
