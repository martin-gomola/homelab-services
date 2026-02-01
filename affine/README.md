# Affine

Self-hosted collaborative documentation platform.

## Quick Start

```bash
cp .env.example .env
nano .env  # Configure your settings
docker compose up -d
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `AFFINE_PORT` | Web UI port | 3010 |
| `AFFINE_REVISION` | Docker image version | 0.25.7 |
| `DB_USERNAME` | PostgreSQL username | affine |
| `DB_PASSWORD` | PostgreSQL password | - |
| `DB_DATABASE` | PostgreSQL database | affinedb |
| `MAILER_SENDER` | Email sender address | - |
| `SMTP_RELAY_HOST` | External SMTP host | smtp.gmail.com |
| `SMTP_RELAY_PORT` | External SMTP port | 587 |
| `MAILER_USER` | SMTP username | - |
| `MAILER_PASSWORD` | SMTP app password | - |
| `MAIL_DOMAIN` | Allowed sender domain | - |

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
- Affine connects to the relay (internal Docker network)
- `MAILER_IGNORE_TLS=true` ignores the relay's self-signed certificate
- The relay forwards to Gmail/your mail provider with proper SSL/STARTTLS

The Affine config file at `/srv/docker/affine/config/.env` should contain:
```
MAILER_HOST=smtp_relay
MAILER_PORT=587
MAILER_USER=
MAILER_PASSWORD=
MAILER_SENDER=your-email@example.com
MAILER_IGNORE_TLS=true
```

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
0 3 * * * /home/matie/homelab-services/affine/backup-db.sh >> /srv/backups/affine/backup.log 2>&1
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
