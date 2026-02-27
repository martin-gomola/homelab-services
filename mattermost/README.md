# Mattermost + Agents

This stack runs Mattermost with the built-in Agents plugin (`mattermost-ai`).
It also includes `codex-bridge`, a local OpenAI-compatible adapter for Codex CLI.

## Why Enterprise Image

For Agents features like multiple bot configurations and MCP support, run
`mattermost-enterprise-edition`. The plugin docs state these are license-gated.
When running Enterprise Edition, an Entry license can be auto-applied.

## Start / Update

```bash
cd /path/to/homelab-services/mattermost
docker compose --env-file .env up -d --build
```

## Websocket/CORS (Mobile Reliability)

To avoid "server unreachable" on mobile while desktop/web works, keep:

```dotenv
MM_SITE_URL=https://chat.yourdomain.com
MM_WEBSOCKET_URL=wss://chat.yourdomain.com
MM_ALLOW_CORS_FROM=*
```

Reason: some mobile websocket requests use origins that do not match a strict
`https://...` allowlist, which can block `/api/v4/websocket`.

## Bootstrap Agents Config

This repo includes `configure-agents.sh` to seed plugin config in `config.json`.

It configures:
- Ollama bot via OpenAI-compatible API (`http://host.docker.internal:11434/v1`)
- Optional Codex bot (`http://codex-bridge:8092/v1`)

Run:

```bash
cd /path/to/homelab-services/mattermost
chmod +x ./configure-agents.sh
./configure-agents.sh
```

## Codex On Mattermost (No OpenAI API Key)

`codex-bridge` uses your existing Codex login token from `~/.codex/auth.json` and
exposes an OpenAI-compatible endpoint for the Agents plugin.

In `.env`, set:

```dotenv
AGENTS_ENABLE_CODEX_BOT=true
AGENTS_CODEX_PROVIDER=openaicompatible
AGENTS_CODEX_API_URL=http://codex-bridge:8092/v1
AGENTS_CODEX_API_KEY=your_local_shared_secret
AGENTS_CODEX_MODEL=gpt-5-codex
CODEX_CONFIG_DIR=/Users/<you>/.codex
CODEX_WORKSPACE_DIR=/Users/<you>/dev/homelab-services
```

Then rerun:

```bash
./configure-agents.sh
```

`AGENTS_CODEX_API_KEY` here is only a local bearer secret between Mattermost and
`codex-bridge`. It is not an OpenAI key.

## Optional OpenAI Provider Instead

If you want direct OpenAI instead of local bridge:

```dotenv
AGENTS_ENABLE_CODEX_BOT=true
AGENTS_CODEX_PROVIDER=openai
AGENTS_CODEX_API_URL=https://api.openai.com/v1
AGENTS_CODEX_API_KEY=<openai_api_key>
```
