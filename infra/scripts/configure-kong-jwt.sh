#!/usr/bin/env bash
# Fetches the Keycloak realm RSA public key and patches kong.yml so that
# Kong's JWT plugin can verify RS256 tokens.
#
# Must be run AFTER Keycloak is healthy and BEFORE Kong starts (or Kong
# must be reloaded after).
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-aial}"
KONG_YML="${1:-infra/kong/kong.yml}"

echo "Fetching realm public key from $KEYCLOAK_URL/realms/$REALM ..."

RAW_KEY=$(curl -fsS "$KEYCLOAK_URL/realms/$REALM" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['public_key'])
")

if [ -z "$RAW_KEY" ]; then
  echo "ERROR: Could not fetch public key from Keycloak realm '$REALM'" >&2
  exit 1
fi

PEM_KEY="-----BEGIN PUBLIC KEY-----
$RAW_KEY
-----END PUBLIC KEY-----"

# Escape newlines for sed replacement (use python for cross-platform safety)
python3 -c "
import sys, re
kong = open('$KONG_YML').read()
pem = '''$PEM_KEY'''
kong = kong.replace('\"__KEYCLOAK_RSA_PUBLIC_KEY__\"', repr(pem))
open('$KONG_YML', 'w').write(kong)
"

echo "Patched $KONG_YML with Keycloak RSA public key for realm '$REALM'."
