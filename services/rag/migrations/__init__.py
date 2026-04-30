"""Weaviate schema migrations for the RAG service.

Migration scripts are versioned Python files: V001__description.py, V002__description.py, ...
Each script must be idempotent. The bootstrap script (infra/scripts/init-weaviate-schema.py)
runs V001 (initial schema) automatically via weaviate_schema.schema.bootstrap_schema().

Ownership: Epic 2A owns the schema contract in weaviate_schema/schema.py.
Epic 3 (this service) consumes — never forks — that contract.
"""
