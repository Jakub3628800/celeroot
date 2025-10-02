.PHONY: help build up down logs clean test shell

# Default target
help: ## Show this help message
	@echo "Celeroot Commands"
	@echo "=================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Core commands
build: ## Build containers
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Show logs
	docker compose logs -f

clean: ## Stop and clean everything
	docker compose down -v

test: ## Test the CLI
	uv run python -m celeroot config init --no-interactive --force

shell: ## Open shell in dev container
	docker compose exec dev bash
