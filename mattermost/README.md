# Mattermost + Agents + Optional Codex Bridge

This stack runs Mattermost with the `mattermost-ai` plugin and optional local
`codex-bridge` (OpenAI-compatible API backed by Codex CLI).

## Who This Is For

- Self-hosters running Mattermost behind a reverse proxy (for example Cloudflare or Nginx).
- Teams that want built-in Agents bots (Ollama, Codex, or OpenAI-compatible endpoints).
- Users who want reproducible Docker Compose deployment with minimal manual config.

## Who This Is Not For

- Single binary/manual Mattermost installs outside Docker Compose.
- Deployments that do not need Agents or external LLM integrations.
- Environments where wildcard CORS (`MM_ALLOW_CORS_FROM=*`) is not acceptable.

## Architecture

- `mattermost`: Mattermost server (`mattermost-enterprise-edition`).
- `mattermost_postgres`: PostgreSQL backend.
- `codex-bridge` (optional runtime use): local OpenAI-compatible endpoint for Codex CLI auth.
- `configure-agents.sh`: writes `mattermost-ai` plugin config into `config.json`.

## Quickstart

1. Create env file and edit required values.

```bash
cd /path/to/homelab-services/mattermost
cp .env.example .env
```

2. In `.env`, set at least:

```dotenv
MM_SITE_URL=https://chat.yourdomain.com
MM_WEBSOCKET_URL=wss://chat.yourdomain.com
MM_ALLOW_CORS_FROM=*
MM_DB_PASSWORD=replace-with-strong-password
```

3. Start services.

```bash
docker compose --env-file .env up -d --build
```

4. Apply Agents plugin config.

```bash
chmod +x ./configure-agents.sh
./configure-agents.sh
```

## Configure Bots

By default, `.env.example` enables an Ollama-compatible bot and leaves Codex disabled.

To enable Codex via local bridge:

```dotenv
AGENTS_ENABLE_CODEX_BOT=true
AGENTS_CODEX_PROVIDER=openaicompatible
AGENTS_CODEX_API_URL=http://codex-bridge:8092/v1
AGENTS_CODEX_API_KEY=your_local_shared_secret
AGENTS_CODEX_MODEL=gpt-5-codex
CODEX_CONFIG_DIR=/path/to/codex-config
CODEX_WORKSPACE_DIR=/path/to/workspace
```

Then rerun:

```bash
./configure-agents.sh
```

To use OpenAI directly instead of local bridge:

```dotenv
AGENTS_ENABLE_CODEX_BOT=true
AGENTS_CODEX_PROVIDER=openai
AGENTS_CODEX_API_URL=https://api.openai.com/v1
AGENTS_CODEX_API_KEY=<openai_api_key>
```

## Operations

Start/update:

```bash
docker compose --env-file .env up -d --build
```

Logs:

```bash
docker compose --env-file .env logs -f mattermost
```

Restart Mattermost only:

```bash
docker compose --env-file .env up -d mattermost
```

## Troubleshooting

### Mobile app says "server unreachable" but login works

Symptom:
- You can authenticate, but server list shows unreachable or realtime updates fail.

Cause:
- `/api/v4/websocket` blocked by CORS/origin checks.

Fix:

```dotenv
MM_SITE_URL=https://chat.yourdomain.com
MM_WEBSOCKET_URL=wss://chat.yourdomain.com
MM_ALLOW_CORS_FROM=*
```

Then restart Mattermost:

```bash
docker compose --env-file .env up -d mattermost
```

### Bot replies in thread only appear after reopening thread

Cause:
- Realtime websocket connection is failing, so client falls back to polling/reload behavior.

Fix:
- Apply the same websocket/CORS settings above.
- Confirm reverse proxy allows websocket upgrade for `/api/v4/websocket`.
