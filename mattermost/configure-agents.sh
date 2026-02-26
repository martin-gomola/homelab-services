#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found at $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

DATA_ROOT="${DATA_DIR:-/srv/docker}"
CONFIG_PATH="${MATTERMOST_CONFIG_PATH:-$DATA_ROOT/mattermost/config/config.json}"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "ERROR: Mattermost config.json not found at $CONFIG_PATH" >&2
  exit 1
fi

AGENTS_ENABLE_OLLAMA="${AGENTS_ENABLE_OLLAMA:-true}"
AGENTS_OLLAMA_API_URL="${AGENTS_OLLAMA_API_URL:-http://host.docker.internal:11434/v1}"
AGENTS_OLLAMA_API_KEY="${AGENTS_OLLAMA_API_KEY:-}"
AGENTS_OLLAMA_MODEL="${AGENTS_OLLAMA_MODEL:-qwen2.5-coder:7b}"
AGENTS_OLLAMA_BOT_NAME="${AGENTS_OLLAMA_BOT_NAME:-ai}"
AGENTS_OLLAMA_BOT_DISPLAY_NAME="${AGENTS_OLLAMA_BOT_DISPLAY_NAME:-Ollama AI}"
AGENTS_OLLAMA_BOT_INSTRUCTIONS="${AGENTS_OLLAMA_BOT_INSTRUCTIONS:-You are a practical engineering assistant running on local Ollama.}"

AGENTS_ENABLE_CODEX_BOT="${AGENTS_ENABLE_CODEX_BOT:-false}"
AGENTS_CODEX_PROVIDER="${AGENTS_CODEX_PROVIDER:-openaicompatible}"
AGENTS_CODEX_API_URL="${AGENTS_CODEX_API_URL:-http://codex-bridge:8092/v1}"
AGENTS_CODEX_API_KEY="${AGENTS_CODEX_API_KEY:-}"
AGENTS_CODEX_MODEL="${AGENTS_CODEX_MODEL:-gpt-5-codex}"
AGENTS_CODEX_BOT_NAME="${AGENTS_CODEX_BOT_NAME:-codex}"
AGENTS_CODEX_BOT_DISPLAY_NAME="${AGENTS_CODEX_BOT_DISPLAY_NAME:-Codex}"
AGENTS_CODEX_BOT_INSTRUCTIONS="${AGENTS_CODEX_BOT_INSTRUCTIONS:-You are Codex, focused on code and infrastructure tasks. Format replies with clear Mattermost Markdown, prefer short title + bullet points, and use [label](url) links for sources.}"

AGENTS_ALLOWED_UPSTREAM_HOSTNAMES="${AGENTS_ALLOWED_UPSTREAM_HOSTNAMES:-host.docker.internal,api.openai.com,codex-bridge}"
AGENTS_ENABLE_LLM_TRACE="${AGENTS_ENABLE_LLM_TRACE:-false}"
AGENTS_STREAMING_TIMEOUT_SECONDS="${AGENTS_STREAMING_TIMEOUT_SECONDS:-120}"
AGENTS_DEFAULT_BOT_NAME="${AGENTS_DEFAULT_BOT_NAME:-}"
RESTART_AFTER_CONFIG="${RESTART_AFTER_CONFIG:-true}"

if ! [[ "$AGENTS_STREAMING_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: AGENTS_STREAMING_TIMEOUT_SECONDS must be numeric" >&2
  exit 1
fi

if is_true "$AGENTS_ENABLE_CODEX_BOT"; then
  case "$AGENTS_CODEX_PROVIDER" in
    openai|openaicompatible) ;;
    *)
      echo "ERROR: AGENTS_CODEX_PROVIDER must be openai or openaicompatible" >&2
      exit 1
      ;;
  esac

  if [[ -z "$AGENTS_CODEX_API_KEY" && "$AGENTS_CODEX_PROVIDER" == "openai" ]]; then
    echo "ERROR: AGENTS_CODEX_API_KEY is required when AGENTS_CODEX_PROVIDER=openai" >&2
    exit 1
  fi
fi

services='[]'
bots='[]'

if is_true "$AGENTS_ENABLE_OLLAMA"; then
  services="$(
    jq \
      --arg id "svc-ollama" \
      --arg name "Ollama Local" \
      --arg type "openaicompatible" \
      --arg apiKey "$AGENTS_OLLAMA_API_KEY" \
      --arg apiURL "$AGENTS_OLLAMA_API_URL" \
      --arg model "$AGENTS_OLLAMA_MODEL" \
      --argjson timeout "$AGENTS_STREAMING_TIMEOUT_SECONDS" \
      '. + [{
        id: $id,
        name: $name,
        type: $type,
        apiKey: $apiKey,
        orgId: "",
        defaultModel: $model,
        apiURL: $apiURL,
        tokenLimit: 0,
        streamingTimeoutSeconds: $timeout,
        sendUserID: false,
        outputTokenLimit: 0,
        useResponsesAPI: false
      }]' <<<"$services"
  )"

  bots="$(
    jq \
      --arg id "bot-ollama" \
      --arg name "$AGENTS_OLLAMA_BOT_NAME" \
      --arg displayName "$AGENTS_OLLAMA_BOT_DISPLAY_NAME" \
      --arg instructions "$AGENTS_OLLAMA_BOT_INSTRUCTIONS" \
      --arg serviceID "svc-ollama" \
      '. + [{
        id: $id,
        name: $name,
        displayName: $displayName,
        customInstructions: $instructions,
        serviceID: $serviceID,
        model: "",
        enableVision: false,
        disableTools: false,
        channelAccessLevel: 0,
        channelIDs: [],
        userAccessLevel: 0,
        userIDs: [],
        teamIDs: [],
        maxFileSize: 0,
        enabledNativeTools: [],
        reasoningEnabled: false,
        reasoningEffort: "medium",
        thinkingBudget: 0
      }]' <<<"$bots"
  )"
fi

if is_true "$AGENTS_ENABLE_CODEX_BOT"; then
  services="$(
    jq \
      --arg id "svc-codex" \
      --arg name "Codex Service" \
      --arg type "$AGENTS_CODEX_PROVIDER" \
      --arg apiKey "$AGENTS_CODEX_API_KEY" \
      --arg apiURL "$AGENTS_CODEX_API_URL" \
      --arg model "$AGENTS_CODEX_MODEL" \
      --argjson timeout "$AGENTS_STREAMING_TIMEOUT_SECONDS" \
      '. + [{
        id: $id,
        name: $name,
        type: $type,
        apiKey: $apiKey,
        orgId: "",
        defaultModel: $model,
        apiURL: $apiURL,
        tokenLimit: 0,
        streamingTimeoutSeconds: $timeout,
        sendUserID: false,
        outputTokenLimit: 0,
        useResponsesAPI: false
      }]' <<<"$services"
  )"

  bots="$(
    jq \
      --arg id "bot-codex" \
      --arg name "$AGENTS_CODEX_BOT_NAME" \
      --arg displayName "$AGENTS_CODEX_BOT_DISPLAY_NAME" \
      --arg instructions "$AGENTS_CODEX_BOT_INSTRUCTIONS" \
      --arg serviceID "svc-codex" \
      '. + [{
        id: $id,
        name: $name,
        displayName: $displayName,
        customInstructions: $instructions,
        serviceID: $serviceID,
        model: "",
        enableVision: false,
        disableTools: false,
        channelAccessLevel: 0,
        channelIDs: [],
        userAccessLevel: 0,
        userIDs: [],
        teamIDs: [],
        maxFileSize: 0,
        enabledNativeTools: [],
        reasoningEnabled: false,
        reasoningEffort: "medium",
        thinkingBudget: 0
      }]' <<<"$bots"
  )"
fi

if [[ -z "$AGENTS_DEFAULT_BOT_NAME" ]]; then
  if is_true "$AGENTS_ENABLE_OLLAMA"; then
    AGENTS_DEFAULT_BOT_NAME="$AGENTS_OLLAMA_BOT_NAME"
  elif is_true "$AGENTS_ENABLE_CODEX_BOT"; then
    AGENTS_DEFAULT_BOT_NAME="$AGENTS_CODEX_BOT_NAME"
  else
    AGENTS_DEFAULT_BOT_NAME="ai"
  fi
fi

if is_true "$AGENTS_ENABLE_LLM_TRACE"; then
  enable_llm_trace=true
else
  enable_llm_trace=false
fi

backup_path="${CONFIG_PATH}.bak.$(date +%Y%m%d%H%M%S)"
cp "$CONFIG_PATH" "$backup_path"

tmp_cfg="$(mktemp)"
jq \
  --arg allowedHosts "$AGENTS_ALLOWED_UPSTREAM_HOSTNAMES" \
  --arg defaultBot "$AGENTS_DEFAULT_BOT_NAME" \
  --arg transcriptBackend "" \
  --argjson enableLLMTrace "$enable_llm_trace" \
  --argjson services "$services" \
  --argjson bots "$bots" \
  '
  .PluginSettings.Enable = true
  | .PluginSettings.EnableUploads = true
  | .PluginSettings.Plugins["mattermost-ai"].config.allowedUpstreamHostnames = $allowedHosts
  | .PluginSettings.Plugins["mattermost-ai"].config.services = $services
  | .PluginSettings.Plugins["mattermost-ai"].config.bots = $bots
  | .PluginSettings.Plugins["mattermost-ai"].config.defaultBotName = $defaultBot
  | .PluginSettings.Plugins["mattermost-ai"].config.enableLLMTrace = $enableLLMTrace
  | .PluginSettings.Plugins["mattermost-ai"].config.transcriptBackend = $transcriptBackend
  ' "$CONFIG_PATH" >"$tmp_cfg"

mv "$tmp_cfg" "$CONFIG_PATH"

echo "Wrote Agents config to: $CONFIG_PATH"
echo "Backup saved as: $backup_path"
echo "Configured services: $(jq 'length' <<<"$services")"
echo "Configured bots: $(jq 'length' <<<"$bots")"

if is_true "$RESTART_AFTER_CONFIG"; then
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" --env-file "$ENV_FILE" restart mattermost >/dev/null
  echo "Restarted mattermost container."
fi
