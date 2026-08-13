# Protected Tours

Private chaptered walking-tour player for `tours.martingomola.com`.

The container serves only the reusable application shell. Tour media and
manifests live outside Git under `${DATA_DIR}/tours` and are mounted read-only.
The public hostname must be protected by Cloudflare Access before it is shared.

## Data layout

```text
${DATA_DIR}/tours/
├── tours.json
└── bratislava-old-town/
    ├── episode.mp3
    ├── cover.jpg
    └── route.html
```

## Deploy

```bash
cp .env.example .env
docker compose up -d
curl -fsS http://127.0.0.1:4180/healthz
```

Nginx Proxy Manager forwards `tours.martingomola.com` to the mac-mini on port
4180. Cloudflare Access owns authentication; the app never receives or stores
identity credentials.
