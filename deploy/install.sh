#!/usr/bin/env bash
# Installs the Greek visa checker on a fresh Ubuntu 22.04 VM.
# Run on the VM as the ubuntu user:
#   curl -fsSL https://raw.githubusercontent.com/AIFahim/greec_visa_check/main/deploy/install.sh | bash
set -euo pipefail

REPO_URL="https://github.com/AIFahim/greec_visa_check.git"
APP_DIR="${HOME}/greec_visa_check"
VENV_DIR="${HOME}/.venv"
SERVICE_NAME="greek-visa-check"

echo ">> Updating apt and installing system packages..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

if [[ ! -d "${APP_DIR}" ]]; then
    echo ">> Cloning ${REPO_URL} into ${APP_DIR}..."
    git clone "${REPO_URL}" "${APP_DIR}"
else
    echo ">> Repo already present; pulling latest..."
    git -C "${APP_DIR}" pull --ff-only
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    echo ">> Creating virtualenv at ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
fi

echo ">> Installing Python dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo ">> Installing Playwright Chromium + system deps..."
"${VENV_DIR}/bin/python" -m playwright install --with-deps chromium

if [[ ! -f "${APP_DIR}/.env" ]]; then
    echo ">> Creating .env from template (fill this in before enabling the timer)..."
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"
fi

echo ">> Installing systemd service + timer..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service >/dev/null <<EOF
[Unit]
Description=Greek visa slot checker (one-shot)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${VENV_DIR}/bin/python ${APP_DIR}/run_once.py
Nice=5
TimeoutStartSec=180
EOF

sudo tee /etc/systemd/system/${SERVICE_NAME}.timer >/dev/null <<EOF
[Unit]
Description=Run Greek visa slot checker every minute

[Timer]
OnBootSec=30s
OnUnitActiveSec=60s
AccuracySec=5s
Persistent=true
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload

cat <<'NEXT'

----------------------------------------------------------------
Install complete.

NEXT STEPS:
  1. Edit credentials:
         nano ~/greec_visa_check/.env
  2. Enable the timer:
         sudo systemctl enable --now greek-visa-check.timer
  3. Watch logs:
         journalctl -u greek-visa-check.service -f
  4. Check schedule:
         systemctl list-timers | grep greek-visa
----------------------------------------------------------------
NEXT
