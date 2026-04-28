---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-ai-safety
  - step-12-polish
  - step-13-party-review
  - step-14-complete
date: '2026-04-23'
inputDocuments:
  - _bmad-output/planning-artifacts/research/enterprise-ai-chatbot-working-checklist-2026-04-22.md
  - _bmad-output/planning-artifacts/research/enterprise-ai-chatbot-decision-memo-2026-04-22.md
  - _bmad-output/planning-artifacts/research/technical-ai-chatbot-noi-bo-doanh-nghiep-research-2026-04-22.md
  - requirement.txt
documentCounts:
  briefCount: 0
  researchCount: 3
  brainstormingCount: 0
  projectDocsCount: 2
classification:
  projectType: SaaS B2B / Enterprise AI Platform
  domain: Enterprise Data Intelligence
  complexity: High
  projectContext: Brownfield
workflowType: 'prd'
revision: '2.1 — Post-Validation Fixes Applied'
---

# Product Requirements Document
# Enterprise AI Data Assistant — Hệ Thống AI Chatbot Nội Bộ Doanh Nghiệp

**Phiên bản:** 2.1  
**Ngày cập nhật:** 2026-04-23  
**Tác giả:** Admin  
**Trạng thái:** Draft — Chờ sign-off sau party review  

---

## Executive Summary

Hệ thống **Enterprise AI Data Assistant** là một **nền tảng truy cập dữ liệu doanh nghiệp có governance dành cho AI** — không phải đơn thuần là một chatbot. Hệ thống cho phép người dùng truy vấn dữ liệu nghiệp vụ bằng ngôn ngữ tự nhiên, kết hợp **Text-to-SQL qua Semantic Layer** (dữ liệu Oracle) và **RAG** (tài liệu nội bộ), đảm bảo an toàn tuyệt đối thông qua policy-enforced retrieval và audit toàn diện.

### Giá trị cốt lõi

| Giá trị | Mô tả |
|---------|-------|
| **Verified Truth** | Mọi câu trả lời đều kèm SQL gốc, nguồn trích dẫn, và logic tính toán |
| **Deep Governance** | RBAC/ABAC + Row/Column-level security tại Oracle + policy-first retrieval |
| **Sovereign AI** | Kiến trúc modular, sẵn sàng chuyển OpenAI → Local LLM khi cần |
| **Auditable by Design** | 100% tương tác được ghi log, truy vết, và kiểm duyệt |

### Vị thế chiến lược

Hệ thống này không phải chatbot hỏi đáp Oracle — đây là lớp truy cập dữ liệu có governance, cho phép toàn bộ doanh nghiệp ra quyết định dựa trên dữ liệu mà không cần phụ thuộc vào đội IT/Data cho từng báo cáo.

---

## Project Classification

| Thuộc tính | Giá trị |
|-----------|---------|
| Project Type | SaaS B2B / Enterprise AI Platform |
| Domain | Enterprise Data Intelligence |
| Complexity | High |
| Project Context | Brownfield (tích hợp vào hạ tầng Oracle hiện tại) |

---

## Success Criteria

### 1. User Success (Đo lường sau 90 ngày production)

| Tiêu chí | Mục tiêu | Baseline | Cách đo |
|----------|----------|----------|---------|
| Thời gian phản hồi câu hỏi đơn | P50 < 5s / P95 < 12s | Không có (hiện manual) | End-to-end latency tracing |
| Tỷ lệ câu hỏi có kết quả hữu ích | > 85% (user vote thumbs-up) | Không có | Feedback button trong UI |
| Giảm thời gian chờ báo cáo IT | > 60% trong 30 ngày đầu | Đo baseline trước launch | Ticket count IT/Data |
| Tỷ lệ người dùng active hàng tuần | > 40% active user / WAU | 0 | Analytics dashboard |

### 2. Business & Technical Success (Đo lường liên tục)

| Tiêu chí | Mục tiêu | Cách đo |
|----------|----------|---------|
| Sự cố rò rỉ dữ liệu | 0 incidents | Audit log + Security review hàng tháng |
| Tỷ lệ truy vấn được audit đầy đủ | 100% | Audit completeness check |
| Text-to-SQL accuracy trong Semantic Layer scope | > 90% | Eval set 100 câu hỏi chuẩn |
| Leo thang đặc quyền qua hội thoại | 0 incidents | Security regression test |
| Thời gian chuyển đổi Local LLM (Phase 2) | Sụt giảm accuracy < 5% | Benchmark eval set |

### 3. Điều kiện thành công (Non-negotiable)

- Có business owner, data owner, security owner, engineering owner được chỉ định rõ
- Bắt đầu hẹp: top 20–50 business questions, top 10–20 KPI tier-0
- Semantic layer phải được data team sở hữu và maintain, không để AI tự phát minh metric logic
- Đo hiệu quả theo adoption, answer quality, latency, auditability — không chỉ demo

---

## Stakeholders

| Vai trò | Mô tả | Quyền lợi chính |
|---------|-------|----------------|
| Business User (Sales, Finance, Ops, HR) | Người hỏi câu hỏi hàng ngày | Tự phục vụ dữ liệu, không chờ IT |
| IT Admin | Cấu hình hệ thống, phân quyền | Kiểm soát an toàn, audit dễ dàng |
| Data Owner | Quản lý Semantic Layer, metadata | Đảm bảo định nghĩa KPI chính xác |
| Security Officer | Giám sát bảo mật | Zero data leakage, PDPA compliance |
| C-Suite / Management | Ra quyết định chiến lược | Báo cáo nhanh, đáng tin cậy |
| Compliance Officer | Đảm bảo tuân thủ | Audit trail đầy đủ, không lộ PII |

---

## User Journeys

### Journey 1 — Trưởng phòng Sales (Minh)

**Ngữ cảnh:** Họp giao ban lúc 8h, Minh cần so sánh doanh thu các chi nhánh và lý do sụt giảm.

**Luồng:**
1. Minh đăng nhập bằng LDAP (SSO), hệ thống load đúng scope dữ liệu Sales của Minh
2. Minh hỏi: *"Doanh thu chi nhánh HCM tháng 3/2026 so với tháng 3/2025 thay đổi thế nào?"*
3. Hệ thống phân loại ý định → SQL mode → query Oracle Sales DB qua Semantic Layer
4. Trả về bảng số liệu + biểu đồ + giải thích SQL bằng tiếng Việt
5. Minh hỏi tiếp: *"Vì sao giảm?"* → Hybrid mode: kết hợp SQL (số liệu) + RAG (biên bản họp, báo cáo thị trường)
6. Minh xuất file PDF để trình bày trong 3 phút

**Acceptance:** Toàn bộ trong < 8 phút, dữ liệu chỉ thuộc chi nhánh Minh được phép xem

---

### Journey 2 — IT Admin (Lan)

**Ngữ cảnh:** Lan cần onboard phòng Finance vào hệ thống.

**Luồng:**
1. Lan vào Admin Portal → tạo role `finance_analyst`, gán schema `FINANCE_ANALYTICS`, whitelist bảng được phép
2. Lan upload business glossary cho Finance (định nghĩa "doanh thu thuần", "EBITDA")
3. Lan theo dõi Audit Log — xem ai hỏi gì, SQL nào được sinh, dữ liệu nào được trả về
4. Lan phát hiện một query của user cố tình gọi bảng `HR_SALARY` — hệ thống đã block, ghi log → Lan nhận alert

---

### Journey 3 — Trưởng phòng Finance (Tuấn)

**Ngữ cảnh:** Tuấn cần báo cáo chi phí vs doanh thu theo quý để họp HĐQT.

**Luồng:**
1. Tuấn hỏi: *"Chi phí vận hành Q1/2026 so với ngân sách?"*
2. Hệ thống decompose: query `FINANCE_ANALYTICS` (chi phí thực) + `BUDGET_DB` (ngân sách) → merge tại application layer
3. Tuấn yêu cầu xuất Excel → hệ thống tạo async job, gửi link download sau 2 phút
4. Hệ thống log: ai export gì, khi nào, dữ liệu gì

---

### Journey 4 — HR Manager (Hoa)

**Ngữ cảnh:** Hoa muốn phân tích tỷ lệ nghỉ việc theo phòng ban.

**Luồng:**
1. Hoa hỏi về tỷ lệ turnover → Hệ thống chỉ query schema HR được phép, mask toàn bộ thông tin cá nhân (tên, lương) trong kết quả
2. Hoa hỏi về dự báo nhân sự quý tới → Forecast mode: dùng Time-series model → kết quả kèm confidence interval và giải thích bằng tiếng Việt

---

### Journey 5 — Data Owner (Nam)

**Ngữ cảnh:** Nam cần cập nhật định nghĩa KPI "doanh thu thuần" vì quy tắc tính toán thay đổi.

**Luồng:**
1. Nam vào Semantic Layer Admin → cập nhật metric definition với version mới
2. Hệ thống invalidate cache liên quan, ghi changelog
3. Từ lần hỏi tiếp theo, tất cả user nhận kết quả theo logic KPI mới

---

### Journey 6 — Approval Officer / Data Steward (Hùng)

**Ngữ cảnh:** Một Finance Analyst submit query có sensitivity_tier = 2 (liên quan đến margin theo sản phẩm) — cần approval trước khi execute.

**Luồng:**
1. Finance Analyst gửi câu hỏi → hệ thống detect sensitivity_tier >= 2 → tạo approval request, trả về thông báo "Câu hỏi này đang chờ phê duyệt"
2. Hùng (Data Steward) nhận notification qua email + Admin Portal → xem nội dung câu hỏi, SQL được sinh, dữ liệu sẽ được access
3. Hùng approve hoặc reject với lý do trong < 4 giờ (SLA)
4. Nếu approve: query được execute, kết quả trả về Finance Analyst; toàn bộ flow được audit log
5. Nếu reject: Finance Analyst nhận thông báo lý do từ chối; không có dữ liệu nào được trả về

**Acceptance:** 100% sensitive queries không thể bypass approval gate; mọi quyết định approve/reject đều có audit entry

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│  Chat UI (User)  │  Admin Portal (IT/Data)  │  API Consumers    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       GATEWAY LAYER                             │
│  Kong API Gateway (Auth, Rate Limit, Tracing, Routing)          │
│  Keycloak IdP (LDAP/AD, OIDC, JWT)                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   AI ORCHESTRATION LAYER                        │
│  LangGraph (Intent Router, Multi-step Agent, Mode Dispatcher)   │
│  Policy Check: Cerbos (ABAC pre-retrieval enforcement)          │
└───────┬──────────────┬──────────────┬──────────────┬────────────┘
        │              │              │              │
┌───────▼──┐  ┌────────▼────┐  ┌─────▼──────┐  ┌──▼──────────────┐
│ SEMANTIC │  │   RAG       │  │  FORECAST  │  │ MEMORY / CACHE  │
│  LAYER   │  │  SERVICE    │  │  SERVICE   │  │   SERVICE       │
│(Cube.dev)│  │(LlamaIndex) │  │  (Nixtla)  │  │(Redis/PgSQL)    │
└───────┬──┘  └────────┬────┘  └─────┬──────┘  └──────────────────┘
        │              │              │
┌───────▼──────────────▼──────────────▼─────────────────────────┐
│                    DATA ACCESS LAYER                           │
│  Oracle Connector Gateway (read-only, AST validation, audit)  │
│  Oracle DB (VPD, RLS, SQL Firewall, True Cache)               │
│  Weaviate Vector Store (self-hosted, network-isolated)        │
│  PostgreSQL (Metadata, Audit Store, Memory)                   │
│  Redis (Session cache, Rate limiting, Result cache)           │
└────────────────────────────────────────────────────────────────┘
```

**4 nguyên tắc kiến trúc bất biến:**
1. **API-first** — không component nào gọi Oracle trực tiếp, mọi thứ qua Connector Gateway
2. **Semantic-layer-first** — LLM không nhìn thấy raw schema; chỉ thấy business entities từ Semantic Layer
3. **Policy-enforced retrieval** — policy engine check TRƯỚC khi fetch dữ liệu, không phải sau
4. **Decomposed multi-domain** — cross-DB queries được tách thành nhiều single-domain queries, merge tại application layer

---

## Functional Requirements

### Module 1 — Agent Orchestration

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-O1 | Intent Classification: phân loại câu hỏi thành mode `sql`, `rag`, `hybrid`, `forecast`, `fallback` | Accuracy > 95% trên test set 200 câu; fallback khi confidence < threshold |
| FR-O2 | Multi-turn Context: duy trì ngữ cảnh hội thoại trong session | Câu hỏi follow-up được hiểu đúng ngữ cảnh trong cùng session |
| FR-O3 | Contextual Security Guardrails: session memory bị giới hạn theo user_id + department_id; không thể inject context của user khác | Test: user A không thể trigger dữ liệu từ session của user B |
| FR-O4 | Multi-turn Privilege Escalation Prevention: phát hiện và chặn pattern hỏi nhiều turns để dần dần mở rộng phạm vi dữ liệu | Policy check được thực hiện độc lập tại mỗi turn, không tích lũy quyền |
| FR-O5 | Natural Language SQL Explanation: giải thích SQL được sinh và nguồn dữ liệu bằng tiếng Việt | Mọi câu trả lời SQL đều có thể expand xem SQL + logic giải thích |

### Module 2 — Text-to-SQL & Semantic Layer

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-S1 | Semantic Layer là trung gian bắt buộc: LLM chỉ nhận business entities từ Semantic Layer, không nhìn thấy raw Oracle schema | LLM prompt không chứa tên bảng vật lý; chỉ chứa metric/dimension definitions |
| FR-S2 | Metadata Catalog & Business Glossary: catalog ánh xạ business terms → metric definition → technical columns/views | Có thể tìm kiếm glossary; mỗi metric có owner, formula, freshness rule |
| FR-S3 | SQL Whitelist & AST Validation: chỉ cho phép `SELECT`; SQL được parse qua AST checker trước khi execute | Block: `DROP`, `INSERT`, `UPDATE`, `EXEC`, subquery vòng lặp, Cartesian joins, cross-DB links |
| FR-S4 | Query Governor: giới hạn row count, timeout, query cost | Default: max 50,000 rows, timeout 30s, cấm full table scan trên bảng > 1M rows nếu không có partition predicate |
| FR-S5 | Cross-domain Query Decomposition: câu hỏi multi-domain được tách thành nhiều single-domain queries, merge tại application layer | Test: câu hỏi cross-schema trả đúng kết quả và không expose schema chéo; implementation production chỉ bắt đầu sau spike định nghĩa `QueryDecompositionState`, horizontal/vertical strategies, và merge patterns |
| FR-S6 | Query Result Cache: cache semantic results theo normalized intent + role scope | Cache hit rate > 40% cho câu hỏi phổ biến sau 2 tuần vận hành |

### Module 3 — RAG & Document Management

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-R1 | Document Ingestion Pipeline: hỗ trợ PDF, DOCX, XLSX, TXT; tự động parse → chunk → embed → index | Upload xong trong 5 phút cho file < 100 trang |
| FR-R2 | Pre-retrieval Policy Filtering: policy engine filter đúng department/classification TRƯỚC khi vector search | User phòng Sales không nhận chunks từ tài liệu phòng HR dù query overlap |
| FR-R3 | Citation & Source Attribution: mọi câu trả lời RAG đều trích dẫn tên tài liệu, trang, đoạn cụ thể | Kiểm tra: citation dẫn đến đúng đoạn văn gốc |
| FR-R4 | Document Access Control: mỗi document được gán `department`, `classification`, `effective_date`, `source_trust` | Upload không thể bỏ qua metadata tagging |
| FR-R5 | Admin Upload & Management: IT/Data Owner có thể upload, edit metadata, xóa, re-index tài liệu qua Admin Portal | CRUD operations với audit log |

### Module 4 — Security & Access Control (CRITICAL)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-A1 | LDAP/Active Directory Integration: đăng nhập SSO qua Keycloak + LDAP; user không cần tài khoản riêng | SSO hoạt động với LDAP/AD doanh nghiệp; JWT hợp lệ < 1s |
| FR-A2 | RBAC + ABAC Policy Engine: phân quyền dựa trên role + attributes (department, region, clearance, purpose) | Baseline Phase 1 khóa `principal.attr` tối thiểu với `department` và `clearance`; Epic sau chỉ được mở rộng, không backfill JWT mapping; ABAC policy enforce đúng khi user có role nhưng sai region/department |
| FR-A3 | Row-level Security (Oracle VPD): LLM không thể bypass RLS tại DB layer dù SQL bị inject | Test: SQL bypass attempt vẫn bị Oracle VPD chặn tại DB layer |
| FR-A4 | Column-level Security: các cột nhạy cảm (lương, margin, PII) không trả về cho user không có quyền | Test: query trả về `***` hoặc loại bỏ cột thay vì error message chứa giá trị |
| FR-A5 | Data Masking & PII Redaction: kết quả được scan qua Presidio trước khi trả về; PII bị mask theo policy | Test: CMND, họ tên, email không xuất hiện raw trong kết quả của user không có clearance |
| FR-A6 | Identity Passthrough: mọi Oracle query phải mang identity của user thực, không dùng shared DBA account | Audit log Oracle chứa đúng user_id, không phải service account |
| FR-A7 | Query Approval Workflow: queries thuộc sensitive_tier >= 2 yêu cầu approval từ Data Owner trước khi execute | Workflow: submit → notify approver → approve/reject → execute/cancel; SLA approve < 4h |
| FR-A8 | Comprehensive Audit Log: ghi đầy đủ (who, what question, when, what intent, what SQL, what sources, what result, what policy applied) | 100% requests có audit entry; log immutable (append-only); retention tối thiểu 12 tháng |

### Module 5 — Session Memory & Conversation History

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-M1 | Short-term Memory (in-session): lưu ngữ cảnh hội thoại hiện tại trong Redis TTL 24h | Câu hỏi "nó" / "cái đó" trong cùng session được resolve đúng |
| FR-M2 | Medium-term Memory (cross-session): lưu summary của 30 sessions gần nhất; không lưu raw data | Summary không chứa raw dữ liệu Oracle; chỉ chứa business terms và filter context |
| FR-M3 | Long-term Memory / User Preference: lưu báo cáo hay dùng, bộ lọc phổ biến, KPI yêu thích | Khi user mở session mới, hệ thống hiển thị top 3 KPI/báo cáo được dùng nhiều nhất trong 30 ngày qua |
| FR-M4 | Memory Isolation: memory của user A không thể bị user B đọc dù cùng phòng ban | Test: không có shared memory path giữa user khác nhau |
| FR-M5 | Selective Context Injection: chỉ inject relevant history vào context, không inject toàn bộ | Token usage per session tăng < 20% sau mỗi 10 turns nhờ memory compaction; đo bằng LLM observability dashboard |
| FR-M6 | Conversation History Search: user có thể tìm lại câu hỏi cũ theo keyword, time range, topic | Search history trong < 2s |
| FR-M7 | Memory không lưu raw dữ liệu nhạy cảm: chỉ lưu business intent, không lưu giá trị số cụ thể từ Oracle | Audit: memory store không chứa raw Oracle data |

### Module 6 — Forecasting & Advanced Analytics

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-F1 | Time-series Forecasting: dự báo số liệu theo ngày/tuần/tháng/quý cho các KPI tier-0 | Kết quả kèm confidence interval; MAPE < 15% trên validation set |
| FR-F2 | Anomaly Detection: phát hiện bất thường trong time-series và alert cho user có quyền | Alert trong < 1 giờ sau khi dữ liệu cập nhật; false positive rate < 10% |
| FR-F3 | Trend Analysis: phân tích xu hướng tăng/giảm, so sánh cùng kỳ (YoY, MoM, QoQ) | Kết quả kèm giải thích không chứa thuật ngữ thống kê/ML; diễn giải được bởi người dùng không có background phân tích số liệu; validatable qua user acceptance test |
| FR-F4 | Drill-down Analytics: phân tích theo phòng ban, sản phẩm, khu vực, kênh bán | Drill-down hoạt động đúng theo phân quyền; user chỉ thấy chiều phân tích thuộc quyền |
| FR-F5 | Result Explainability: giải thích kết quả dự báo bằng ngôn ngữ tự nhiên kèm top 3 yếu tố đóng góp | Kết quả không chứa thuật ngữ kỹ thuật ML; confidence level diễn đạt bằng ngôn ngữ thông thường (ví dụ: "có khả năng tăng", "khả năng cao giảm"); validatable qua user acceptance test |
| FR-F6 | Async Forecast Jobs: forecast nặng chạy async, không block chat UI | Forecast request trả về job_id ngay; kết quả notify khi xong |

### Module 7 — Export & Reporting

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-E1 | Export kết quả: hỗ trợ xuất bảng → Excel, PDF, CSV | Export chuẩn xác; không có dữ liệu ngoài phạm vi quyền trong file |
| FR-E2 | Scheduled Reports: báo cáo định kỳ (daily/weekly/monthly) tự động gửi qua email | Đúng người nhận; có audit log mỗi lần gửi; cơ chế xác nhận người nhận |
| FR-E3 | Export Authorization: export file yêu cầu approval nếu chứa sensitive data | Không thể export past approval gate nếu data sensitivity >= tier 2 |
| FR-E4 | Export Audit: mọi file export được ghi log (ai export, khi nào, dữ liệu gì, gửi cho ai) | 100% export events có audit entry |

### Module 8 — Administration

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-AD1 | Semantic Layer Management: Data Owner quản lý metric definitions, business glossary, version history qua UI | Có diff view giữa versions; rollback được trong 1 click |
| FR-AD2 | User & Role Management: IT Admin quản lý users, roles, phân quyền tài liệu/schema | CRUD user/role với audit; sync với LDAP |
| FR-AD3 | Data Source Configuration: cấu hình Oracle connections, schema allowlist, timeout, row limits | Cấu hình không expose credentials trong UI |
| FR-AD4 | Audit Dashboard: xem audit log với filter (user, time, action, data source, policy decision) | Tìm kiếm log trong < 3s |
| FR-AD5 | System Health Dashboard: xem latency, cache hit ratio, error rate, token usage, query throughput | Metrics cập nhật mỗi 30 giây; alert gửi trong < 2 phút sau khi threshold bị vi phạm |

---

## Non-Functional Requirements

### 1. Performance SLOs

| Workload | P50 Target | P95 Target | Ghi chú |
|----------|------------|------------|---------|
| Intent classification / routing | < 300ms | < 700ms | Không gọi DB nặng |
| Single-domain SQL Q&A | < 3s | < 8s | Đã cache metadata |
| Hybrid SQL + RAG | < 5s | < 12s | Có retrieval + synthesis |
| Cross-domain decomposed query | < 8s | < 20s | Multi-step orchestration |
| Forecast summary (interactive) | < 10s | < 30s | Chỉ summary; heavy jobs async |
| Export / Report generation | Async (< 5 phút) | Async | Trả job_id ngay; notify khi xong |

**Concurrency:** 100 concurrent users Phase 1; 500 users Phase 3.

### 2. Security

| Requirement | Spec |
|-------------|------|
| Encryption at rest | AES-256 cho PostgreSQL, Redis, Vector Store |
| Encryption in transit | TLS 1.3 bắt buộc; không accept TLS 1.2 |
| Secret management | HashiCorp Vault là baseline; local/dev dùng Vault dev mode, staging/prod dùng Vault-integrated secret delivery; không hardcode |
| Audit log integrity | Append-only store; log không thể sửa sau khi ghi |
| Session token | JWT với expiry 8h; refresh token rotation |
| Network isolation | Database layer không expose public; chỉ accessible từ Connector Gateway |
| Compliance | PDPA (Vietnam); không lưu PII thô trong memory/log |

### 3. High Availability & Disaster Recovery

| Requirement | Spec |
|-------------|------|
| Uptime SLA | 99.5% (Production) |
| RTO (Recovery Time Objective) | < 4 giờ |
| RPO (Recovery Point Objective) | < 1 giờ |
| Backup | PostgreSQL: daily snapshot + WAL streaming; Redis: AOF; Weaviate: daily backup |
| Failover | API/Orchestration: multi-instance behind load balancer; Oracle: read replica failover |
| Multi-region | Không bắt buộc Phase 1; option cho Phase 3 nếu có data residency requirement |

### 4. Scalability

| Requirement | Spec |
|-------------|------|
| Horizontal scaling | Orchestration + API nodes scale-out stateless |
| Workload isolation | Tách pool riêng: `chat-low-latency`, `sql-heavy`, `rag-ingestion`, `forecast-batch`, `export-jobs` |
| Oracle read scaling | AI read workloads không query primary OLTP; đi qua read-optimized layer (replica hoặc cache node); xem Technology Stack section |
| Vector search scaling | Weaviate sharding theo department/data domain |

### 5. Observability

| Requirement | Spec |
|-------------|------|
| Distributed tracing | End-to-end trace mọi request từ UI → Orchestrator → DB → Response; xem Technology Stack |
| LLM Observability | Track token usage, latency per model, hallucination signals theo session và per-user; xem Technology Stack |
| Infrastructure metrics | Thu P50/P95/P99 theo từng mode (`sql`, `rag`, `hybrid`, `forecast`); cache hit ratio, error rate, DB wait events |
| Log aggregation | Centralized log aggregation; log retention tối thiểu 12 tháng; xem Technology Stack |
| Alerting | Alert khi P95 > SLO threshold; cache hit < 20%; error rate > 1%; timeout rate > 2% |

### 6. Cost Management

| Requirement | Spec |
|-------------|------|
| Token cost monitoring | Track cost per query, per user, per department |
| Rate limiting | Per-user: 100 queries/day (configurable); per-department: configurable quota |
| Budget alert | Alert khi LLM cost vượt ngưỡng tháng (configurable) |
| Cost optimization | Hierarchical memory (giảm 80-90% token), semantic result cache, async jobs cho heavy workload |

### 7. Maintainability

| Requirement | Spec |
|-------------|------|
| Modular LLM | Chuyển đổi LLM (OpenAI → Local) chỉ qua config; không thay đổi code |
| Semantic Layer versioning | Metric definitions có version; rollback 1-click |
| API versioning | API contract versioned (`/v1/`, `/v2/`); backward compatible |
| Test coverage | > 80% unit test; regression tests cho policy, SQL validation, RAG leakage |

---

## AI Safety & Guardrails

Đây là section bắt buộc cho mọi AI system kết nối production data. Tham chiếu OWASP LLM Top 10 2025.

### Threat Model & Mitigations

| Threat | Mô tả rủi ro | Mitigation |
|--------|-------------|------------|
| **Prompt Injection** (OWASP LLM #1) | User nhúng instruction độc hại vào câu hỏi để override system prompt | Input sanitizer + harden system prompt + separate SYSTEM/USER context; không dùng system prompt là sole control |
| **SQL Injection via LLM** | LLM sinh SQL độc hại do injection vào câu hỏi | AST parser validate SQL trước execute; chỉ allow `SELECT`; Oracle SQL Firewall |
| **Jailbreak** | User bypass guardrails qua roleplay, hypothetical framing | Output scanner + LLM Guard; rate limit jailbreak pattern; monitor repeated bypass attempts |
| **Data Exfiltration** | User crafts queries để extract toàn bộ dataset qua nhiều requests | Row limit per query; rate limit per user; export requires approval; result size monitoring |
| **Multi-turn Privilege Escalation** | Dùng nhiều turns để dần dần mở rộng phạm vi dữ liệu được access | Policy check độc lập tại mỗi turn; không tích lũy permission across turns; session scope cố định |
| **Tool/Function Calling Abuse** | Lạm dụng tool calls để thực hiện actions ngoài phạm vi | Tool catalog tối thiểu (least privilege); validate tool parameters theo session context; block side-effect tools |
| **Hallucination → Wrong Reports** | LLM "bịa" dữ liệu khi không đủ thông tin | Chỉ trả kết quả từ verified SQL/RAG; không cho LLM generate số liệu từ memory; Guardrails AI output validation |
| **Metadata/Schema Poisoning** | Tài liệu độc hại được upload để thay đổi behavior của RAG | Ingestion pipeline validate source trust; chỉ Data Owner mới upload; scan content trước index |
| **Cross-department Data Leakage** | Dữ liệu phòng ban A bị lộ sang phòng ban B qua RAG/memory | Pre-retrieval filtering mandatory; memory isolated by user_id + department_id; cross-session check |
| **Heavy Query Abuse** | User gửi query nặng làm ảnh hưởng Oracle production | Query governor (timeout, row limit, cost ceiling); rate limit; async path cho heavy queries |
| **PII Exposure** | Dữ liệu cá nhân nhạy cảm xuất hiện trong kết quả | Presidio PII detector scan kết quả trước khi trả về; column-level security; data masking |
| **Wrong Export Recipient** | File báo cáo gửi nhầm người | Export requires explicit recipient confirmation; audit log recipient; DLP scan file trước gửi |
| **Sensitive Data in Logs** | Log chứa giá trị nhạy cảm (lương, margin, PII) | Log sanitizer: chỉ log metadata (intent, schema, row count) không log raw data values |
| **Inference from Combined Sources** | LLM suy luận dữ liệu bị hạn chế từ nhiều nguồn kết hợp | Tách domain contexts; result-level masking sau merge; không expose data lineage chi tiết cho user |

### Guardrails Stack (Tools)

| Layer | Tool | Vai trò |
|-------|------|---------|
| Input guard | LLM Guard (Protect AI) | Scan input: injection, jailbreak, toxic content |
| PII detection | Microsoft Presidio | Detect và mask PII trong input/output |
| SQL validation | Custom AST Parser + Oracle SQL Firewall | Validate SQL syntax + semantic safety |
| Output validation | Guardrails AI | Schema-validate output format và content |
| Rate limiting | Kong + Redis | Chống brute-force jailbreak và data exfiltration |
| Audit trail | Immutable PostgreSQL + event streaming | Forensics khi incident |

---

## Product Scope

### Phase 0 — Foundation Alignment (1–2 tuần, trước MVP)

**Mục tiêu:** Alignment giữa teams, không code.

- [ ] Chỉ định owners: business, data, security, engineering
- [ ] Kiểm kê Oracle sources, schema boundaries, role mapping, sensitivity classes
- [ ] Chọn semantic layer strategy: Cube.dev / custom / dbt MetricFlow
- [x] Lock policy engine: Cerbos; principal attribute mapping Phase 1 tối thiểu gồm `department` và `clearance`
- [ ] Chốt top 20–50 business questions và 10–20 KPI tier-0
- [ ] Chuẩn hóa canonical business keys giữa các domain

**Exit criteria:** Source inventory ✓ | Policy attribute model ✓ | KPI shortlist ✓ | Agreed integration boundaries ✓

---

### Phase 1 (MVP) — "The Reliable Assistant" (3–5 tuần)

**Phạm vi:**
- Text-to-SQL cho 1 domain pilot (Sales hoặc Finance)
- Basic RAG cho 1–2 kho tài liệu ưu tiên
- Auth: Keycloak + LDAP; RBAC Oracle; Audit Log đầy đủ
- Session memory: short-term Redis only
- Inference: OpenAI GPT-4o hoặc Claude Sonnet 4.6
- Export: CSV/Excel cơ bản

**Không có trong MVP:**
- Cross-domain federated queries
- Forecasting
- Approval workflow nhiều tầng
- Long-term memory
- Scheduled reports tự động
- Local LLM

**MVP Go/No-Go Gate:**
- [ ] Tier-0 KPI definitions tồn tại trong Semantic Layer
- [ ] Audit log 100% complete
- [ ] Oracle connector read-only và validated
- [ ] Ít nhất 1 domain hoạt động end-to-end
- [ ] Policy enforcement trước retrieval/query

---

### Phase 2 (Pilot) — "The Knowledge Expert" (4–8 tuần)

**Phạm vi:**
- Mở rộng sang 3–5 departments
- Cross-domain decomposed queries
- Cerbos obligations trước retrieval + tool calls; Phase 1 đã lock baseline `principal.attr` với `department` và `clearance`, Phase 2 chỉ mở rộng obligations/policy depth
- RAG metadata filtering + ingestion validation đầy đủ
- Semantic result cache + curated marts cho hot paths
- Async export + basic scheduled reporting
- Medium-term memory (PostgreSQL summaries)
- Query approval workflow (sensitive tier >= 2)
- Chuyển đổi Local LLM (LLaMA 3 / Qwen 2.5) — A/B test với cloud LLM

**Pilot Go/No-Go Gate:**
- [ ] Cross-domain queries hoạt động qua decomposition
- [ ] P95 trong ngưỡng target
- [ ] Audit đủ truy vết data lineage
- [ ] Policy enforcement có test coverage

---

### Phase 3 (Production) — "The Private Sovereign AI" (6–12 tuần)

**Phạm vi:**
- Oracle True Cache / read scaling
- Tách workload pools đầy đủ
- Hierarchical memory + selective recall
- Observability end-to-end (OpenTelemetry + Langfuse)
- Approval workflow cho sensitive exports
- Materialized integration views cho cross-domain hot paths
- Forecasting: time-series, anomaly detection, drill-down
- Bulk forecast async (Spark/Dask workers)
- Full Local LLM sovereign deployment (option)

**Production Go/No-Go Gate:**
- [ ] Answer quality validated trên real business questions (> 90% accuracy)
- [ ] Governance và auditability validated
- [ ] Cache/read-scaling strategy implemented
- [ ] Runbooks cho Oracle, RAG, model, policy failures

---

## Out-of-Scope

Các item sau **KHÔNG** nằm trong phạm vi của dự án này:

| Item | Lý do out-of-scope |
|------|-------------------|
| Real-time streaming data (Kafka, CDC) | Dữ liệu Oracle đủ cho batch analytics; streaming là separate project |
| Mobile application (iOS/Android) | Web-first; mobile không trong yêu cầu hiện tại |
| Voice interface | Không trong requirement; có thể xem xét Phase 4+ |
| Public-facing chatbot | Hệ thống chỉ dành cho nội bộ; không expose ra internet |
| Data warehouse / ETL pipeline | Hệ thống đọc Oracle trực tiếp; không build data warehouse mới |
| BI tool replacement (Tableau, Power BI) | AI Assistant bổ sung, không thay thế BI tools hiện tại |
| Code generation / DevOps chatbot | Scope chỉ là data Q&A, không phải code assistant |
| Integration với non-Oracle sources (SAP, Salesforce) ngoài Phase 1 | Chỉ Oracle cho Phase 1; cân nhắc Phase 3+ |
| Multi-language (ngoài Vietnamese/English) | Hệ thống hỗ trợ Tiếng Việt và Tiếng Anh; không có language khác trong scope |
| Autonomous AI agent tự thực thi actions (write/update DB) | Chỉ read-only; không có write operations vào Oracle |

---

## Technology Stack

| Layer | Technology | Lý do chọn |
|-------|-----------|------------|
| Backend API | Python 3.12 + FastAPI | Async, AI/ML ecosystem tốt nhất; aligned với workspace/tooling đã lock |
| API Gateway | Kong Gateway | Rate limiting, auth plugin, distributed tracing |
| Identity Provider | Keycloak | LDAP/AD integration, OIDC/OAuth2, enterprise-ready |
| Agent Orchestration | LangGraph | Stateful multi-step agent, workflow control |
| RAG Framework | LlamaIndex | RAG-optimized, 35% better retrieval vs alternatives |
| Semantic Layer | Cube.dev (headless) + custom YAML | Business contract API; Oracle-specific KPI definitions |
| Policy Engine | Cerbos | ABAC/RBAC pre-retrieval enforcement; supports query plan filtering |
| Primary LLM (Phase 1) | Claude Sonnet 4.6 (Anthropic) | Best coding + SQL generation; 200K context; safety |
| Complex analysis | Claude Opus 4.7 | Deepest reasoning cho forecast, phân tích phức tạp |
| Local LLM (Phase 2+) | LLaMA 3.x 70B+ / Qwen 2.5-72B | On-premise, air-gapped, full data control |
| Oracle Connector | python-oracledb + SQLAlchemy | Oracle official driver; connection pooling |
| Vector Store | Weaviate (self-hosted) | Vector retrieval cho RAG; access control dựa vào pre-retrieval policy filtering + network isolation + metadata constraints |
| Metadata / Audit / Memory | PostgreSQL 16+ | ACID, RLS, append-only audit tables |
| Session Cache | Redis 7+ | Short-term memory TTL, result cache, rate limiting |
| PII Detection | Microsoft Presidio | Production-grade PII anonymization |
| AI Safety | LLM Guard + Guardrails AI | Input/output scanning, output validation |
| Forecasting | Nixtla TimeGPT + statsmodels | Zero-shot forecasting + explainable statistical |
| Observability | OpenTelemetry + Prometheus/Grafana + Langfuse | Full-stack + LLM-specific observability |
| Frontend | React 18 + TypeScript + shadcn/ui | Enterprise UI; streaming support |
| Container | Docker + Kubernetes | Production orchestration |

---

## Risk Checklist

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Semantic Layer chậm tiến độ** do phải model hóa toàn enterprise | High | High | Bắt đầu 10–20 metrics tier-0; không model toàn enterprise trước Phase 1 |
| **Data quality kém** làm SQL accuracy thấp | Medium | High | Validate tier-0 metric definitions trước launch; eval set chuẩn |
| **LLM hallucination** sinh báo cáo sai | Medium | High | Chỉ trả kết quả từ verified SQL/RAG; không cho LLM generate numbers; output validation |
| **Oracle performance degradation** do AI query storm | Medium | High | Read replicas; query governor; rate limit; không query primary OLTP |
| **User adoption thấp** vì không tin tưởng AI | Medium | Medium | Show SQL + source citations; feedback loop; gradual rollout |
| **Vendor lock-in** với OpenAI | Medium | Medium | Modular LLM interface; test Local LLM từ Phase 2 |
| **RAG leakage** tài liệu cross-department | Low | Critical | Pre-retrieval filtering mandatory; regression tests; security review trước pilot |
| **Prompt injection attack** thành công | Low | Critical | Defense-in-depth; LLM Guard; rate limit; audit alert |
| **PDPA non-compliance** do log chứa PII | Low | High | Log sanitizer; Presidio scan; log retention policy; quarterly audit |
| **Key mismatch** khi merge cross-domain queries | Medium | Medium | Canonical business keys chuẩn hóa từ Phase 0; integration tests |
| **Chi phí LLM tăng mạnh** khi scale | High | Medium | Semantic cache; hierarchical memory; async jobs; Local LLM Phase 2 |
| **Memory isolation failure** giữa users | Low | Critical | Memory isolated by user_id + department_id; regression test bắt buộc |

---

## Department Use Cases

### Sales Department

| Câu hỏi người dùng | Mode | Nguồn dữ liệu |
|---------------------|------|---------------|
| "Doanh thu chi nhánh HCM tháng này vs cùng kỳ năm ngoái?" | SQL | SALES_DB.REVENUE |
| "Top 10 sản phẩm bán chạy nhất Q1/2026 theo khu vực?" | SQL | SALES_DB.PRODUCT_SALES |
| "Tại sao doanh thu miền Bắc giảm 15%?" | Hybrid | SQL (số liệu) + RAG (biên bản họp, báo cáo thị trường) |
| "Dự báo doanh thu tháng sau theo kênh phân phối?" | Forecast | Time-series trên SALES_DB.DAILY_REVENUE |

### Finance Department

| Câu hỏi người dùng | Mode | Nguồn dữ liệu |
|---------------------|------|---------------|
| "Chi phí vận hành Q1 so với ngân sách phê duyệt?" | SQL (cross-domain) | FINANCE_DB.COST + BUDGET_DB.APPROVED |
| "EBITDA 6 tháng đầu năm theo từng BU?" | SQL | FINANCE_ANALYTICS.EBITDA_VIEW |
| "Các khoản chi nào vượt ngân sách > 20%?" | SQL | FINANCE_DB.ACTUAL vs BUDGET_DB.PLAN |
| "Dự báo dòng tiền Q3/2026?" | Forecast | Cash flow time-series |

### HR Department

| Câu hỏi người dùng | Mode | Nguồn dữ liệu |
|---------------------|------|---------------|
| "Tỷ lệ nghỉ việc theo phòng ban 6 tháng đầu năm?" | SQL (masked PII) | HR_DB.EMPLOYEE_STATUS |
| "Phân tích lý do nghỉ việc dựa trên exit interview?" | RAG | Tài liệu exit interview (masked) |
| "Dự báo nhu cầu tuyển dụng Q4 theo phòng ban?" | Forecast | HR headcount time-series |

### Operations Department

| Câu hỏi người dùng | Mode | Nguồn dữ liệu |
|---------------------|------|---------------|
| "Hiệu suất kho theo khu vực tháng này?" | SQL | OPS_DB.WAREHOUSE_KPI |
| "Tỷ lệ giao hàng đúng hẹn theo vùng?" | SQL | OPS_DB.DELIVERY_METRICS |
| "Phát hiện bất thường trong số lượng đơn hàng tháng 3?" | Forecast (anomaly) | Order volume time-series |

---

## Luồng Xử Lý Một Câu Hỏi (End-to-End)

```
User gửi câu hỏi
    │
    ▼
Kong Gateway: Auth (JWT validate) + Rate Limit check + Trace ID gán
    │
    ▼
LangGraph Orchestrator: Intent Classification (sql/rag/hybrid/forecast)
    │
    ▼
Policy Check (Cerbos): user có quyền access domain này không?
Principal mapping tối thiểu Phase 1: `principal.attr.department`, `principal.attr.clearance`; schema này được freeze sớm để các phase sau chỉ extend.
    │  (Nếu không → reject ngay, ghi audit)
    ▼
Semantic Layer: Resolve business terms → metric definitions → allowed joins
    │
    ├─[SQL]──► Oracle Connector Gateway → AST validate → Query Governor check
    │               → Oracle VPD enforce RLS → Execute → Return rows
    │
    ├─[RAG]──► LlamaIndex → Policy pre-filter → Vector search → Rerank
    │               → Citation extraction
    │
    ├─[Hybrid]─► Cả hai paths trên → Merge tại application layer
    │
    └─[Forecast]─► Async job queue → Nixtla/statsmodels → Job ID trả về ngay
    │
    ▼
Result Composer: PII scan (Presidio) + Data Masking + Natural Language Explanation
    │
    ▼
Audit Logger: ghi đầy đủ (user, intent, SQL, sources, policy, result metadata)
    │
    ▼
Response trả về User: Bảng/Biểu đồ + Citations + SQL Explanation
```

---

## Appendix: Best Practices & Anti-Patterns

### PHẢI LÀM

- Build semantic layer TRƯỚC khi build SQL generation
- Enforce policy TRƯỚC khi fetch dữ liệu, không phải sau
- Dùng Oracle VPD + Application-layer check (defense-in-depth)
- Tag mọi memory entry với user_id + department_id + sensitivity
- Test RAG leakage cross-department từ ngày đầu
- Bắt đầu hẹp (1 domain, 20 KPIs) rồi mở rộng

### KHÔNG ĐƯỢC LÀM

- Cho LLM nhìn thấy toàn bộ raw Oracle schema
- Dùng shared DBA account cho AI query path
- Filter quyền SAU KHI đã fetch dữ liệu
- Lưu raw Oracle data trong conversation memory hoặc log
- Cho cross-schema SQL trực tiếp là default answer path
- Deploy toàn enterprise trước khi MVP/Pilot chứng minh governance
- Trộn interactive chat path với batch export/forecasting trong cùng execution path
