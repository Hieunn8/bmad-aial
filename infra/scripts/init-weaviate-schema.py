"""Weaviate schema initialisation entry point.

Uses the canonical schema contract from weaviate_schema.schema.
Run via: PYTHONPATH=infra python infra/scripts/init-weaviate-schema.py
Or via Makefile: make init-schemas
"""

from __future__ import annotations

import os
import sys

from weaviate_schema.schema import bootstrap_schema

WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8081")


def main() -> None:
    print(f"Bootstrapping Weaviate schema at {WEAVIATE_URL} ...")
    bootstrap_schema(WEAVIATE_URL)
    print("Schema bootstrap complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Schema bootstrap failed: {exc}", file=sys.stderr)
        sys.exit(1)
