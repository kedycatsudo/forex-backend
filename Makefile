.PHONY: dev down logs ps test lint format migrate makemigration seed shell

# Compose command (supports old docker-compose and new docker compose)
DC := docker-compose

dev:
	$(DC) up --build -d

down:
	$(DC) down

logs:
	$(DC) logs -f --tail=200 api postgres

ps:
	$(DC) ps

test:
	$(DC) exec api pytest -q

lint:
	$(DC) exec api ruff check .
	$(DC) exec api black --check .

format:
	$(DC) exec api black .
	$(DC) exec api ruff check . --fix

migrate:
	$(DC) exec api alembic upgrade head

makemigration:
	@test -n "$(msg)" || (echo 'Usage: make makemigration msg="add users table"' && exit 1)
	$(DC) exec api alembic revision --autogenerate -m "$(msg)"

seed:
	$(DC) exec api python -m app.db.seed

shell:
	$(DC) exec api sh