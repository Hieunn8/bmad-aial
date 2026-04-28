.PHONY: install dev test lint format infra-up infra-down seed-secrets init-schemas configure-kong-jwt

install:
	uv sync --all-packages
	uv run pre-commit install

dev: infra-up
	@echo "Infrastructure is up. Run application services separately as needed."

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

infra-up:
	docker compose -f infra/docker-compose.dev.yml up -d
	bash infra/scripts/wait-for-services.sh
	bash infra/scripts/seed-secrets.sh
	bash infra/scripts/vault-to-dotenv.sh
	bash infra/scripts/configure-kong-jwt.sh
	docker compose -f infra/docker-compose.dev.yml restart kong
	PYTHONPATH=infra uv run python infra/scripts/init-weaviate-schema.py
	@echo "Secrets exported to .env.infra — source with: eval \"\$$(bash infra/scripts/vault-env-export.sh)\""

infra-down:
	docker compose -f infra/docker-compose.dev.yml down

seed-secrets:
	bash infra/scripts/seed-secrets.sh

init-schemas:
	PYTHONPATH=infra uv run python infra/scripts/init-weaviate-schema.py

configure-kong-jwt:
	bash infra/scripts/configure-kong-jwt.sh
	docker compose -f infra/docker-compose.dev.yml restart kong
