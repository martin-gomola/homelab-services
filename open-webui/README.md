# Open WebUI + Ollama Setup (Step by Step)

This is a copy/paste runbook for:
- Ollama local models
- Open WebUI in Docker
- Context7 tool integration
- Codex Gateway tool integration
- Open WebUI MCP server (`openwebui-mcp-server`) via `uv`

## 1. Install Prerequisites

```bash
brew install ollama uv
brew install --cask docker
```

Start Docker Desktop, then verify:

```bash
docker ps
```

## 2. Prepare Config

```bash
export REPO_DIR="$HOME/dev/homelab-services/open-webui"
cd "$REPO_DIR"
cp .env.example .env
openssl rand -hex 32
```

Put the generated key into `.env` as `WEBUI_SECRET_KEY`.

Edit `.env` and set at minimum:
- `WEBUI_URL=https://ai.home.example.com`
- `ENABLE_WEBSOCKET_SUPPORT=true`
- `WEBUI_SECRET_KEY=<your_64_hex_chars>`
- `MCPO_CONTEXT7_API_KEY=<your_context7_key>` (if using mcpo)
- `CODEX_GATEWAY_API_KEY=<your_gateway_key>` (if using Codex Gateway)
- `CODEX_CONFIG_DIR=/Users/<service-user>/.codex`
- `CODEX_WORKSPACE_DIR=/Users/<service-user>/dev/homelab-services`

## 3. Start Ollama First, Pull Models Second

Terminal 1:

```bash
ollama serve
```

Terminal 2:

```bash
ollama pull ministral-3:8b
ollama pull qwen2.5-coder:7b
ollama list
```

## 4. Start Open WebUI Stack

Core service:

```bash
cd "$REPO_DIR"
docker compose up -d
```

Optional tool services (`mcpo` + `codex-gateway`):

```bash
cd "$REPO_DIR"
docker compose --profile mcpo --profile codex up -d --build
```

Verify containers:

```bash
docker ps
```

## 5. Open WebUI URLs

- Local: `http://localhost:3040`
- Domain (example): `https://ai.home.example.com`

If using reverse proxy, enable websocket upgrade.  
Without websocket support, chat may fail with:
`Unexpected token 'd', "data:..." is not valid JSON`.

## 6. Configure Open WebUI (Admin UI)

### 6.1 Connections
1. Go to `Settings -> Connections`.
2. Confirm Ollama endpoint is `http://host.docker.internal:11434`.
3. Save.

### 6.2 Codex Gateway Tool (OpenAPI)
1. Go to `Settings -> External Tools`.
2. Add OpenAPI server:
- URL: `http://codex-gateway:8091`
- Path: `openapi.json`
- Auth type: `bearer`
- Key: value of `CODEX_GATEWAY_API_KEY`

### 6.3 Context7 Tool
Choose one:
- Direct MCP (recommended):
  - Go to `Settings -> General -> Manage Tool Servers`
  - Add MCP URL: `https://mcp.context7.com/mcp`
  - Set API key in auth settings
- mcpo bridge (OpenAPI):
  - URL: `http://mcpo-context7:8000`
  - Path: `openapi.json`
  - Auth type: `bearer`
  - Key: value of `MCPO_CONTEXT7_API_KEY`

If tools exist in admin settings but not in normal chat, check role/permission visibility for tools.

## 7. Start Open WebUI MCP Server (Optional)

Use this if you want MCP clients (Codex CLI, Claude Desktop) to manage Open WebUI objects via MCP.

```bash
cd "$REPO_DIR"
./run-openwebui-mcp.sh
```

Default MCP endpoint:
- `http://127.0.0.1:8001/mcp`

Related env keys:
- `OPENWEBUI_MCP_OPENWEBUI_URL`
- `OPENWEBUI_MCP_BIND_HOST`
- `OPENWEBUI_MCP_PORT`
- `OPENWEBUI_MCP_PATH`
- `OPENWEBUI_MCP_API_KEY`

## 8. Quick Health Checks

```bash
curl -sS http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | head
curl -sS http://localhost:8091/healthz
curl -sS http://localhost:8011/openapi.json | head
curl -i http://127.0.0.1:8001/mcp | head
```

`/mcp` returning HTTP `406` on plain curl is expected because MCP endpoint expects SSE/MCP headers.

## 9. Runtime Notes

- Containers started by an admin user keep running after logout.
- Keep data mount path unchanged (`/srv/docker/ollama/open-webui`) to avoid migration issues.
- Grant only required folder access to the non-admin runtime user.
