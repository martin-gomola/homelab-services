# Umami

Lightweight, privacy-focused web analytics. PostgreSQL only, no ClickHouse. ~512MB RAM.

## Setup

```bash
cp .env.example .env
# Set UMAMI_APP_SECRET: openssl rand -base64 32 | tr -d '\n'; echo
nano .env
docker compose up -d
```

## Access

http://localhost:3025 — Default login: `admin` / `umami`

## Add to your site

```html
<script async src="https://your-umami-domain.com/script.js" data-website-id="YOUR_WEBSITE_ID"></script>
```

Get the script URL and website ID from Umami dashboard after adding a website.
