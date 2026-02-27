# Open WebUI + Codex Gateway

Open WebUI stack for local/self-hosted AI, designed to run cleanly alongside the Mattermost stack in this repo.

## Who This Is For

- Self-hosters running Open WebUI behind a reverse proxy.
- Teams that want Open WebUI + optional external tools (Context7, Codex Gateway).
- Users deploying both `mattermost/` and `open-webui/` as one package.

## Who This Is Not For

- Users who only need a local throwaway Open WebUI test.
- Environments that cannot run Docker Compose profiles.

## Package Compatibility With Mattermost

When running both stacks, keep these values aligned in both `.env` files:

- `CODEX_CONFIG_DIR`
- `CODEX_WORKSPACE_DIR`
- `CODEX_DEFAULT_REASONING_EFFORT`
- `CODEX_DISABLE_CONTEXT7`
- `CODEX_TIMEOUT_SECONDS`
- `CODEX_MAX_TIMEOUT_SECONDS`

Recommended public domains:

- Mattermost: `https://chat.yourdomain.com`
- Open WebUI: `https://ai.yourdomain.com`

## Quickstart

1. Prepare env.

```bash
cd /path/to/homelab-services/open-webui
cp .env.example .env
```

2. Edit `.env` and set required values.

```dotenv
WEBUI_URL=https://ai.yourdomain.com
CORS_ALLOW_ORIGIN=https://ai.yourdomain.com;http://localhost:3040
ENABLE_WEBSOCKET_SUPPORT=true
WEBUI_SECRET_KEY=<64_hex_chars>
CODEX_GATEWAY_API_KEY=<strong_local_secret>
CODEX_CONFIG_DIR=/path/to/codex-config
CODEX_WORKSPACE_DIR=/path/to/workspace
```

3. Start Open WebUI core.

```bash
docker compose --env-file .env up -d --build
```

4. Optional: start external tool profiles.

```bash
docker compose --env-file .env --profile mcpo --profile codex up -d --build
```

5. Optional: upsert tool servers in Open WebUI.

```bash
./scripts/sync-tool-servers.py --email "<admin_email>"
```

## Deploy Together With Mattermost

From repo root:

```bash
cd /path/to/homelab-services/mattermost
docker compose --env-file .env up -d --build
./configure-agents.sh

cd /path/to/homelab-services/open-webui
docker compose --env-file .env --profile codex up -d --build
```

This gives you:

- Mattermost Agents chat UI at `chat.*`
- Open WebUI chat UI at `ai.*`
- Codex-backed tooling in both stacks, each with its own gateway service

## Open WebUI URLs

- Local: `http://localhost:3040`
- Public: `https://ai.yourdomain.com`

## Open WebUI Admin Configuration

### Connections

- Set Ollama endpoint to `http://host.docker.internal:11434`.

### External Tools

- Codex Gateway (OpenAPI): `http://codex-gateway:8091/openapi.json` with bearer key `CODEX_GATEWAY_API_KEY`.
- Context7 via mcpo (OpenAPI): `http://mcpo-context7:8000/openapi.json` with bearer key `MCPO_CONTEXT7_API_KEY`.
- Context7 direct MCP: `https://mcp.context7.com/mcp` (if you prefer direct MCP).

## Operations

Start/update:

```bash
docker compose --env-file .env up -d --build
```

Restart only Open WebUI app:

```bash
docker compose --env-file .env up -d open-webui
```

Logs:

```bash
docker compose --env-file .env logs -f open-webui
```

## Troubleshooting

### Chat streaming fails with JSON parse errors

Symptom:
- `Unexpected token 'd', "data:..." is not valid JSON`.

Fix:
- Ensure proxy websocket upgrade is enabled.
- Keep `ENABLE_WEBSOCKET_SUPPORT=true`.

### Tools configured in admin but not visible in chat

Fix:
- Recheck tool visibility/permissions in Open WebUI roles.
- Re-run `./scripts/sync-tool-servers.py --email "<admin_email>"`.

### Codex Gateway starts but tool calls fail

Fix:
- Verify `CODEX_GATEWAY_API_KEY` matches Open WebUI external tool bearer key.
- Verify `CODEX_CONFIG_DIR` contains valid Codex auth files.
- Verify `CODEX_WORKSPACE_DIR` exists and is readable by Docker.

## Optional MCP Bridge

If you need Open WebUI MCP server for external MCP clients:

```bash
./scripts/run-openwebui-mcp.sh
```

Default endpoint: `http://127.0.0.1:8001/mcp`.
