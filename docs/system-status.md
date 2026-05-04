# Trạng thái hệ thống

Tài liệu này trả lời câu hỏi ngắn nhất trước:

**Hiện tại chưa nên coi là "full tính năng production-ready".**

**Có thể chạy được local dev end-to-end cho phần lớn luồng UI/backend chính.**

**Một số tính năng vẫn đang là stub, fallback hoặc in-memory.**

## 1. Có thể chạy full tính năng chưa?

Nếu "full tính năng" nghĩa là:

- frontend mở được đầy đủ workspace
- backend trả được API cho các màn hình chính
- auth/gateway/observability/local infra dựng được
- query stream, export, forecast, anomaly, trend, explainability, memory, admin, document ingestion đều có endpoint và UI tương ứng

thì câu trả lời là: **có thể chạy được phần lớn local flow**.

Nếu "full tính năng" nghĩa là:

- truy vấn thật vào data warehouse/Oracle production
- semantic layer thật gắn với metric catalog thật
- ingestion/reindex chạy qua queue worker thật
- audit/read model và job state lưu DB bền vững
- explainability/forecast dùng provider thật và dữ liệu thật
- phân quyền, directory sync, semantic governance, export, documents đều ở trạng thái production-hardening

thì câu trả lời là: **chưa**.

## 2. Những gì đang chạy được

### Frontend

App chính là `apps/chat`, route mặc định render `Epic5BWorkspace`.

Workspace hiện ghép các khu vực sau:

- Semantic studio / memory studio / history studio
- Export studio
- Forecast studio
- Anomaly alerts
- Trend analysis
- Drilldown explainability
- Login / callback với Keycloak

### Backend orchestration

Service chính là `services/orchestration`.

Các nhóm API hiện có:

- `POST /v1/chat/query`
- `GET /v1/chat/stream/{request_id}`
- `GET /v1/chat/query/{request_id}/sql-explanation`
- export preview / export job / export status / download
- forecast run / status / result / download
- anomaly detection
- trend analysis
- drilldown explainability
- memory / preferences / suggestions / templates / history
- onboarding role preference
- glossary
- scheduled reports
- admin roles/users/data sources/system health/audit/semantic layer
- admin documents upload/list/detail/delete/reindex status

### Hạ tầng local

`infra/docker-compose.dev.yml` dựng được:

- Vault
- Postgres
- Redis
- Keycloak
- Cerbos
- Kong
- Weaviate
- OTel Collector
- Tempo
- Prometheus
- Grafana
- Oracle Free theo profile tùy chọn
- Langfuse theo profile tùy chọn

## 3. Những phần còn stub hoặc in-memory

Đây là phần quan trọng nhất để đặt kỳ vọng đúng.

### Query graph

`services/orchestration/graph/nodes/stub_response.py` vẫn là walking skeleton node.

Điều đó có nghĩa:

- câu trả lời query thường là stub có điều kiện
- SQL sinh ra vẫn là giả lập hoặc skeleton
- chưa phải query engine thật tới warehouse

### Cross-domain query

`services/orchestration/cross_domain/service.py` đang merge dữ liệu mẫu cứng cho luồng FINANCE/BUDGET.

Điều đó có nghĩa:

- UI conflict/provenance chạy được
- nhưng chưa nối vào nguồn dữ liệu nghiệp vụ thật

### Forecast

`services/orchestration/forecasting/service.py` đang chạy job/service in-memory.

- có trả status/result/download
- có mô phỏng provider TimeGPT hoặc fallback
- nhưng dữ liệu forecast hiện là dữ liệu dựng sẵn

### Document ingestion / reindex

`services/rag/tasks/ingest.py` đang mô phỏng queue worker và đánh dấu thành công ngay.

- upload document, chunking, status flow chạy được
- chưa có Celery worker/queue thật
- job state chưa persist ở DB thật

### Audit / jobs / cache

Một số read model và job registry vẫn là in-memory hoặc fallback:

- audit read model
- ingest job registry
- một số graph/checkpoint/cache fallback

### Explainability / RAG composition

Một số phần đang là rule-based hoặc fallback thay vì provider thật.

## 4. Kết luận thực tế

Hiện trạng phù hợp nhất với:

- local development
- demo nội bộ
- kiểm thử UI/API flow
- validate kiến trúc
- phát triển tiếp story/epic

Hiện trạng **chưa đủ** để kết luận:

- production ready
- data-ready
- compliance-ready
- fully integrated với schema nghiệp vụ thật

## 5. Thông tin còn thiếu nếu muốn đi tới "full tính năng thật"

Nếu mục tiêu là chạy đủ nghiệp vụ thật, bạn cần bổ sung ít nhất:

- thông tin database thật:
  - loại DB
  - host/port
  - schema
  - table
  - view
  - account / quyền truy cập
- semantic layer thật:
  - danh sách metric
  - công thức
  - dimension
  - grain
  - freshness rule
- auth thật:
  - realm/client/user test
  - role mapping
  - sample account cho admin / user / data owner
- sample dữ liệu:
  - câu hỏi mẫu
  - expected result
  - dataset cho forecast / anomaly / explainability
- tài liệu policy:
  - sensitivity tiers
  - masking rules
  - approval rules
  - Cerbos policy mapping
- nếu muốn triển khai:
  - môi trường target
  - domain / TLS
  - secrets management
  - logging / tracing / backup
