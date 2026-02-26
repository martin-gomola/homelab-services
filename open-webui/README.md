# Open WebUI + Ollama Setup (Step by Step)

This is a copy/paste runbook for:
- Ollama local models
- Open WebUI in Docker
- Context7 tool integration
- Codex Gateway tool integration
- Open WebUI MCP server (`openwebui-mcp-server`) via `uv`

## Quick Start (Minimum Path)

Use this order if you want the fastest working setup:
1. Install prerequisites (`ollama`, `docker`, `uv`).
2. Copy `.env.example` to `.env` and set required keys.
3. Start Ollama and pull `ministral-3:8b` and `qwen2.5-coder:7b`.
4. Start Open WebUI with `docker compose up -d`.
5. If you need External Tools, start `mcpo` + `codex-gateway` profiles.
6. In Open WebUI, configure Connections and External Tools.
7. In chat, use either `ministral-3:8b` (native tools) or `qwen2.5-coder:7b` (non-native tool flow).

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
- `HOST_DATA_DIR=/Users/<service-user>/dev/homelab-services/data` (macOS/OrbStack: prevents data loss from `/srv/docker` inside VM)
- `WEBUI_URL=https://ai.home.example.com`
- `ENABLE_WEBSOCKET_SUPPORT=true`
- `WEBUI_SECRET_KEY=<your_64_hex_chars>`
- `MCPO_CONTEXT7_API_KEY=<your_context7_key>` (if using mcpo)
- `CODEX_GATEWAY_API_KEY=<your_gateway_key>` (if using Codex Gateway)
- `CODEX_CONFIG_DIR=/Users/<service-user>/.codex`
- `CODEX_WORKSPACE_DIR=/Users/<service-user>/dev/homelab-services`
- `CODEX_DEFAULT_MODEL=gpt-5-codex` (recommended for lower latency)
- `CODEX_DEFAULT_REASONING_EFFORT=low` (recommended for lower latency)
- `CODEX_DISABLE_CONTEXT7=true` (avoid per-request MCP startup overhead in gateway)

## 3. Start Ollama and Pull Required Model

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

Use `ministral-3:8b` for native tool calls.  
Use `qwen2.5-coder:7b` with non-native tool flow configured by `OPENWEBUI_TOOL_MODEL_NON_NATIVE_IDS`.

## 4. Start Open WebUI Stack

Core service:

```bash
cd "$REPO_DIR"
docker compose up -d
```

This repo builds a local Open WebUI image (`Dockerfile.open-webui`) that patches
non-native tool routing for models like `qwen2.5-coder:7b`.

Optional tool services (`mcpo` + `codex-gateway`) for External Tools:

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

### 6.4 Model Selection For External Tools
1. Open a new chat.
2. Select model `ministral-3:8b` or `qwen2.5-coder:7b`.
3. Keep `qwen2.5-coder:7b` in non-native mode via `OPENWEBUI_TOOL_MODEL_NON_NATIVE_IDS`.

### 6.5 Reapply Tool Servers After Reset (Script)

This script upserts (does not wipe other entries):
- `Context7` as MCP (`https://mcp.context7.com/mcp`)
- `Codex Gateway` as OpenAPI (`http://codex-gateway:8091/openapi.json`)
- Tool model settings for `OPENWEBUI_TOOL_MODEL_IDS`:
  - `params.function_calling = native` by default
  - models listed in `OPENWEBUI_TOOL_MODEL_NON_NATIVE_IDS` are set to `params.function_calling = default`
  - `meta.toolIds` includes both Context7 and Codex Gateway
- Slash prompt `/codex` (enabled by default) for faster Codex Gateway usage

Run:

```bash
cd "$REPO_DIR"
./sync-tool-servers.py --email "<admin_email>"
```

It reads keys from `.env`:
- `MCPO_CONTEXT7_API_KEY` (or `CONTEXT7_API_KEY` env override)
- `CODEX_GATEWAY_API_KEY`
- `OPENWEBUI_TOOL_MODEL_IDS` (comma-separated, default `ministral-3:8b`)
- `OPENWEBUI_TOOL_MODEL_NON_NATIVE_IDS` (comma-separated, default empty)
- `OPENWEBUI_CODEX_SLASH_ENABLE` (`true`/`false`, default `true`)
- `OPENWEBUI_CODEX_SLASH_COMMAND` (default `codex`)
- `OPENWEBUI_CODEX_SLASH_NAME` (default `Codex Gateway Shortcut`)
- `OPENWEBUI_CODEX_SLASH_CONTENT` (default text that inserts Codex Gateway instruction)

Useful flags:
- `--tool-model-ids "ministral-3:8b,qwen2.5-coder:7b"`
- `--non-native-model-ids "qwen2.5-coder:7b"`
- `--skip-model-upsert` (only manage tool servers)
- `--replace-model-tool-ids` (replace instead of merge)
- `--skip-prompt-upsert` (skip `/codex` shortcut)
- `--codex-command "codex"`
- `--codex-prompt-name "Codex Gateway Shortcut"`
- `--codex-prompt-content "Use Codex Gateway tool delegate_delegate_post to complete this task: "`

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

### 7.1 Keep MCP Running Across Restarts (macOS LaunchAgent)

If `docker`/OrbStack restarts, the standalone MCP bridge process can disappear.  
Use a user LaunchAgent so it auto-starts and stays alive.

Create `~/Library/LaunchAgents/com.openwebui.mcp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.openwebui.mcp</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd "$HOME/dev/homelab-services/open-webui" &amp;&amp; ./run-openwebui-mcp.sh</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>

  <key>StandardOutPath</key>
  <string>/tmp/openwebui-mcp.launchd.out.log</string>

  <key>StandardErrorPath</key>
  <string>/tmp/openwebui-mcp.launchd.err.log</string>
</dict>
</plist>
```

Load and start:

```bash
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.openwebui.mcp.plist"
launchctl kickstart -k "gui/$(id -u)/com.openwebui.mcp"
```

Useful commands:

```bash
# status
launchctl print "gui/$(id -u)/com.openwebui.mcp" | head -n 40

# restart
launchctl kickstart -k "gui/$(id -u)/com.openwebui.mcp"

# stop/unload
launchctl bootout "gui/$(id -u)/com.openwebui.mcp"
```

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

## 10. Troubleshooting

### 10.1 `docker ps` hangs (OrbStack)

If Docker commands hang with no output, restart OrbStack and retry:

```bash
orbctl status
orbctl stop
orbctl start
docker ps
```

### 10.2 Open WebUI MCP endpoint missing after restart

Symptoms:
- `curl http://127.0.0.1:8001/mcp` fails to connect
- MCP tools disappear in clients

Checks:

```bash
pgrep -fl 'openwebui-mcp|run-openwebui-mcp'
curl -i http://127.0.0.1:8001/mcp | head
```

Expected MCP response for plain curl is `406 Not Acceptable` (this is healthy for non-SSE requests).

Recovery:

```bash
launchctl kickstart -k "gui/$(id -u)/com.openwebui.mcp"
```

### 10.3 Ollama API not reachable (`127.0.0.1:11434`)

Checks:

```bash
pgrep -fl 'ollama serve'
curl -sS http://127.0.0.1:11434/api/tags
```

Recovery:

```bash
nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
```
