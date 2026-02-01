# Homelab Services

Docker Compose stacks for self-hosted applications. Works with [pi-commander](https://github.com/martin-gomola/pi-commander).

## Port Reference

| Service | Port | URL Pattern | Notes |
|---------|------|-------------|-------|
| **Affine** | 3010 | docs.domain.com | WebSockets required |
| **Mealie** | 9925 | mealie.domain.com | |
| **Plausible** | 8001 | analytics.domain.com | ClickHouse + PostgreSQL |
| **Ntfy** | 8040 | ntfy.domain.com | |
| **Rallly** | 3030 | rallly.domain.com | |
| **ChangeDetection** | 5050 | monitor.domain.com | Browserless on 3020 |
| **Stirling PDF** | 8080 | pdf.domain.com | Stateless |
| **Grocy** | 9283 | grocy.domain.com | Default login: admin/admin |
| **Uptime Kuma** | 3006 | uptime.domain.com | Monitoring & status page |

## Quick Start

```bash
cd <service>
cp .env.example .env
nano .env
docker-compose up -d
```

## Makefile Commands

```bash
make list                  # List services
make deploy SERVICE=affine # Deploy service
make status                # Show running containers
make logs SERVICE=affine   # Tail logs
make update SERVICE=affine # Pull and redeploy
make stop SERVICE=affine   # Stop service
make backup SERVICE=affine # Backup data
make clean                 # Prune Docker
```

## Data Storage

All data stored in `/srv/docker/<service>/`

## Proxy Setup

Configure in Nginx Proxy Manager:
1. Forward `service.domain.com` → `server-ip:port`
2. Enable SSL
3. Enable WebSockets (for Affine)

## Troubleshooting

```bash
# Check logs
docker-compose logs -f

# Port conflict
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Fix permissions
sudo chown -R 1000:1000 /srv/docker/<service>/
```

---
[pi-commander](https://github.com/martin-gomola/pi-commander) | MIT License
