#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-mcp"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install with: brew install uv" >&2
  exit 1
fi

if [ ! -x "${VENV_DIR}/bin/openwebui-mcp" ]; then
  uv venv "${VENV_DIR}"
  uv pip install --python "${VENV_DIR}/bin/python" \
    git+https://github.com/troylar/open-webui-mcp-server.git
fi

read_env_value() {
  local key="$1"
  local env_file="${ROOT_DIR}/.env"
  [ -f "${env_file}" ] || return 0
  local line
  line="$(grep -E "^${key}=" "${env_file}" | tail -n 1 || true)"
  [ -n "${line}" ] || return 0
  printf '%s' "${line#*=}"
}

openwebui_url="${OPENWEBUI_MCP_OPENWEBUI_URL:-${OPENWEBUI_URL:-$(read_env_value OPENWEBUI_MCP_OPENWEBUI_URL)}}"
if [ -z "${openwebui_url}" ]; then
  openwebui_url="${OPENWEBUI_URL:-$(read_env_value OPENWEBUI_URL)}"
fi
if [ -z "${openwebui_url}" ]; then
  openwebui_url="http://localhost:3040"
fi

bind_host="${OPENWEBUI_MCP_BIND_HOST:-$(read_env_value OPENWEBUI_MCP_BIND_HOST)}"
bind_host="${bind_host:-127.0.0.1}"

mcp_port="${OPENWEBUI_MCP_PORT:-$(read_env_value OPENWEBUI_MCP_PORT)}"
mcp_port="${mcp_port:-8001}"

mcp_path="${OPENWEBUI_MCP_PATH:-$(read_env_value OPENWEBUI_MCP_PATH)}"
mcp_path="${mcp_path:-/mcp}"

mcp_transport="${OPENWEBUI_MCP_TRANSPORT:-$(read_env_value OPENWEBUI_MCP_TRANSPORT)}"
mcp_transport="${mcp_transport:-http}"

mcp_api_key="${OPENWEBUI_MCP_API_KEY:-$(read_env_value OPENWEBUI_MCP_API_KEY)}"

export OPENWEBUI_URL="${openwebui_url}"
export MCP_TRANSPORT="${mcp_transport}"
export MCP_HTTP_HOST="${bind_host}"
export MCP_HTTP_PORT="${mcp_port}"
export MCP_HTTP_PATH="${mcp_path}"

if [ -n "${mcp_api_key}" ]; then
  export OPENWEBUI_API_KEY="${mcp_api_key}"
fi

exec "${VENV_DIR}/bin/openwebui-mcp"
