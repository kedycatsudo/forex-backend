.PHONY: dev down logs ps test lint format migrate makemigration seed shell ctest clint

# Compose command (supports old docker-compose and new docker compose)
DC := docker-compose

dev:
	$(DC) up --build -d

down:
	$(DC) down --remove-orphans

logs:
	$(DC) logs -f --tail=200 api postgres

ps:
	$(DC) ps

# Host-consistent command entrypoints (run inside api container)
test:
	$(DC) exec api pytest

lint:
	$(DC) exec api ruff check .
	$(DC) exec api black --check .

format:
	$(DC) exec api ruff check . --fix
	$(DC) exec api black .

migrate:
	$(DC) exec api alembic upgrade head

makemigration:
	@test -n "$(msg)" || (echo 'Usage: make makemigration msg="..."' && exit 1)
	$(DC) exec api alembic revision --autogenerate -m "$(msg)"

seed:
	$(DC) exec api python -m app.db.seed

shell:
	$(DC) exec api sh

# Explicit aliases for clarity in docs/CI
ctest:
	$(MAKE) test

clint:
	$(MAKE) lint