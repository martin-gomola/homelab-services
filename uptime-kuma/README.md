# Uptime Kuma

Self-hosted monitoring tool for tracking service availability.

## Access

- **Web UI**: `http://<YOUR_SERVER_IP>:3006`

## First Setup

1. Open web UI
2. Create admin account
3. Add monitors for your services

## Recommended Monitors

| Service | Type | URL/Host |
|---------|------|----------|
| NPM | HTTP | `http://localhost:81` |
| AdGuard | HTTP | `http://localhost:3001` |
| Website | HTTP | `https://yourdomain.com` |
| DNS | DNS | Query `google.com` via `localhost:53` |

## Features

- Service uptime monitoring
- Response time tracking
- Notifications (Email, Telegram, Discord, etc.)
- Status pages
- Docker container monitoring

## Notifications Setup

Uptime Kuma supports many notification channels:
- Email (SMTP)
- Telegram
- Discord
- Slack
- Pushover
- And many more...

Configure in Settings → Notifications.
