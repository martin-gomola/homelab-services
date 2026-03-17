.PHONY: help setup up down restart logs ps codex-mcp-install tuya-local-install

.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  setup   - Generate runtime config and credentials from .env"
	@echo "  up      - Run setup and start the stack"
	@echo "  down    - Stop the stack"
	@echo "  restart - Restart the stack"
	@echo "  logs    - Tail stack logs"
	@echo "  ps      - Show container status"
	@echo "  codex-mcp-install - Register Home Assistant MCP in local Codex config"
	@echo "  tuya-local-install - Install pinned tuya_local custom component and repo overlays"

setup:
	./setup.sh

up: setup
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail 50

ps:
	docker compose ps

codex-mcp-install:
	bash ./scripts/install-codex-mcp.sh

tuya-local-install:
	bash ./scripts/install-tuya-local.sh
