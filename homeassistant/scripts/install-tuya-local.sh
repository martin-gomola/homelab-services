#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PROJECT_DIR}/.env"

DATA_DIR="${DATA_DIR:-/srv/docker}"
HA_CONFIG_DIR="${DATA_DIR}/homeassistant/config"
LIVE_COMPONENT_DIR="${HA_CONFIG_DIR}/custom_components/tuya_local"
REPO_OVERLAY_DIR="${PROJECT_DIR}/custom_components/tuya_local"
TUYA_LOCAL_TAG="${TUYA_LOCAL_TAG:-2026.3.1}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "Installing tuya_local ${TUYA_LOCAL_TAG} into ${LIVE_COMPONENT_DIR}"
mkdir -p "${HA_CONFIG_DIR}/custom_components"

git clone --depth 1 --branch "${TUYA_LOCAL_TAG}" \
  https://github.com/make-all/tuya-local.git \
  "${TMP_DIR}/tuya-local"

rm -rf "${LIVE_COMPONENT_DIR}"
cp -R "${TMP_DIR}/tuya-local/custom_components/tuya_local" "${LIVE_COMPONENT_DIR}"

if [ -d "${REPO_OVERLAY_DIR}" ]; then
  echo "Applying repo overlays from ${REPO_OVERLAY_DIR}"
  cp -R "${REPO_OVERLAY_DIR}/." "${LIVE_COMPONENT_DIR}/"
fi

echo "tuya_local installed."
echo "Restart Home Assistant to load the updated custom component."
