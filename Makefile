.PHONY: install dev test lint format infra-up infra-down seed-secrets init-schemas configure-kong-jwt oracle-vpd-up oracle-vpd-test oracle-vpd-down walking-skeleton-gate

install:
	uv sync --all-packages
	npm install
	uv run pre-commit install

dev: infra-up
	@echo "Infrastructure is up. Run application services separately as needed."

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	npx eslint .

format:
	uv run ruff format .

infra-up:
	@echo "Phase 1: Starting Vault and seeding secrets ..."
	docker compose -f infra/docker-compose.dev.yml up -d vault
	bash infra/scripts/wait-for-vault.sh
	bash infra/scripts/seed-secrets.sh
	bash infra/scripts/vault-to-dotenv.sh
	@echo "Phase 2: Starting remaining services with secrets available ..."
	@test -f infra/kong/kong.yml || cp infra/kong/kong.yml.tmpl infra/kong/kong.yml
	docker compose --env-file .env.infra -f infra/docker-compose.dev.yml up -d
	bash infra/scripts/wait-for-services.sh
	bash infra/scripts/configure-kong-jwt.sh infra/kong
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
	bash infra/scripts/configure-kong-jwt.sh infra/kong
	docker compose -f infra/docker-compose.dev.yml restart kong

oracle-vpd-up:
	docker compose --profile oracle-vpd -f infra/docker-compose.dev.yml up -d oracle-free

oracle-vpd-test:
	AIAL_RUN_ORACLE_VPD_TESTS=1 uv run pytest tests/test_oracle_vpd_smoke.py -m "requires_oracle and security_gate" -q

oracle-vpd-down:
	docker compose --profile oracle-vpd -f infra/docker-compose.dev.yml stop oracle-free

walking-skeleton-gate:
	@echo "Running Epic 1 Walking Skeleton Gate — requires full infra stack (make infra-up first)"
	AIAL_RUN_E2E_TESTS=1 uv run pytest tests/test_e2e_walking_skeleton.py \
		-m "walking_skeleton_gate" \
		-v \
		--timeout=60 \
		-x
