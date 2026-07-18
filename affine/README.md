# Affine

Self-hosted collaborative documentation platform.

## Quick Start

```bash
cp .env.example .env
nano .env  # infra settings (DB, ports, SMTP relay creds)

# AFFiNE 0.27+ mailer config lives in config.json, not .env
mkdir -p "${DATA_DIR:-/srv/docker}/affine/config"
cp config.json.example "${DATA_DIR:-/srv/docker}/affine/config/config.json"
nano "${DATA_DIR:-/srv/docker}/affine/config/config.json"  # set sender address

docker compose up -d
```

## Configuration

Config is split across two files:

**`.env`** — infrastructure and SMTP relay creds (Postfix container).

| Variable | Description | Default |
|----------|-------------|---------|
| `AFFINE_PORT` | Web UI port | 3010 |
| `AFFINE_REVISION` | Docker image version | 0.27.0 |
| `DB_USERNAME` | PostgreSQL username | affine |
| `DB_PASSWORD` | PostgreSQL password | - |
| `DB_DATABASE` | PostgreSQL database | affinedb |
| `SMTP_RELAY_HOST` | Upstream SMTP host (Gmail, Fastmail, etc.) | smtp.gmail.com |
| `SMTP_RELAY_PORT` | Upstream SMTP port | 587 |
| `MAILER_USER` | Upstream SMTP username | - |
| `MAILER_PASSWORD` | Upstream SMTP app password | - |
| `MAIL_DOMAIN` | Allowed sender domain for the relay | - |

**`config.json`** (mounted at `/root/.affine/config/config.json`) — AFFiNE application config. Since 0.27, upstream dropped the `MAILER_*` env vars; mailer settings must go here. Template: `config.json.example`. Schema: `https://github.com/toeverything/affine/releases/latest/download/config.schema.json`.

## Known Issues

### SMTP Bug (v0.25.x)

**Issue:** Affine 0.25.x has a bug where SMTP connections fail with "Connection closed unexpectedly" error. The root cause is that Affine's nodemailer implementation doesn't properly configure TLS for secure SMTP connections.

**Affected versions:** 0.25.5, 0.25.7 (and likely other 0.25.x versions)

**GitHub Issue:** [#14192](https://github.com/toeverything/AFFiNE/issues/14192)

**Symptoms:**
```
[ERROR] [MailSender] Failed to send mail [VerifyEmail].
Error: Connection closed unexpectedly
    at SMTPConnection._onClose
    at SMTPConnection._onSocketClose
```

**Workaround (implemented in this repo):**

This stack includes a local SMTP relay (`boky/postfix`) that handles TLS correctly:
- AFFiNE connects to the relay over the internal Docker network
- `ignoreTLS: true` in `config.json` skips the relay's self-signed certificate
- The relay forwards to Gmail (or your provider) with proper SSL/STARTTLS

The `mailer.SMTP` block in `${DATA_DIR}/affine/config/config.json` should look like:

```json
{
  "mailer": {
    "SMTP": {
      "host": "smtp_relay",
      "port": 587,
      "username": "",
      "password": "",
      "sender": "AFFiNE <your-email@example.com>",
      "ignoreTLS": true
    }
  }
}
```

The upstream provider credentials (`MAILER_USER` / `MAILER_PASSWORD`) stay in `.env` — those are consumed by the Postfix relay, not by AFFiNE.

**Alternative workaround (manual user management):**
1. Go to `https://your-domain/admin/accounts` with admin account
2. Add users manually
3. Use "Reset Password" → generates a shareable link
4. Users can accept workspace invites via in-app notifications (no email needed)

**Manually verify user emails (database hack):**
```bash
# Check current verification status
docker exec affine_postgres psql -U affine -d affinedb -c \
  "SELECT name, email, email_verified FROM users;"

# Set a specific user's email as verified
docker exec affine_postgres psql -U affine -d affinedb -c \
  "UPDATE users SET email_verified = NOW() WHERE email = 'user@example.com';"

# Verify all unverified users at once
docker exec affine_postgres psql -U affine -d affinedb -c \
  "UPDATE users SET email_verified = NOW() WHERE email_verified IS NULL;"
```

## Data Locations

| Data | Path |
|------|------|
| Config | `/srv/docker/affine/config` |
| Storage | `/srv/docker/affine/storage` |
| PostgreSQL | `/srv/docker/affine/postgres` |
| Redis | `/srv/docker/affine/redis` |
| Backups | `/srv/backups/affine/postgres` |

## Backup & Restore

**Automated backup (cron):**
```bash
# Add to crontab - daily at 3 AM
0 3 * * * /path/to/homelab-services/affine/backup-db.sh >> /srv/backups/affine/backup.log 2>&1
```

**Manual backup/restore:**
```bash
# Backup database
./backup-db.sh

# Restore database
./restore-db.sh /srv/backups/affine/postgres/backup_file.sql
```

**Retention:** 30 days (configured in `backup-db.sh`)

## Proxy Setup

Configure in Nginx Proxy Manager:
1. Forward `docs.domain.com` → `server-ip:3010`
2. Enable SSL
3. **Enable WebSockets** (required for real-time collaboration)
