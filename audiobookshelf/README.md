# Audiobookshelf

Self-hosted audiobook and podcast server with multi-user playback sync. Requires WebSockets behind the reverse proxy.

## Setup

```bash
cp .env.example .env
nano .env
docker compose up -d
```

## Access

- Web UI: `http://localhost:13378`
- First run: open the web UI and create the admin account

## Storage Layout

- `/audiobooks` -> `${DATA_DIR}/audiobookshelf/audiobooks`
- `/podcasts` -> `${DATA_DIR}/audiobookshelf/podcasts`
- `/metadata` -> `${DATA_DIR}/audiobookshelf/metadata`
- `/config` -> `${DATA_DIR}/audiobookshelf/config`

If you already keep your media somewhere else, change the host-side volume paths in `docker-compose.yml`.

## Reverse Proxy

- Recommended host: `books.yourdomain.com`
- Enable WebSockets in Nginx Proxy Manager
- If you publish large uploads, raise the proxy body size limit

The upstream project explicitly documents WebSocket support as required for reverse proxies.
