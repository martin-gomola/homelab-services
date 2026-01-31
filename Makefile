.PHONY: help list status deploy stop restart logs update backup clean ps

.DEFAULT_GOAL := help

help:
	@echo "Usage: make <target> [SERVICE=name]"
	@echo ""
	@echo "Targets:"
	@echo "  list     - List available services"
	@echo "  status   - Show running services"
	@echo "  deploy   - Deploy service (requires SERVICE=)"
	@echo "  stop     - Stop service (requires SERVICE=)"
	@echo "  restart  - Restart service (requires SERVICE=)"
	@echo "  logs     - Tail logs (requires SERVICE=)"
	@echo "  update   - Pull and redeploy (requires SERVICE=)"
	@echo "  backup   - Backup service data (requires SERVICE=)"
	@echo "  clean    - Remove unused Docker resources"
	@echo ""
	@echo "Example: make deploy SERVICE=affine"

list:
	@for dir in */; do \
		[ -f "$$dir/docker-compose.yml" ] && echo "$${dir%/}"; \
	done

status:
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

ps: status

deploy:
	@[ -z "$(SERVICE)" ] && echo "Error: SERVICE required" && exit 1 || true
	@[ ! -d "$(SERVICE)" ] && echo "Error: $(SERVICE) not found" && exit 1 || true
	@[ ! -f "$(SERVICE)/.env" ] && [ -f "$(SERVICE)/.env.example" ] && \
		echo "Run: cd $(SERVICE) && cp .env.example .env" && exit 1 || true
	cd $(SERVICE) && docker-compose pull && docker-compose up -d

stop:
	@[ -z "$(SERVICE)" ] && echo "Error: SERVICE required" && exit 1 || true
	cd $(SERVICE) && docker-compose stop

restart:
	@[ -z "$(SERVICE)" ] && echo "Error: SERVICE required" && exit 1 || true
	cd $(SERVICE) && docker-compose restart

logs:
	@[ -z "$(SERVICE)" ] && echo "Error: SERVICE required" && exit 1 || true
	cd $(SERVICE) && docker-compose logs -f --tail 50

update:
	@[ -z "$(SERVICE)" ] && echo "Error: SERVICE required" && exit 1 || true
	cd $(SERVICE) && docker-compose pull && docker-compose up -d

backup:
	@[ -z "$(SERVICE)" ] && echo "Error: SERVICE required" && exit 1 || true
	@if [ -f "$(SERVICE)/backup-db.sh" ]; then \
		cd $(SERVICE) && ./backup-db.sh; \
	else \
		sudo mkdir -p /srv/backups/$(SERVICE) && \
		sudo tar -czf /srv/backups/$(SERVICE)/backup-$$(date +%Y%m%d).tar.gz /srv/docker/$(SERVICE)/; \
	fi

clean:
	docker container prune -f
	docker image prune -f

##@ Git

commit: ## Commit changes (interactive prompt for message, use PUSH=true to push)
	@echo "$(BLUE)=== Git Commit ===$(NC)"
	@echo ""
	@if [ -z "$$(git status --porcelain)" ]; then \
		echo "$(YELLOW)No changes to commit$(NC)"; \
		exit 0; \
	fi
	@echo "$(YELLOW)Changes to be committed:$(NC)"
	@git status --short
	@echo ""
	@if [ -z "$(COMMIT_MSG)" ]; then \
		echo -n "$(BLUE)Enter commit message: $(NC)"; \
		read MSG; \
		if [ -z "$$MSG" ]; then \
			echo "$(YELLOW)No message provided. Using default message.$(NC)"; \
			MSG="Update docker-compose configurations"; \
		fi; \
		git add -A; \
		git commit -m "$$MSG" || (echo "$(RED)Commit failed$(NC)" && exit 1); \
		echo "$(GREEN)✓ Changes committed: $$MSG$(NC)"; \
	else \
		git add -A; \
		git commit -m "$(COMMIT_MSG)" || (echo "$(RED)Commit failed$(NC)" && exit 1); \
		echo "$(GREEN)✓ Changes committed: $(COMMIT_MSG)$(NC)"; \
	fi
	@if [ "$(PUSH)" = "true" ]; then \
		echo "$(BLUE)Pushing to remote...$(NC)"; \
		git push || (echo "$(RED)Push failed$(NC)" && exit 1); \
		echo "$(GREEN)✓ Changes pushed to remote$(NC)"; \
	else \
		echo "$(YELLOW)Tip: Use $(GREEN)make commit PUSH=true$(NC) to push after committing"; \
	fi