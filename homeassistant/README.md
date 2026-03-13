# Home Assistant + Zigbee2MQTT

Smart home automation stack for Zigbee and Wi-Fi devices.

## Architecture

```
Zigbee Devices ─── SONOFF Dongle Max ─── Zigbee2MQTT ─── Mosquitto (MQTT) ─── Home Assistant
  (sensors)         (coordinator)          :8099            :1883           │     :8123
                                                                           │
Wi-Fi Devices ─────────────────── Local Network (mDNS/SSDP) ──────────────┘
  (switches, lights)
```

Home Assistant runs with `network_mode: host` so it can discover Wi-Fi devices on your LAN via mDNS and SSDP.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Home Assistant | 8123 | Automation dashboard & rules (host network) |
| Zigbee2MQTT | 8099 | Zigbee device management UI |
| Mosquitto | 1883 | MQTT message broker |

## Hardware & Devices

| Device | Protocol | Integration |
|--------|----------|-------------|
| SONOFF Dongle Max (EFR32MG21) | Zigbee 3.0 | Zigbee2MQTT coordinator |
| Tuya Soil Moisture Sensor | Zigbee | Zigbee2MQTT → MQTT auto-discovery |
| Wi-Fi Light Switches | Wi-Fi | Tuya (built-in) or LocalTuya (HACS) |
| Xiaomi Light Strip | Wi-Fi | Yeelight or Xiaomi Miio (built-in) |

## Setup

### 1. Configure environment

```bash
cp .env.example .env
nano .env
```

Set your `MQTT_PASSWORD` (generate with `openssl rand -base64 32`) and configure the SONOFF Dongle connection.

### 2. SONOFF Dongle Max Connection

The dongle supports three connection modes:

#### Network Mode (Ethernet PoE / Wi-Fi) — Recommended for Docker

Set in `.env`:
```bash
ZIGBEE_CONNECTION_MODE=network
SONOFF_DONGLE_IP=192.168.1.100   # Your dongle's IP
SONOFF_DONGLE_PORT=6638
```

To find your dongle's IP:
- Check your router's DHCP client list
- Use the eWeLink/SONOFF app
- Run `nmap -sP 192.168.1.0/24` and look for the dongle

#### USB Mode

Set in `.env`:
```bash
ZIGBEE_CONNECTION_MODE=usb
ZIGBEE_DEVICE=/dev/ttyACM0
```

Find the device path:
```bash
ls -la /dev/ttyACM* /dev/ttyUSB*
# or
dmesg | grep tty
```

Then uncomment the `devices` section in `docker-compose.yml`:
```yaml
zigbee2mqtt:
  devices:
    - ${ZIGBEE_DEVICE:-/dev/ttyACM0}:/dev/ttyACM0
```

### 3. Run setup and deploy

```bash
./setup.sh
docker compose up -d
```

### 4. Initial configuration

1. **Home Assistant** — Open `http://your-server:8123`, create your account
2. **MQTT Integration** — Settings > Integrations > Add > MQTT
   - Broker: `localhost` (HA uses host networking, Mosquitto maps port 1883 to host)
   - Port: `1883`
   - Username/Password: from your `.env`
3. **Zigbee2MQTT** — Open `http://your-server:8099`
   - Verify the coordinator is connected (green status)

### 5. Pair Zigbee devices (soil moisture sensor)

1. In Zigbee2MQTT UI, click "Permit Join" (top right)
2. Put your Tuya sensor in pairing mode (hold reset button ~5 seconds until LED blinks)
3. The sensor should appear in Z2M within 60 seconds
4. It will auto-discover in Home Assistant via MQTT

### 6. Add Wi-Fi light switches (Tuya)

Two options for Tuya Wi-Fi switches — choose one:

#### Option A: Tuya Cloud Integration (easier setup)

1. Create a free account at [Tuya IoT Platform](https://iot.tuya.com/)
2. Create a Cloud Project (select your data center region)
3. Link your Tuya/Smart Life app account under "Link Tuya App Account"
4. In HA: Settings > Integrations > Add > **Tuya**
5. Enter your Tuya IoT credentials and authorize

#### Option B: LocalTuya via HACS (fully local, no cloud)

1. Install HACS in Home Assistant (see [hacs.xyz](https://hacs.xyz/))
2. In HACS: search and install **LocalTuya**
3. Get your device keys using one of:
   - Tuya IoT Platform (API Explorer → Get Device Info)
   - `tinytuya` CLI: `pip install tinytuya && python -m tinytuya wizard`
4. In HA: Settings > Integrations > Add > **LocalTuya** > enter device IP and local key

### 7. Add Xiaomi Light Strip

The Xiaomi Wi-Fi light strip should be auto-discovered. If not:

#### Yeelight Strip

1. In the Yeelight/Mi Home app, enable **LAN Control** for the strip
2. HA should auto-discover it — check Settings > Integrations
3. If not found: Settings > Integrations > Add > **Yeelight** > enter the strip's IP

#### Xiaomi Miio (Mi Smart LED Strip)

1. Get the device token using `miio` CLI or from Mi Home app logs
2. In HA: Settings > Integrations > Add > **Xiaomi Miio** > enter IP and token

#### Xiaomi Miot Auto via HACS (most comprehensive)

1. Install HACS, then search for **Xiaomi Miot Auto**
2. Add integration with your Xiaomi account credentials
3. All linked Xiaomi devices will be imported

## Sensor Data

The Tuya Zigbee Soil Moisture Sensor exposes:

| Entity | Type | Unit | Description |
|--------|------|------|-------------|
| `soil_moisture` | sensor | % | Soil moisture level |
| `temperature` | sensor | °C | Soil/ambient temperature |
| `humidity` | sensor | % | Ambient humidity |
| `illuminance_lux` | sensor | lx | Light intensity |
| `soil_ec` | sensor | µS/cm | Soil fertility (conductivity) |
| `battery` | sensor | % | Battery level |

## Garden Automation Example

After pairing, create automations in Home Assistant. Example `automations.yaml`:

```yaml
- alias: "Water garden when soil is dry"
  trigger:
    - platform: numeric_state
      entity_id: sensor.soil_moisture_sensor_soil_moisture
      below: 30
      for:
        minutes: 30
  condition:
    - condition: time
      after: "06:00:00"
      before: "20:00:00"
  action:
    - service: switch.turn_on
      target:
        entity_id: switch.garden_irrigation_valve
    - delay:
        minutes: 15
    - service: switch.turn_off
      target:
        entity_id: switch.garden_irrigation_valve
    - service: notify.notify
      data:
        title: "Garden Watered"
        message: "Soil moisture was {{ trigger.to_state.state }}%. Watered for 15 min."
```

## Troubleshooting

### Logs

```bash
docker compose logs -f                    # All services
docker compose logs -f zigbee2mqtt        # Z2M only
docker compose logs -f homeassistant      # HA only
```

### MQTT

```bash
# Verify broker is reachable
docker exec mosquitto mosquitto_sub -t 'zigbee2mqtt/#' -u mqtt -P 'your_password' -v

# Test from HA container (host network → localhost)
curl -s http://localhost:8123/api/ | head
```

### Zigbee

```bash
# Check dongle reachability (network mode)
nc -zv 192.168.1.100 6638

# Check USB device (USB mode)
ls -la /dev/ttyACM* /dev/ttyUSB*

# Restart Z2M after config changes
docker compose restart zigbee2mqtt
```

### Wi-Fi Devices

```bash
# Check if HA can see mDNS traffic (host network verification)
docker exec homeassistant ip addr show

# Ping a Wi-Fi device from the server
ping 192.168.1.xxx

# Scan for Yeelight/Xiaomi devices
nmap -sP 192.168.1.0/24 | grep -i -A1 "xiaomi\|yeelight\|tuya\|espressif"

# Check Yeelight LAN control (port 55443)
nc -zv <yeelight-ip> 55443
```

### Common Issues

| Problem | Solution |
|---------|----------|
| HA can't discover Wi-Fi devices | Verify `network_mode: host` is set; check firewall allows mDNS (port 5353 UDP) |
| MQTT connection refused in HA | Use `localhost` as broker (not `mosquitto`) since HA is on host network |
| Tuya devices unavailable | Check Tuya Cloud project is active; for LocalTuya verify local keys haven't rotated |
| Xiaomi strip not found | Enable LAN Control in Yeelight/Mi Home app; ensure same VLAN as server |

## Proxy Setup

Configure in Nginx Proxy Manager:
- `home.domain.com` → `server-ip:8123` (enable WebSockets)
- `zigbee.domain.com` → `server-ip:8099`
