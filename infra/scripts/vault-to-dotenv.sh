#!/usr/bin/env bash
# Reads secrets from Vault and writes .env.infra for docker-compose env_file usage.
# Usage: bash infra/scripts/vault-to-dotenv.sh
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-root}"
OUTPUT="${1:-.env.infra}"

export VAULT_ADDR VAULT_TOKEN

oracle=$(vault kv get -format=json secret/aial-dev/oracle/credentials 2>/dev/null) || {
  echo "ERROR: Cannot read secret/aial-dev/oracle/credentials — run 'make seed-secrets' first." >&2
  exit 1
}
keycloak=$(vault kv get -format=json secret/aial-dev/keycloak/client 2>/dev/null) || {
  echo "ERROR: Cannot read secret/aial-dev/keycloak/client." >&2
  exit 1
}
kong=$(vault kv get -format=json secret/aial-dev/kong/admin 2>/dev/null) || {
  echo "ERROR: Cannot read secret/aial-dev/kong/admin." >&2
  exit 1
}

extract() {
  echo "$1" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data']['$2'])"
}

cat > "$OUTPUT" <<EOF
AIAL_ORACLE_USERNAME=$(extract "$oracle" username)
AIAL_ORACLE_PASSWORD=$(extract "$oracle" password)
AIAL_ORACLE_DSN=$(extract "$oracle" dsn)
AIAL_KEYCLOAK_CLIENT_SECRET=$(extract "$keycloak" client_secret)
AIAL_KONG_ADMIN_TOKEN=$(extract "$kong" admin_token)
EOF

echo "Wrote secrets to $OUTPUT"
