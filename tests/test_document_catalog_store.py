from __future__ import annotations

from datetime import date

from aial_shared.auth.keycloak import JWTClaims
from orchestration.persistence.document_catalog_store import DocumentCatalogStore


def _claims(*, department: str, roles: tuple[str, ...], clearance: int) -> JWTClaims:
    return JWTClaims(
        sub=f"{department}-user",
        email=f"{department}@aial.local",
        department=department,
        roles=roles,
        clearance=clearance,
        raw={},
    )


def test_filter_accessible_documents_requires_department_role_and_clearance() -> None:
    store = DocumentCatalogStore(dsn=None)
    store.save_document(
        document_id="doc-1",
        filename="policy.txt",
        source_url="",
        owner_department="sales",
        allowed_departments=["sales", "finance"],
        allowed_roles=["user", "manager"],
        visibility="restricted",
        classification=1,
        source_trust="internal",
        effective_date=date(2026, 5, 1),
        chunk_count=4,
        status="indexed",
        uploaded_by="admin",
        indexed_at=None,
    )

    sales_user = _claims(department="sales", roles=("user",), clearance=1)
    finance_manager = _claims(department="finance", roles=("manager",), clearance=2)
    engineering_user = _claims(department="engineering", roles=("user",), clearance=3)
    sales_guest = _claims(department="sales", roles=("guest",), clearance=3)
    sales_low_clearance = _claims(department="sales", roles=("user",), clearance=0)

    assert store.filter_accessible_documents(["doc-1"], sales_user) == {"doc-1"}
    assert store.filter_accessible_documents(["doc-1"], finance_manager) == {"doc-1"}
    assert store.filter_accessible_documents(["doc-1"], engineering_user) == set()
    assert store.filter_accessible_documents(["doc-1"], sales_guest) == set()
    assert store.filter_accessible_documents(["doc-1"], sales_low_clearance) == set()


def test_company_wide_document_ignores_department_but_respects_status() -> None:
    store = DocumentCatalogStore(dsn=None)
    store.save_document(
        document_id="doc-2",
        filename="handbook.txt",
        source_url="",
        owner_department="hr",
        allowed_departments=[],
        allowed_roles=[],
        visibility="company-wide",
        classification=1,
        source_trust="internal",
        effective_date=date(2026, 5, 1),
        chunk_count=2,
        status="indexed",
        uploaded_by="admin",
        indexed_at=None,
    )
    store.save_document(
        document_id="doc-3",
        filename="obsolete.txt",
        source_url="",
        owner_department="hr",
        allowed_departments=["hr"],
        allowed_roles=[],
        visibility="restricted",
        classification=1,
        source_trust="internal",
        effective_date=date(2026, 5, 1),
        chunk_count=2,
        status="deleted",
        uploaded_by="admin",
        indexed_at=None,
    )

    principal = _claims(department="engineering", roles=("user",), clearance=1)

    assert store.filter_accessible_documents(["doc-2", "doc-3"], principal) == {"doc-2"}
