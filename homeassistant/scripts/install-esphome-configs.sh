#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ESPHOME_DIR="${PROJECT_DIR}/esphome"
ESPHOME_API="http://192.168.1.200:6052"

if [ ! -d "${REPO_ESPHOME_DIR}" ]; then
  echo "No esphome/ directory found in ${PROJECT_DIR}"
  exit 1
fi

if ! curl -sf "${ESPHOME_API}/devices" > /dev/null 2>&1; then
  echo "ESPHome Dashboard not reachable at ${ESPHOME_API}"
  echo "Make sure the ESPHome container is running."
  exit 1
fi

SECRETS_FILE="${REPO_ESPHOME_DIR}/secrets.yaml"
if [ ! -f "${SECRETS_FILE}" ]; then
  echo "Missing ${SECRETS_FILE}"
  echo "Copy secrets.yaml.example to secrets.yaml and fill in your values."
  exit 1
fi

curl -sf -X POST "${ESPHOME_API}/edit?configuration=secrets.yaml" \
  -H "Content-Type: application/yaml" \
  --data-binary "@${SECRETS_FILE}"
echo "Synced secrets.yaml to ESPHome Dashboard"

for config in "${REPO_ESPHOME_DIR}"/*.yaml; do
  filename="$(basename "${config}")"
  [ "${filename}" = "secrets.yaml" ] && continue
  [ "${filename}" = "secrets.yaml.example" ] && continue

  curl -sf -X POST "${ESPHOME_API}/edit?configuration=${filename}" \
    -H "Content-Type: application/yaml" \
    --data-binary "@${config}"
  echo "Synced ${filename} to ESPHome Dashboard"
done
