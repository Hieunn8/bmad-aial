#!/usr/bin/env bash
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-root}"

export VAULT_ADDR VAULT_TOKEN

vault kv put secret/aial-dev/oracle/credentials username="dev_oracle_user" password="dev_oracle_pass" dsn="localhost:1521/FREEPDB1"
vault kv put secret/aial-dev/keycloak/client client_secret="dev-keycloak-secret"
vault kv put secret/aial-dev/kong/admin admin_token="dev-kong-token"
