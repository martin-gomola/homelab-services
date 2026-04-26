# Homelab Services

Docker Compose stacks for the self-hosted services that ride with [pi-commander](https://github.com/martin-gomola/pi-commander).

This repo runs the worker-side services in the homelab fleet. Current split:

- `pi-commander` holds the control plane on `192.168.1.190`
- `homelab-services` runs on the Mac mini worker host `192.168.1.200`
- `mythosaur-tools` runs the shared MCP gateway for AI work against Home Assistant, AdGuard, and other remote services

## Services

| Service | Port | URL Pattern | Notes |
|---------|------|-------------|-------|
| **Affine** | 3010 | docs.domain.com | Docs & knowledge base, WebSockets required |
| **Mealie** | 9925 | mealie.domain.com | Recipe manager |
| **Plausible** | 8001 | analytics.domain.com | Privacy-friendly analytics (ClickHouse + PostgreSQL) |
| **Ntfy** | 8040 | ntfy.domain.com | Push notifications |
| **Rallly** | 3030 | rallly.domain.com | Meeting poll scheduler |
| **ChangeDetection** | 5050 | monitor.domain.com | Website change monitoring (Browserless on 3020) |
| **Stirling PDF** | 8080 | pdf.domain.com | PDF toolkit (stateless) |
| **Grocy** | 9283 | grocy.domain.com | Household management |
| **Uptime Kuma** | 3006 | uptime.domain.com | Monitoring & status page |
| **Umami** | 3025 | stats.domain.com | Lightweight analytics (PostgreSQL only) |
| **Audiobookshelf** | 13378 | knihy.martingomola.com | Audiobooks & podcasts, WebSockets required |
| **Home Assistant** | 8123 | home.domain.com | Smart home automation (Zigbee2MQTT + MQTT) |
| **ESPHome** | 6052 | esphome.domain.com | ESP32/ESP8266 firmware builder & OTA manager |
| **TRIP** | 8050 | trip.domain.com | POI map tracker & trip planner (SQLite) |

## Quick Start

```bash
cd <service>
cp .env.example .env
nano .env
docker compose up -d
```

## Makefile Commands

```bash
make list                  # List available services
make deploy SERVICE=affine # Deploy service
make status                # Show running containers
make logs SERVICE=affine   # Tail logs
make update SERVICE=affine # Pull and redeploy
make stop SERVICE=affine   # Stop service
make backup SERVICE=affine # Backup service data
make clean                 # Prune Docker resources
```

## Data Storage

Each service stores its data in `${DATA_DIR}/<service>/` and falls back to `/srv/docker/<service>/`.

**macOS users:** Add to your `.env`:
```bash
DATA_DIR=$HOME/srv/docker
BACKUP_DIR=$HOME/srv/backups
```

## Proxy Setup

Set up each host in Nginx Proxy Manager through [pi-commander](https://github.com/martin-gomola/pi-commander):
1. Forward `service.domain.com` → `server-ip:port`
2. Enable SSL
3. Enable WebSockets where needed (Affine, Audiobookshelf)

## Troubleshooting

```bash
docker compose logs -f

docker ps --format "table {{.Names}}\t{{.Ports}}"

# Fix permissions (Linux)
sudo chown -R 1000:1000 /srv/docker/<service>/
```

## Related

| Repo | What it does |
|------|--------------|
| [pi-commander](https://github.com/martin-gomola/pi-commander) | Infrastructure stack: reverse proxy (NPM), DNS (AdGuard), VPN (Tailscale), DDNS (Cloudflare) |
| [mythosaur-ai](https://github.com/martin-gomola/mythosaur-ai) | Mattermost runtime: Grogu local operator bot and Mythosaur Codex-first planner |
| [mythosaur-tools](https://github.com/martin-gomola/mythosaur-tools) | Shared MCP gateway: Home Assistant, AdGuard, pi-commander, Google, browser, and fetch |
| **homelab-services** (this repo) | Self-hosted applications |

---

MIT License
