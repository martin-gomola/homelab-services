#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PROJECT_DIR}/.env"

DATA_DIR="${DATA_DIR:-/srv/docker}"
HA_CONFIG_DIR="${DATA_DIR}/homeassistant/config"
LIVE_DASHBOARD_DIR="${HA_CONFIG_DIR}/dashboards"
REPO_DASHBOARD_DIR="${PROJECT_DIR}/dashboards"
LIVE_TEMPLATE_DIR="${HA_CONFIG_DIR}/templates"
REPO_TEMPLATE_DIR="${PROJECT_DIR}/templates"

if [ ! -d "${REPO_DASHBOARD_DIR}" ]; then
  echo "No tracked dashboards found in ${REPO_DASHBOARD_DIR}"
  exit 1
fi

mkdir -p "${LIVE_DASHBOARD_DIR}"
cp -R "${REPO_DASHBOARD_DIR}/." "${LIVE_DASHBOARD_DIR}/"

if [ -d "${REPO_TEMPLATE_DIR}" ]; then
  mkdir -p "${LIVE_TEMPLATE_DIR}"
  cp -R "${REPO_TEMPLATE_DIR}/." "${LIVE_TEMPLATE_DIR}/"
fi

echo "Synced dashboards to ${LIVE_DASHBOARD_DIR}"
echo "Restart Home Assistant to load any dashboard or Lovelace wiring changes."
