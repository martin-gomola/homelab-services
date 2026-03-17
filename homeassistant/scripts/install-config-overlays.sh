#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PROJECT_DIR}/.env"

DATA_DIR="${DATA_DIR:-/srv/docker}"
HA_CONFIG_DIR="${DATA_DIR}/homeassistant/config"
LIVE_THEME_DIR="${HA_CONFIG_DIR}/themes"
REPO_THEME_DIR="${PROJECT_DIR}/themes"
LIVE_COMMUTE_DIR="${HA_CONFIG_DIR}/commute"
REPO_COMMUTE_DIR="${PROJECT_DIR}/commute"

mkdir -p "${HA_CONFIG_DIR}"

if [ -f "${PROJECT_DIR}/configuration.yaml" ]; then
  cp "${PROJECT_DIR}/configuration.yaml" "${HA_CONFIG_DIR}/configuration.yaml"
  echo "Synced configuration.yaml to ${HA_CONFIG_DIR}"
else
  echo "No tracked configuration.yaml found in ${PROJECT_DIR}"
  exit 1
fi

if [ -f "${PROJECT_DIR}/command_line.yaml" ]; then
  cp "${PROJECT_DIR}/command_line.yaml" "${HA_CONFIG_DIR}/command_line.yaml"
  echo "Synced command_line.yaml to ${HA_CONFIG_DIR}"
fi

if [ -d "${REPO_THEME_DIR}" ]; then
  mkdir -p "${LIVE_THEME_DIR}"
  cp -R "${REPO_THEME_DIR}/." "${LIVE_THEME_DIR}/"
  echo "Synced themes to ${LIVE_THEME_DIR}"
fi

if [ -d "${REPO_COMMUTE_DIR}" ]; then
  mkdir -p "${LIVE_COMMUTE_DIR}"
  cp -R "${REPO_COMMUTE_DIR}/." "${LIVE_COMMUTE_DIR}/"
  echo "Synced commute helpers to ${LIVE_COMMUTE_DIR}"
fi
