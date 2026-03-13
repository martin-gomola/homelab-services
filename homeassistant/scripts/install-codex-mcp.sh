#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repo_root/.env"
server_name="home_assistant"
token_env_var="HOME_ASSISTANT_ACCESS_TOKEN"
codex_config_file="${HOME}/.codex/config.toml"

usage() {
  cat <<'EOF'
Usage: ./scripts/install-codex-mcp.sh [--env-file PATH] [--name NAME] [--token-env-var ENV_VAR]

Registers the Home Assistant MCP endpoint from this repo into the local Codex config.

Defaults:
  --env-file        ./.env
  --name            home_assistant
  --token-env-var   HOME_ASSISTANT_ACCESS_TOKEN

Before using the MCP from Codex, make sure the bearer token env var is available
to Codex. If the token key exists in this repo's `.env`, this script will also sync
it into `~/.codex/config.toml` under `shell_environment_policy.set`.
EOF
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

strip_wrapping_quotes() {
  local value="$1"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

read_env_value() {
  local key="$1"
  local raw
  raw="$(awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$env_file")"
  raw="$(trim "$raw")"
  strip_wrapping_quotes "$raw"
}

sync_codex_shell_env() {
  local key="$1"
  local value="$2"
  local config_file="$3"
  python3 - <<'PY' "$config_file" "$key" "$value"
from pathlib import Path
import re
import sys

config_path = Path(sys.argv[1]).expanduser()
key = sys.argv[2]
value = sys.argv[3]
section_header = "[shell_environment_policy.set]"

if config_path.exists():
    text = config_path.read_text(encoding="utf-8")
else:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    text = ""

pattern = re.compile(r"(?ms)^\[shell_environment_policy\.set\]\n(?P<body>.*?)(?=^\[|\Z)")
match = pattern.search(text)

if value:
    entry = f'{key} = "{value.replace("\\\\", "\\\\\\\\").replace(chr(34), "\\\\" + chr(34))}"\n'
else:
    entry = ""

if match:
    body = match.group("body")
    body = re.sub(rf"(?m)^{re.escape(key)}\s*=.*\n?", "", body)
    if entry:
        if body and not body.endswith("\n"):
            body += "\n"
        body += entry
    replacement = f"{section_header}\n{body}"
    text = text[: match.start()] + replacement + text[match.end() :]
else:
    if entry:
        if text and not text.endswith("\n"):
            text += "\n"
        text += f"{section_header}\n{entry}"

config_path.write_text(text, encoding="utf-8")
PY
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      env_file="$2"
      shift 2
      ;;
    --name)
      server_name="$2"
      shift 2
      ;;
    --token-env-var)
      token_env_var="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$env_file" ]]; then
  echo "Missing env file: $env_file" >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "The 'codex' CLI is not installed or not on PATH." >&2
  exit 1
fi

ha_url="$(read_env_value "HA_URL")"
if [[ -z "$ha_url" ]]; then
  echo "HA_URL is missing in $env_file" >&2
  exit 1
fi

mcp_url="${ha_url%/}/api/mcp"
ha_token="$(read_env_value "$token_env_var")"

if codex mcp get "$server_name" >/dev/null 2>&1; then
  codex mcp remove "$server_name" >/dev/null
fi

codex mcp add "$server_name" --url "$mcp_url" --bearer-token-env-var "$token_env_var" >/dev/null
sync_codex_shell_env "$token_env_var" "$ha_token" "$codex_config_file"

echo "Registered Codex MCP server '$server_name' -> $mcp_url"
if [[ -n "$ha_token" ]]; then
  echo "Synced $token_env_var from $env_file into $codex_config_file"
else
  echo "Note: $token_env_var is empty in $env_file."
  echo "Add your Home Assistant long-lived token there and rerun this command."
fi

codex mcp get "$server_name"
