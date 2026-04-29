#!/usr/bin/env bash
set -euo pipefail

for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:8200/v1/sys/health" >/dev/null 2>&1; then
    echo "vault healthy"
    exit 0
  fi
  sleep 1
done

echo "vault not healthy in 60s" >&2
exit 1
