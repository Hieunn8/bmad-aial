#!/usr/bin/env bash
# Fetches the Keycloak realm RSA public key and generates kong.yml from the
# template so that Kong's JWT plugin can verify RS256 tokens.
#
# Idempotent: always reads from kong.yml.tmpl and writes kong.yml.
# Must be run AFTER Keycloak is healthy and BEFORE Kong starts (or Kong
# must be reloaded after).
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${KEYCLOAK_REALM:-aial}"
KONG_DIR="${1:-infra/kong}"
KONG_TMPL="$KONG_DIR/kong.yml.tmpl"
KONG_YML="$KONG_DIR/kong.yml"

if [ ! -f "$KONG_TMPL" ]; then
  echo "ERROR: Template not found: $KONG_TMPL" >&2
  exit 1
fi

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

KONG_PEM_KEY="$PEM_KEY" KONG_TMPL_PATH="$KONG_TMPL" KONG_YML_PATH="$KONG_YML" python3 -c '
import os

pem = os.environ["KONG_PEM_KEY"]
tmpl_path = os.environ["KONG_TMPL_PATH"]
yml_path = os.environ["KONG_YML_PATH"]

with open(tmpl_path) as f:
    content = f.read()

lines = pem.strip().splitlines()
block = "|-\n" + "\n".join("          " + l for l in lines)
content = content.replace("\"__KEYCLOAK_RSA_PUBLIC_KEY__\"", block)

with open(yml_path, "w") as f:
    f.write(content)
'

echo "Generated $KONG_YML from $KONG_TMPL with Keycloak RSA public key."
