# Open WebUI + Ollama

Chat interface for local LLMs. Ollama runs natively for Metal GPU acceleration.

## Setup (Mac)

```bash
brew install ollama
ollama serve
ollama pull ministral-3:8b
docker-compose up -d
```

## Access

Open WebUI: http://localhost:3040

## Workflow

- **Local workhorse (ministral-3:8b)**: Plans, drafts, quick tasks. Newer than Mistral 7B, 256K context, function calling.
- **Codex (API)**: Complex execution, heavy lifting
- Add Codex/OpenAI in Open WebUI Settings > Connections

## Mattermost + OpenClaw

Connect OpenClaw to Mattermost. Local model plans → Codex executes when ready. Saves API tokens.

## Switching Models

- **Open WebUI**: Dropdown per chat. Add Ollama + Codex in Settings > Connections.
- **OpenClaw CLI**: `openclaw models set ollama/ministral-3:8b` or `openclaw models set anthropic/claude-sonnet-4` — then `openclaw configure` for interactive setup.
- **Claude Code local**: `ollama launch claude` — uses local model; switch to API via Claude Code settings.

## Claude Code + Local

Run Claude Code fully local: `ollama launch claude`, pick `ministral-3:8b` or `qwen3-coder`. Zero API cost.
