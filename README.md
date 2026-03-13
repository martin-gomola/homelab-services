# Homelab Services

Docker Compose stacks for self-hosted applications. Works with [pi-commander](https://github.com/martin-gomola/pi-commander).

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
| **Home Assistant** | 8123 | home.domain.com | Smart home automation (Zigbee2MQTT + MQTT) |

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

All data stored in `${DATA_DIR}/<service>/` (defaults to `/srv/docker/<service>/`).

**macOS users:** Add to your `.env`:
```bash
DATA_DIR=$HOME/srv/docker
BACKUP_DIR=$HOME/srv/backups
```

## Proxy Setup

Configure in Nginx Proxy Manager (via [pi-commander](https://github.com/martin-gomola/pi-commander)):
1. Forward `service.domain.com` → `server-ip:port`
2. Enable SSL
3. Enable WebSockets where needed (Affine)

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
| [pi-commander](https://github.com/martin-gomola/pi-commander) | Infrastructure — reverse proxy (NPM), DNS (AdGuard), VPN (Tailscale), DDNS (Cloudflare) |
| [mythosaur-ai](https://github.com/martin-gomola/mythosaur-ai) | AI platform — Ollama, Mattermost, Codex, Open WebUI |
| **homelab-services** (this repo) | Self-hosted applications |

---

MIT License
