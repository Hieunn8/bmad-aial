"""Tests for Story 4.3 — PII Masking with Presidio (FR-A5)."""

from __future__ import annotations

import pytest

from orchestration.security.pii_masker import (
    PiiMasker,
    PiiScanResult,
    SanitizedLogger,
)


class TestPiiMasker:
    @pytest.fixture()
    def masker(self) -> PiiMasker:
        return PiiMasker()

    def test_masks_person_name(self, masker: PiiMasker) -> None:
        result = masker.mask_text("Nguyễn Văn An là trưởng phòng")
        assert "<TÊN_ĐƯỢC_ẨN>" in result.text or result.entities_found

    def test_masks_email_address(self, masker: PiiMasker) -> None:
        result = masker.mask_text("Liên hệ qua email: user@company.com")
        assert "user@company.com" not in result.text
        assert "<EMAIL_ĐƯỢC_ẨN>" in result.text or "EMAIL" in str(result.entities_found)

    def test_masks_phone_number(self, masker: PiiMasker) -> None:
        result = masker.mask_text("Số điện thoại: 0912345678")
        assert "0912345678" not in result.text

    def test_inline_scan_for_small_result(self, masker: PiiMasker) -> None:
        """≤10,000 cells → inline synchronous scan."""
        rows = [{"notes": "Contact Hùng at hung@test.com"} for _ in range(10)]
        scan = masker.scan_rows(rows, free_text_columns=["notes"], user_clearance=1)
        assert scan.mode == "inline"
        for row in scan.rows:
            assert "hung@test.com" not in str(row)

    def test_async_scan_for_large_result(self, masker: PiiMasker) -> None:
        """>10,000 cells → async stub, returns scan_id."""
        rows = [{"notes": f"Name {i}"} for i in range(5001)]  # 5001 * 2 col > 10,000
        scan = masker.scan_rows(rows, free_text_columns=["notes", "comment"], user_clearance=1)
        assert scan.mode == "async"
        assert scan.scan_id is not None

    def test_clearance_3_bypasses_masking(self, masker: PiiMasker) -> None:
        result = masker.mask_text("Email: admin@aial.local", user_clearance=3)
        assert "admin@aial.local" in result.text  # unmasked for clearance ≥ 3

    def test_audit_never_stores_pii_values(self, masker: PiiMasker) -> None:
        result = masker.mask_text("Gọi cho Minh: 0987654321")
        audit = result.to_audit_dict()
        assert "0987654321" not in str(audit)
        assert "Minh" not in str(audit)
        assert "masked_count" in audit or "entities_found" in str(audit)


class TestSanitizedLogger:
    def test_strips_pii_before_logging(self) -> None:
        logged: list[str] = []
        logger = SanitizedLogger(sink=logged.append)
        logger.log("Processing user email: test@pii.com")
        assert len(logged) == 1
        assert "test@pii.com" not in logged[0]

    def test_safe_messages_pass_through(self) -> None:
        logged: list[str] = []
        logger = SanitizedLogger(sink=logged.append)
        logger.log("Query processed in 150ms")
        assert "150ms" in logged[0]
