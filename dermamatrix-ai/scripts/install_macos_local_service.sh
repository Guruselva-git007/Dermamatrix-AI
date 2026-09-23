#!/bin/zsh
# Install or refresh DermaMatrix's local-only macOS launch agent.
# The service binds Flask to 127.0.0.1 and is not a network deployment.

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
APP_DIR="${SCRIPT_DIR:h}"
PYTHON_BIN="${APP_DIR}/.venv/bin/python"
BACKEND_DIR="${APP_DIR}/backend"
PLIST_DIR="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/DermaMatrix"
PLIST_PATH="${PLIST_DIR}/com.dermamatrix.local-server.plist"
USER_ID="$(/usr/bin/id -u)"
SERVICE_NAME="gui/${USER_ID}/com.dermamatrix.local-server"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  print -u2 "DermaMatrix's Python environment is missing: ${PYTHON_BIN}"
  exit 1
fi

/bin/mkdir -p "${PLIST_DIR}" "${LOG_DIR}"

# Updating the service is safe: it is bound exclusively to the current user's
# loopback interface and contains no credentials.
/bin/launchctl bootout "${SERVICE_NAME}" >/dev/null 2>&1 || true

cat > "${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.dermamatrix.local-server</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${BACKEND_DIR}/app.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${BACKEND_DIR}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>DERMAMATRIX_PORT</key>
    <string>8000</string>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>
  <key>ProcessType</key>
  <string>Background</string>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/local-server.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/local-server-error.log</string>
</dict>
</plist>
PLIST

/usr/bin/plutil -lint "${PLIST_PATH}" >/dev/null
/bin/launchctl bootstrap "gui/${USER_ID}" "${PLIST_PATH}"
/bin/launchctl kickstart -k "${SERVICE_NAME}"
print "DermaMatrix local service is installed and listening only at http://127.0.0.1:8000/."
