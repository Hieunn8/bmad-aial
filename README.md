# AIAL

Monorepo cho hệ thống trợ lý dữ liệu doanh nghiệp gồm frontend chat/workspace, backend orchestration, auth/gateway, observability, semantic/memory/export, và các module RAG hỗ trợ.

Nếu bạn mới bắt đầu, đọc theo thứ tự này:

1. [Tổng quan trạng thái hệ thống](docs/system-status.md)
2. [Hướng dẫn cài đặt và chạy local](docs/setup-local.md)
3. [Hướng dẫn sử dụng](docs/user-guide.md)

## Thành phần chính

- `apps/chat`: frontend React + Vite.
- `services/orchestration`: FastAPI backend chính.
- `services/rag`: ingestion, retrieval, composition cho tài liệu.
- `services/data_connector`: connector Oracle VPD.
- `packages/types`: shared API contract cho frontend.
- `packages/ui`: shared UI components.
- `infra`: docker compose, Kong, Keycloak, Cerbos, observability.

## Lưu ý quan trọng

Repo hiện chạy được local dev và demo được khá nhiều luồng nghiệp vụ, nhưng chưa phải trạng thái production-complete. Một số phần vẫn đang dùng stub hoặc in-memory store. Chi tiết xem tại [docs/system-status.md](docs/system-status.md).
