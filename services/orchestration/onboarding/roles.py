"""User role definitions and query placeholder mapping (Story 2A.9, UX-DR26a)."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    REPORTING = "reporting"   # 📅 Báo cáo định kỳ
    ANSWERING = "answering"   # ⚡ Trả lời câu hỏi từ sếp
    ANALYSIS = "analysis"     # 🔍 Phân tích chuyên sâu


ROLE_PLACEHOLDERS: dict[UserRole, str] = {
    UserRole.REPORTING: "VD: Doanh thu chi nhánh HCM tháng này?",
    UserRole.ANSWERING: "VD: Tổng đơn hàng quý 1 so với cùng kỳ năm ngoái?",
    UserRole.ANALYSIS: "VD: Phân tích xu hướng doanh thu 6 tháng gần nhất theo kênh?",
}

ROLE_INTENT_HINTS: dict[UserRole, str] = {
    UserRole.REPORTING: "AIAL sẽ dùng dữ liệu từ SALES domain",
    UserRole.ANSWERING: "AIAL sẽ tổng hợp dữ liệu từ nhiều domain",
    UserRole.ANALYSIS: "AIAL sẽ phân tích dữ liệu lịch sử chi tiết",
}

ROLE_SUGGESTED_QUERIES: dict[UserRole, str] = {
    UserRole.REPORTING: "Doanh thu tháng trước theo chi nhánh là bao nhiêu?",
    UserRole.ANSWERING: "So sánh doanh thu quý này với quý trước như thế nào?",
    UserRole.ANALYSIS: "Xu hướng tăng trưởng doanh thu 12 tháng qua là gì?",
}


def get_role_placeholder(role: UserRole, *, department: str = "") -> str:
    return ROLE_PLACEHOLDERS.get(role, "Nhập câu hỏi của bạn...")
