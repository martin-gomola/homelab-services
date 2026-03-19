# Home Assistant + Zigbee2MQTT + ESPHome

Beginner-friendly smart home stack with:

- Home Assistant for automations and dashboards
- Mosquitto as the MQTT broker
- Zigbee2MQTT for Zigbee devices
- ESPHome for ESP32/ESP8266 firmware management
- SONOFF Dongle Max as the Zigbee coordinator

## What You Get

| Service | URL | Purpose |
|---------|-----|---------|
| Home Assistant | `http://localhost:8123` | Main smart home UI |
| ESPHome | `http://localhost:6052` | Build, flash, and manage ESP firmware |
| Zigbee2MQTT | `http://localhost:8099` | Pair and manage Zigbee devices |
| Mosquitto | `localhost:1883` | MQTT broker for HA and Zigbee2MQTT |

## Before You Start

You need:

- Docker and Docker Compose
- A `.env` file in this folder
- A SONOFF Dongle Max

Recommended:

- Use the dongle in `network` mode
- On macOS, use `network` mode, not USB passthrough to Docker

## Quick Start

### 1. Put the SONOFF dongle on your network

This is the easiest path and the recommended one for Docker.

1. Connect to the dongle using the SONOFF web UI
2. Join it to your Wi-Fi or Ethernet network
3. Note its IP address

Example:

```text
192.168.1.201
```

The dongle usually exposes the coordinator port on `6638`.

### 2. Create `.env`

```bash
cp .env.example .env
```

Edit `.env` and set at least these values:

```bash
TZ=Europe/Bratislava
DATA_DIR=$HOME/srv/docker

MQTT_USER=mqtt
MQTT_PASSWORD=generate_a_real_password

ZIGBEE_CONNECTION_MODE=network
SONOFF_DONGLE_IP=192.168.1.201
SONOFF_DONGLE_PORT=6638

HA_URL=https://my.home.martingomola.com
# Add the "Model Context Protocol Server" integration in the Home Assistant UI
# before using Codex or Mythosaur against /api/mcp.
HOME_ASSISTANT_ACCESS_TOKEN=replace-with-your-long-lived-access-token
```

Generate a password with:

```bash
openssl rand -base64 32
```

### 3. Start the stack

From this folder:

```bash
make up
```

What `make up` does:

1. Creates the data folders
2. Generates the MQTT password file
3. Updates Zigbee2MQTT config from `.env`
4. Starts the containers

### 4. Open the apps

- Home Assistant: `http://localhost:8123`
- Zigbee2MQTT: `http://localhost:8099`

If you are running this on another machine, replace `localhost` with that machine's IP or hostname.

### 5. Finish first-time Home Assistant setup

1. Open Home Assistant
2. Create your admin account
3. Go to `Settings -> Devices & Services`
4. Add the `MQTT` integration

Use:

- Broker: `localhost`
- Port: `1883`
- Username: value from `.env`
- Password: value from `.env`

Why `localhost`?

Home Assistant runs with host networking in this stack, so it reaches Mosquitto through the host port.

Important:

- Use the `MQTT` integration for Zigbee2MQTT devices in this stack
- Do not add `Zigbee Home Automation (ZHA)` unless you plan to stop using Zigbee2MQTT entirely
- The SONOFF dongle web UI may show its own `MQTT` page, but that is not needed for this setup

### 6. Pair your first Zigbee device

1. Open Zigbee2MQTT
2. Click `Permit join`
3. Put your Zigbee device into pairing mode
4. Wait for it to appear in Zigbee2MQTT
5. It should then appear automatically in Home Assistant through MQTT discovery

Notes:

- If a device appears in Zigbee2MQTT but not in Home Assistant, check that the `MQTT` integration is loaded
- Rename Zigbee devices in Zigbee2MQTT first if you want cleaner entity names in Home Assistant

### 7. Configure Home Assistant basics

Recommended after first boot:

1. Set Home Assistant units to `metric` if you want temperatures in `°C`
2. Create Home Assistant `areas` that match your flat, for example:
   - `Living Room`
   - `Kitchen`
   - `Bedroom`
   - `Bathroom`
3. Assign devices to areas so dashboards and floorplans are easier to build

### 8. Configure Wi-Fi devices

Wi-Fi devices usually need their vendor app first before Home Assistant can use them reliably.

#### Tuya / Smart Life devices

Examples:

- smart plugs
- smart switches
- some humidifiers

Recommended flow:

1. Pair the device in the `Smart Life` app
2. Confirm it works on your Wi-Fi
3. Add the `Tuya` integration in Home Assistant

#### Yeelight devices

Examples:

- Yeelight strip
- Yeelight bulbs

Recommended flow:

1. Pair the device in the `Yeelight` app
2. Enable `LAN control`
3. Add the `Yeelight` integration in Home Assistant

Do not pair Yeelight devices in `Smart Life` unless the device specifically requires it.

#### Xiaomi / Mi Home devices

Recommended flow:

1. Pair the device in the `Xiaomi Home` / `Mi Home` app
2. Install the `xiaomi_home` custom integration in Home Assistant
3. Sign in with the same Xiaomi account and choose the matching cloud region

Notes:

- For Slovakia, use region `de` in the Xiaomi Home integration
- The Xiaomi Home OAuth redirect must use your real Home Assistant URL, for example `https://my.home.martingomola.com`
- `homeassistant.local` is often wrong in reverse-proxy setups and will break the Xiaomi callback flow

If the device is actually Yeelight-branded, use the `Yeelight` app instead.

### 9. TV integration

Samsung TVs are often auto-discovered by Home Assistant through the built-in `samsungtv` integration.

If your TV appears automatically:

- keep the discovered integration
- use `media_player` and `remote` entities for useful dashboard controls
- common source shortcuts are `TV`, `HDMI`, `Apple TV`, `Netflix`, `YouTube`, and `Spotify`

### 10. Dashboards

Good next dashboards to create:

- a simple `TV` dashboard with media controls and source buttons
- a `Plant Sensor` dashboard for humidity, soil moisture, fertility, and battery
- a floorplan dashboard using an image in `/config/www/`

For a floorplan image, place it in:

```text

## Tracked Home Assistant Overlays

This repo can track small, intentional Home Assistant config overlays without committing the whole live `/config` directory.

Tracked today:

- `configuration.yaml`
- `command_line.yaml`
- `commute/`
- `dashboards/`
- `themes/`
- `templates/`
- `custom_components/tuya_local/devices/`

Sync helpers:

```bash
make update
make config-install
make dashboard-install
make tuya-local-install
```

`make update` is the short everyday command for syncing tracked config and dashboard overlays into the live Home Assistant config.

Important:

- Home Assistant config is mounted from `${DATA_DIR}/homeassistant/config:/config`
- it is not baked into the Docker image during build
- so persistent UI and config changes should live in this repo and then be synced into the mounted config directory

Current note:

- the built-in `Energy` dashboard is intentionally excluded from `configuration.yaml` until power-measuring outlets are added
- CP.sk commute routes are configured in `commute/routes.json`, including direct-only and MHD transport filters
/config/www/floorplan.png
```

Then reference it in Lovelace as:

```text
/local/floorplan.png
```

## Common Commands

Run these from this folder:

```bash
make up        # Configure and start everything
make down      # Stop everything
make restart   # Restart containers
make logs      # Follow logs
make ps        # Show container status
make setup     # Regenerate runtime config from .env
make codex-mcp-install   # Register Home Assistant MCP in local Codex
```

Manual equivalent of `make up`:

```bash
./setup.sh
docker compose up -d
```

## Codex MCP

If you want Codex CLI to manage Home Assistant through MCP, install the server into your
machine-local Codex config from this folder:

```bash
make codex-mcp-install
```

Before running that command, add the `Model Context Protocol Server` integration in the
Home Assistant UI. The Docker setup in this repo starts Home Assistant, but it does not
provision UI-managed integrations automatically.

What this does:

1. Reads `HA_URL` from `.env`
2. Reads `HOME_ASSISTANT_ACCESS_TOKEN` from your local `.env`
3. Derives the MCP endpoint as `HA_URL + /api/mcp`
4. Registers a local `home_assistant` MCP server in `~/.codex/config.toml`
5. Syncs the token into Codex's `shell_environment_policy.set`, so you do not need to export it manually each time

After that, `codex mcp get home_assistant` should show the registered server.

## If You Change `.env` Later

After changing:

- `SONOFF_DONGLE_IP`
- `MQTT_PASSWORD`
- `HA_URL`
- ports

run:

```bash
make up
```

That will re-apply the generated runtime config and restart the stack.

## macOS Notes

If you are running Docker on macOS:

- prefer `ZIGBEE_CONNECTION_MODE=network`
- do not rely on USB passthrough to the container

The dongle can still be connected to your Mac by USB for initial setup, firmware, or web access, while Zigbee2MQTT talks to it over the network.

## USB Mode

Use USB mode only if your Docker host can pass serial devices into containers reliably, such as a Linux machine.

In `.env`:

```bash
ZIGBEE_CONNECTION_MODE=usb
ZIGBEE_DEVICE=/dev/ttyACM0
```

Then update `docker-compose.yml` to uncomment the `devices:` mapping for `zigbee2mqtt`.

## ESPHome

ESPHome lets you create and manage firmware for ESP32/ESP8266 devices from a web dashboard. You write YAML configs, ESPHome compiles them into firmware, and flashes the devices over Wi-Fi (OTA) or USB.

### Getting started

1. Open ESPHome at `http://localhost:6052`
2. Click `NEW DEVICE`
3. Give it a name and choose your board type (e.g. `esp32dev`, `esp8266`)
4. ESPHome generates a YAML config you can edit
5. Click `INSTALL` to compile and flash over USB (first time) or OTA (after first flash)

### First flash

The very first flash of a new device must be done over USB or by downloading the compiled binary and flashing it manually (e.g. with ESPHome Web at `web.esphome.io`).

After the first flash, ESPHome can update the device over Wi-Fi (OTA).

### Home Assistant integration

After flashing, the device is auto-discovered by Home Assistant through the `ESPHome` integration. Accept the discovery notification in Home Assistant to add the device.

### GeekMagic displays

For GeekMagic SmallTV devices (ESP8266/ESP32-based), you have two options:

1. **Stock firmware + HACS integration**: Use the [geekmagic-hacs](https://github.com/adrienbrault/geekmagic-hacs) custom integration. It renders dashboards server-side and pushes images to the device over HTTP. No flashing needed.

2. **ESPHome firmware**: Flash ESPHome firmware for full local control. This gives you direct sensor/display integration but requires a compatible device and initial USB flash.

The stock firmware approach is simpler and works without flashing. Use ESPHome when you want full local control or custom sensor integration.

### Config storage

ESPHome configs are stored in:

```text
${DATA_DIR}/homeassistant/esphome/
```

### Proxy setup

If you want remote access to the ESPHome dashboard:

```text
esphome.domain.com -> server:6052
```

## Troubleshooting

### Check container status

```bash
make ps
```

### Follow logs

```bash
make logs
docker compose logs -f zigbee2mqtt
docker compose logs -f homeassistant
docker compose logs -f mosquitto
docker compose logs -f esphome
```

### Check the SONOFF network port

```bash
nc -zv 192.168.1.201 6638
```

If it succeeds, Zigbee2MQTT should be able to reach the coordinator.

### Zigbee2MQTT does not connect

Check:

- `SONOFF_DONGLE_IP` is correct
- port `6638` is reachable
- the dongle is still in Zigbee Coordinator mode

### Home Assistant cannot connect to MQTT

Use:

- broker `localhost`
- port `1883`

Do not use `mosquitto` as the broker hostname inside Home Assistant for this stack.

### ZHA shows `Could not form a new Zigbee network`

This usually means ZHA is trying to grab the coordinator while Zigbee2MQTT is already using it.

For this stack:

- keep Zigbee2MQTT
- keep the `MQTT` integration
- do not configure `ZHA`

## Optional Device Integrations

### Tuya Wi-Fi switches

Simplest path:

1. In Home Assistant, add the `Tuya` integration
2. Sign in with your Tuya or Smart Life account

Local-only path:

1. Run `make tuya-local-install`
2. Restart Home Assistant if it is already running
3. Add `Tuya Local` in Home Assistant
4. Add each device using cloud-assisted setup or its IP and local key

For this repo, custom `Tuya Local` device overlays that we maintain should be
checked into git under:

```text
homeassistant/custom_components/tuya_local/devices/
```

The installer copies those overlays into the live Home Assistant config under
`/config/custom_components/tuya_local/devices/`.

### Xiaomi light strip

Try built-in discovery first. If it does not show up:

1. Enable LAN control in the vendor app
2. Add `Yeelight` or `Xiaomi Miio` in Home Assistant

### Xiaomi Home custom integration

The newer Xiaomi Home account-based integration is not built into the base Home Assistant container in this stack. Install it as a custom component under:

```text
/config/custom_components/xiaomi_home
```

Important:

- use your public HA URL for the OAuth redirect, not `http://homeassistant.local:8123`
- for this setup, `https://my.home.martingomola.com` is the correct redirect base URL
- after installing or updating the custom component, restart Home Assistant before adding the integration

## Tuya Soil Sensor Data

Typical entities from the Tuya Zigbee soil sensor:

| Entity | Unit |
|--------|------|
| `soil_moisture` | `%` |
| `temperature` | `degC` |
| `humidity` | `%` |
| `illuminance_lux` | `lx` |
| `soil_ec` | `uS/cm` |
| `battery` | `%` |

## Example Automation

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
```

## MCP Server

If you want AI tools such as Cursor to control Home Assistant:

1. In Home Assistant, add the `Model Context Protocol Server` integration
2. Create a long-lived access token in your profile
3. Point your MCP client to:

```text
https://your-ha-url/api/mcp
```

Use the `HA_URL` value from your `.env`.

This integration is configured inside Home Assistant after the container is running. It
is not enabled automatically by the Docker Compose files in this repo.

## Proxy Setup

Example reverse proxy targets:

- `my.home.martingomola.com -> server:8123`
- `esphome.domain.com -> server:6052`
- `zigbee.domain.com -> server:8099`

Enable WebSockets for Home Assistant and ESPHome if your proxy requires that setting.
