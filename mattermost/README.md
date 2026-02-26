# Mattermost + Agents

This stack runs Mattermost with the built-in Agents plugin (`mattermost-ai`).

## Why Enterprise Image

For Agents features like multiple bot configurations and MCP support, run
`mattermost-enterprise-edition`. The plugin docs state these are license-gated.
When running Enterprise Edition, an Entry license can be auto-applied.

## Start / Update

```bash
cd /Users/mgomola/dev/homelab-services/mattermost
docker compose --env-file .env up -d
```

## Bootstrap Agents Config

This repo includes `configure-agents.sh` to seed plugin config in `config.json`.

It configures:
- Ollama bot via OpenAI-compatible API (`http://host.docker.internal:11434/v1`)
- Optional Codex bot (OpenAI or OpenAI-compatible endpoint)

Run:

```bash
cd /Users/mgomola/dev/homelab-services/mattermost
chmod +x ./configure-agents.sh
./configure-agents.sh
```

## Codex Note

`codex-gateway` from this homelab exposes `/delegate` only. It is not an
OpenAI-compatible chat-completions endpoint, so it cannot be used directly as an
Agents "Service".

To use a Codex bot in Agents, use:
- OpenAI provider (`gpt-5-codex`) with `AGENTS_CODEX_API_KEY`, or
- another OpenAI-compatible endpoint.

## Optional Codex Bot

In `.env`, set:

```dotenv
AGENTS_ENABLE_CODEX_BOT=true
AGENTS_CODEX_PROVIDER=openai
AGENTS_CODEX_API_URL=https://api.openai.com/v1
AGENTS_CODEX_API_KEY=your_openai_key
AGENTS_CODEX_MODEL=gpt-5-codex
```

Then rerun:

```bash
./configure-agents.sh
```
