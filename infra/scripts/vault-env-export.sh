#!/usr/bin/env bash
# Reads secrets from Vault dev mode and exports them as environment variables.
# Usage: source infra/scripts/vault-env-export.sh
#   or:  eval "$(bash infra/scripts/vault-env-export.sh)"
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-root}"

export VAULT_ADDR VAULT_TOKEN

oracle=$(vault kv get -format=json secret/aial-dev/oracle/credentials 2>/dev/null) || {
  echo "ERROR: Cannot read secret/aial-dev/oracle/credentials from Vault." >&2
  echo "Run 'make seed-secrets' first." >&2
  exit 1
}
keycloak=$(vault kv get -format=json secret/aial-dev/keycloak/client 2>/dev/null) || {
  echo "ERROR: Cannot read secret/aial-dev/keycloak/client from Vault." >&2
  exit 1
}
kong=$(vault kv get -format=json secret/aial-dev/kong/admin 2>/dev/null) || {
  echo "ERROR: Cannot read secret/aial-dev/kong/admin from Vault." >&2
  exit 1
}

extract() {
  echo "$1" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data']['$2'])"
}

cat <<EOF
export AIAL_ORACLE_USERNAME="$(extract "$oracle" username)"
export AIAL_ORACLE_PASSWORD="$(extract "$oracle" password)"
export AIAL_ORACLE_DSN="$(extract "$oracle" dsn)"
export AIAL_KEYCLOAK_CLIENT_SECRET="$(extract "$keycloak" client_secret)"
export AIAL_KONG_ADMIN_TOKEN="$(extract "$kong" admin_token)"
EOF
