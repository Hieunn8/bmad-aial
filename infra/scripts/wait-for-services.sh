#!/usr/bin/env bash
set -euo pipefail

check() {
  local name="$1"
  local url="$2"
  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name healthy"
      return 0
    fi
    sleep 1
  done
  echo "$name not healthy in 60s" >&2
  return 1
}

check_tcp() {
  local name="$1"
  local host="$2"
  local port="$3"
  for _ in $(seq 1 60); do
    if (echo > /dev/tcp/"$host"/"$port") 2>/dev/null; then
      echo "$name healthy"
      return 0
    fi
    sleep 1
  done
  echo "$name not healthy in 60s" >&2
  return 1
}

check vault     "http://localhost:8200/v1/sys/health"
check_tcp postgres localhost 5432
check_tcp redis    localhost 6379
check weaviate  "http://localhost:8081/v1/.well-known/ready"
check keycloak  "http://localhost:8080/"
check_tcp cerbos   localhost 3592
check kong      "http://localhost:8001/"
