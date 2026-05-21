# Audiobookshelf

Self-hosted audiobook and podcast server with multi-user playback sync. Reverse proxies must support WebSockets.

## Setup

```bash
cp .env.example .env
$EDITOR .env
docker compose up -d
```

Then open `http://localhost:13378` and create the admin account in the web UI.

## Access

- Web UI: `http://localhost:13378`
- Default API base URL for helper scripts: `http://localhost:13378`
- Cover images are proxied through an nginx cache layer before they hit the ABS container

## Storage Layout

- `/audiobooks` -> `${DATA_DIR}/audiobookshelf/audiobooks`
- `/ebooks` -> `${DATA_DIR}/audiobookshelf/ebooks`
- `/podcasts` -> `${DATA_DIR}/audiobookshelf/podcasts`
- `/metadata` -> `${DATA_DIR}/audiobookshelf/metadata`
- `/config` -> `${DATA_DIR}/audiobookshelf/config`
- `/var/cache/nginx/abs-covers` -> `${DATA_DIR}/audiobookshelf/nginx-cache`

If you already keep your media somewhere else, change the host-side volume paths in `docker-compose.yml`.

## Reverse Proxy

- Recommended host: `ebooks.yourdomain.com`
- Enable WebSockets in Nginx Proxy Manager or your reverse proxy of choice
- Raise the body size limit if you expect large uploads
- The local nginx sidecar caches `/api/items/:id/cover` responses and adds `X-Cache-Status` headers (`MISS`, `HIT`, etc.) for verification

## Email Bootstrap

Audiobookshelf stores SMTP settings in its own database, not as native container environment variables. This repo keeps those values in `.env` and provides `bootstrap-email-settings.sh` to push them through the API.

Run the bootstrap only after:

1. `docker compose up -d` is complete
2. the admin account already exists in the web UI
3. `ABS_BASE_URL` is reachable from the machine running the script

When those conditions are met:

```bash
./bootstrap-email-settings.sh
```
