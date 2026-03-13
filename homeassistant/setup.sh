#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/.env"

DATA_DIR="${DATA_DIR:-/srv/docker}"
HA_DIR="${DATA_DIR}/homeassistant"

echo "=== Home Assistant + Zigbee2MQTT Setup ==="
echo ""

# Create data directories
echo "[1/4] Creating data directories..."
mkdir -p "${HA_DIR}/config"
mkdir -p "${HA_DIR}/media"
mkdir -p "${HA_DIR}/mosquitto/config"
mkdir -p "${HA_DIR}/mosquitto/data"
mkdir -p "${HA_DIR}/mosquitto/log"
mkdir -p "${HA_DIR}/zigbee2mqtt"
echo "  -> ${HA_DIR}/"

# Copy Mosquitto config
echo "[2/4] Configuring Mosquitto..."
cp "${SCRIPT_DIR}/mosquitto/mosquitto.conf" "${HA_DIR}/mosquitto/config/mosquitto.conf"

# Create Mosquitto password file
echo "[3/4] Creating MQTT credentials..."
MQTT_USER="${MQTT_USER:-mqtt}"
MQTT_PASSWORD="${MQTT_PASSWORD:?MQTT_PASSWORD must be set in .env}"

TEMP_PASSWD=$(mktemp)
echo "${MQTT_USER}:${MQTT_PASSWORD}" > "${TEMP_PASSWD}"
docker run --rm -v "${TEMP_PASSWD}:/tmp/passwd" eclipse-mosquitto:2 \
  mosquitto_passwd -U /tmp/passwd
cp "${TEMP_PASSWD}" "${HA_DIR}/mosquitto/config/password.txt"
rm -f "${TEMP_PASSWD}"
echo "  -> MQTT user '${MQTT_USER}' configured"

# Copy Zigbee2MQTT config
echo "[4/4] Configuring Zigbee2MQTT..."
if [ ! -f "${HA_DIR}/zigbee2mqtt/configuration.yaml" ]; then
  cp "${SCRIPT_DIR}/zigbee2mqtt/configuration.yaml" "${HA_DIR}/zigbee2mqtt/configuration.yaml"

  # Update adapter IP if using network mode
  if [ "${ZIGBEE_CONNECTION_MODE:-network}" = "network" ]; then
    DONGLE_IP="${SONOFF_DONGLE_IP:?SONOFF_DONGLE_IP must be set in .env for network mode}"
    DONGLE_PORT="${SONOFF_DONGLE_PORT:-6638}"
    sed -i.bak "s|tcp://192.168.1.100:6638|tcp://${DONGLE_IP}:${DONGLE_PORT}|" \
      "${HA_DIR}/zigbee2mqtt/configuration.yaml"
    rm -f "${HA_DIR}/zigbee2mqtt/configuration.yaml.bak"
    echo "  -> Network mode: tcp://${DONGLE_IP}:${DONGLE_PORT}"
  else
    echo "  -> USB mode: ${ZIGBEE_DEVICE:-/dev/ttyACM0}"
    echo "  NOTE: Uncomment 'devices' in docker-compose.yml and switch serial config"
  fi
else
  echo "  -> configuration.yaml already exists, skipping"
fi

# Write Z2M secrets
cat > "${HA_DIR}/zigbee2mqtt/secret.yaml" <<SECRETS
mqtt_user: ${MQTT_USER}
mqtt_password: ${MQTT_PASSWORD}
SECRETS
echo "  -> Zigbee2MQTT secrets written"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Review configs in ${HA_DIR}/"
echo "  2. Run: cd ${SCRIPT_DIR} && docker compose up -d"
echo "  3. Open Home Assistant: http://your-server:${HA_PORT:-8123}"
echo "  4. Open Zigbee2MQTT UI: http://your-server:${Z2M_PORT:-8099}"
echo "  5. In HA, add MQTT integration (Settings > Integrations > MQTT)"
echo "     - Broker: mosquitto"
echo "     - Port: 1883"
echo "     - User/Pass: from your .env"
echo ""
