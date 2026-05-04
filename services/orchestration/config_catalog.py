"""Standardized configuration catalog template for data sources, metrics, and role mappings."""

from __future__ import annotations

CONFIG_CATALOG_TEMPLATE: dict[str, object] = {
    "catalog_version": "2026-05-04",
    "data_sources": [
        {
            "name": "oracle-finance",
            "description": "Primary finance warehouse",
            "host": "db.company.local",
            "port": 1521,
            "service_name": "FINPRD",
            "username": "aial_reader",
            "password": "replace-me",
            "schema_allowlist": ["FINANCE_ANALYTICS", "COMMON_DIM"],
            "query_timeout_seconds": 30,
            "row_limit": 50000,
        }
    ],
    "semantic_metrics": [
        {
            "term": "doanh thu thuan",
            "aliases": ["net revenue", "doanh thu rong"],
            "definition": "Doanh thu sau chiet khau va hang tra lai",
            "formula": "SUM(NET_REVENUE)",
            "aggregation": "sum",
            "owner": "Finance",
            "freshness_rule": "daily",
            "grain": "daily_customer",
            "unit": "VND",
            "dimensions": ["date", "customer", "region", "channel"],
            "source": {
                "data_source": "oracle-finance",
                "schema": "FINANCE_ANALYTICS",
                "table": "F_SALES",
            },
            "joins": [
                {"target": "D_CUSTOMER", "on": "F_SALES.CUSTOMER_ID = D_CUSTOMER.CUSTOMER_ID"},
                {"target": "D_REGION", "on": "F_SALES.REGION_ID = D_REGION.REGION_ID"},
            ],
            "certified_filters": ["TRANSACTION_STATUS = 'POSTED'", "IS_DELETED = 0"],
            "security": {
                "sensitivity_tier": 1,
                "allowed_roles": ["finance_analyst", "admin"],
            },
        }
    ],
    "role_mappings": [
        {
            "name": "finance_analyst",
            "description": "Finance analyst with access to finance metrics",
            "schema_allowlist": ["FINANCE_ANALYTICS", "COMMON_DIM"],
            "data_source_names": ["oracle-finance"],
            "metric_allowlist": ["doanh thu thuan"],
        }
    ],
}
