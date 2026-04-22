# Kiến Trúc Hệ Thống AI Chatbot Nội Bộ Doanh Nghiệp
## Tài Liệu Thiết Kế Kiến Trúc & Kỹ Thuật Chi Tiết

---

## MỤC LỤC

1. [Phân Tích Bài Toán](#1-phân-tích-bài-toán)
2. [Kiến Trúc Tổng Thể](#2-kiến-trúc-tổng-thể)
3. [Thành Phần Hệ Thống Chi Tiết](#3-thành-phần-hệ-thống-chi-tiết)
4. [Luồng Xử Lý End-to-End](#4-luồng-xử-lý-end-to-end)
5. [Thiết Kế Phân Quyền & Bảo Mật](#5-thiết-kế-phân-quyền--bảo-mật)
6. [Thiết Kế Session Memory & Lịch Sử Hội Thoại](#6-thiết-kế-session-memory--lịch-sử-hội-thoại)
7. [Thiết Kế Truy Vấn Oracle Đa Nguồn Đa Schema](#7-thiết-kế-truy-vấn-oracle-đa-nguồn-đa-schema)
8. [Guardrails & AI Safety](#8-guardrails--ai-safety)
9. [Dự Báo & Phân Tích Nâng Cao](#9-dự-báo--phân-tích-nâng-cao)
10. [Yêu Cầu Phi Chức Năng](#10-yêu-cầu-phi-chức-năng)
11. [So Sánh Phương Án Kiến Trúc](#11-so-sánh-phương-án-kiến-trúc)
12. [Stack Công Nghệ Đề Xuất](#12-stack-công-nghệ-đề-xuất)
13. [Lộ Trình Triển Khai](#13-lộ-trình-triển-khai)
14. [Checklist Rủi Ro](#14-checklist-rủi-ro)
15. [Use Case Thực Tế](#15-use-case-thực-tế)
16. [Best Practices & Sai Lầm Cần Tránh](#16-best-practices--sai-lầm-cần-tránh)

---

## 1. PHÂN TÍCH BÀI TOÁN

### 1.1 Bản Chất Bài Toán

Đây là bài toán **Enterprise Data Intelligence Platform** kết hợp 4 năng lực cốt lõi:

- **Text-to-SQL + Multi-source Query**: Chuyển câu hỏi tự nhiên thành truy vấn SQL trên nhiều Oracle DB/schema, có kiểm soát phân quyền.
- **RAG (Retrieval-Augmented Generation)**: Truy xuất và tổng hợp thông tin từ tài liệu nội bộ (PDF, Word, Excel...) của từng phòng ban.
- **Analytics & Forecasting**: Phân tích xu hướng, phát hiện bất thường, dự báo số liệu.
- **Governed AI Access**: Toàn bộ hoạt động nằm trong khuôn khổ phân quyền RBAC/ABAC, audit đầy đủ, chống data leakage.

### 1.2 Các Thách Thức Chính

**Phức tạp dữ liệu**: Nhiều DB Oracle, nhiều schema, cấu trúc bảng khác nhau, naming convention không thống nhất, business logic phức tạp ẩn trong stored procedures.

**Phân quyền đa tầng**: Không chỉ phân quyền ở mức bảng/view mà cần row-level, column-level, thậm chí cell-level security. Ví dụ: Phòng kinh doanh miền Bắc chỉ xem dữ liệu miền Bắc, trưởng phòng xem toàn miền, giám đốc xem toàn quốc.

**AI Safety trong ngữ cảnh doanh nghiệp**: LLM có thể bị khai thác để truy cập dữ liệu ngoài quyền hạn thông qua prompt injection, multi-turn escalation, hoặc suy luận gián tiếp từ nhiều nguồn.

**Hiệu năng**: Truy vấn Oracle production không được ảnh hưởng hệ thống giao dịch chính.

### 1.3 Đặc Thù Cần Lưu Ý

- Oracle DB thường có licensing phức tạp — cần tính toán kỹ read replica, connection pooling.
- Doanh nghiệp lớn tại Việt Nam thường có hệ thống LDAP/AD sẵn — cần tích hợp.
- Compliance yêu cầu có thể bao gồm PDPA (nếu có dữ liệu khách hàng), quy định ngành tài chính/ngân hàng, hoặc quy định nội bộ tập đoàn.

---

## 2. KIẾN TRÚC TỔNG THỂ

### 2.1 Sơ Đồ Kiến Trúc High-Level

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │  Web Chat UI │  │  Admin Panel │  │  Mobile App  │  │ API Consumer  │   │
│  │  (React/Vue) │  │  (React)     │  │  (Optional)  │  │ (Ext System)  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘   │
└─────────┼──────────────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │                  │
          ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (Kong / APISIX)                        │
│  Rate Limit │ JWT Validation │ Request Logging │ CORS │ IP Whitelist       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AUTH & IDENTITY LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐                    │
│  │   Keycloak   │  │ LDAP/AD      │  │ Policy Engine  │                    │
│  │   (IdP)      │◄─┤ Integration  │  │ (OPA/Cedar)    │                    │
│  └──────────────┘  └──────────────┘  └────────────────┘                    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI ORCHESTRATION LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Agent Router / Planner                            │   │
│  │  (LangGraph / Custom State Machine)                                 │   │
│  │                                                                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │ Intent  │ │ Query   │ │ Context  │ │ Response │ │ Guardrail  │  │   │
│  │  │Classify │→│ Planner │→│ Builder  │→│Generator │→│ Checker    │  │   │
│  │  └─────────┘ └─────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌───────────────┐       │
│  │ Input      │  │ Output     │  │ Permission   │  │ Tool Call     │       │
│  │ Guardrails │  │ Guardrails │  │ Validator    │  │ Validator     │       │
│  └────────────┘  └────────────┘  └──────────────┘  └───────────────┘       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│   RAG PIPELINE   │  │  TEXT-TO-SQL     │  │  ANALYTICS ENGINE   │
│                  │  │  PIPELINE        │  │                     │
│ ┌──────────────┐ │  │ ┌──────────────┐ │  │ ┌─────────────────┐ │
│ │ Doc Ingestion│ │  │ │Semantic Layer│ │  │ │ Stat Analysis   │ │
│ │ (Unstructured│ │  │ │(Metric Def)  │ │  │ │ (Pandas/Polars) │ │
│ │  / LlamaParse│ │  │ ├──────────────┤ │  │ ├─────────────────┤ │
│ │  / Docling)  │ │  │ │ NL-to-SQL    │ │  │ │ Forecasting     │ │
│ ├──────────────┤ │  │ │ Generator    │ │  │ │ (Prophet/       │ │
│ │ Embedding    │ │  │ ├──────────────┤ │  │ │  statsmodels)   │ │
│ │ (OpenAI /    │ │  │ │ SQL Validator│ │  │ ├─────────────────┤ │
│ │  BGE / E5)   │ │  │ │ & Sanitizer │ │  │ │ Anomaly Detect  │ │
│ ├──────────────┤ │  │ ├──────────────┤ │  │ │ (IsolationForest│ │
│ │ Vector Store │ │  │ │ Query        │ │  │ │  /Z-score)      │ │
│ │ (Milvus /    │ │  │ │ Executor     │ │  │ ├─────────────────┤ │
│ │  pgvector)   │ │  │ ├──────────────┤ │  │ │ Chart Generator │ │
│ ├──────────────┤ │  │ │ Result       │ │  │ │ (ECharts/       │ │
│ │ Reranker     │ │  │ │ Formatter    │ │  │ │  Plotly)        │ │
│ │ (Cohere/BGE) │ │  │ └──────────────┘ │  │ └─────────────────┘ │
│ └──────────────┘ │  └──────────────────┘  └──────────────────────┘
└──────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA ACCESS LAYER                                   │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ Oracle       │  │ Oracle       │  │ Oracle       │  │ Document      │   │
│  │ DB Pool A    │  │ DB Pool B    │  │ DB Pool C    │  │ Storage       │   │
│  │ (Read Rep.)  │  │ (Read Rep.)  │  │ (Read Rep.)  │  │ (MinIO/S3)    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                Metadata Catalog / Business Glossary                  │   │
│  │  (PostgreSQL + Admin UI)                                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE & OPERATIONS                             │
│                                                                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ ┌────────────┐  │
│  │ Redis      │ │ PostgreSQL │ │ ELK/Loki   │ │Prometheus│ │ Celery /   │  │
│  │ (Cache +   │ │ (Metadata, │ │ (Log &     │ │+ Grafana │ │ Temporal   │  │
│  │  Session)  │ │  Audit,    │ │  Audit     │ │(Monitor) │ │ (Workflow) │  │
│  │            │ │  Config)   │ │  Search)   │ │          │ │            │  │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Thành Phần Bắt Buộc vs. Nên Có

**Bắt buộc (MVP)**:
- API Gateway + Auth (Keycloak + LDAP)
- AI Orchestration Layer (Agent Router)
- Text-to-SQL Pipeline + Semantic Layer
- Input/Output Guardrails
- Permission Validator
- Metadata Catalog (ít nhất ở mức config file)
- Session Memory (Redis)
- Audit Logging
- Data Connectors (Oracle read replicas)
- Web Chat UI cơ bản

**Nên có (Pilot)**:
- RAG Pipeline cho tài liệu
- Cache Layer thông minh
- Monitoring & Alerting (Grafana)
- Export Service (Excel/PDF)
- Admin Panel đầy đủ
- Policy Engine (OPA)
- Reranker cho RAG

**Nâng cao (Production)**:
- Forecasting Engine
- Anomaly Detection
- Scheduled Report Service
- Multi-turn conversation memory tối ưu
- Data Masking Engine
- Approval Workflow cho truy vấn nhạy cảm
- HA/DR setup

---

## 3. THÀNH PHẦN HỆ THỐNG CHI TIẾT

### 3.1 Giao Diện Người Dùng

**User Chat Interface (React + TypeScript)**:
- Chat window với streaming response (SSE/WebSocket)
- Hiển thị kết quả dạng bảng (ag-Grid hoặc TanStack Table), biểu đồ (ECharts/Recharts)
- Nút "Xem SQL đã sinh", "Xem nguồn dữ liệu", "Giải thích kết quả"
- Export: CSV, Excel, PDF
- Sidebar: lịch sử hội thoại, báo cáo đã lưu, bookmark câu hỏi hay dùng
- Feedback: thumbs up/down + comment cho mỗi câu trả lời

**Admin Panel (React)**:
- Quản lý user/role/permission mapping
- Upload và quản lý tài liệu theo phòng ban
- Cấu hình data source (DB connection, schema mapping)
- Quản lý metadata catalog: tên bảng → business name, mô tả cột, KPI definitions
- Xem audit log, thống kê sử dụng
- Quản lý prompt templates, guardrail rules
- Approve/reject truy vấn nhạy cảm
- Monitor: latency, error rate, token usage, cost

### 3.2 API Gateway

**Đề xuất: Kong Gateway hoặc Apache APISIX**

Chức năng:
- JWT validation (từ Keycloak)
- Rate limiting: theo user (ví dụ 60 req/min), theo phòng ban (ví dụ 500 req/min)
- Request/Response logging (sanitized — không log body chứa dữ liệu nhạy cảm)
- CORS configuration
- IP whitelist (nếu triển khai on-premise)
- Request size limit (chống upload file quá lớn)
- Circuit breaker cho downstream services

### 3.3 Authentication & Authorization

```
┌─────────────────────────────────────────────────────┐
│                   KEYCLOAK (IdP)                     │
│                                                      │
│  ┌─────────────┐    ┌──────────────────────────┐    │
│  │  User Store │    │   Realm: enterprise-bot    │    │
│  │  (Internal) │    │                            │    │
│  ├─────────────┤    │  Roles:                    │    │
│  │  LDAP/AD    │◄──►│   - admin                  │    │
│  │  Federation │    │   - dept_manager           │    │
│  │             │    │   - dept_user              │    │
│  └─────────────┘    │   - viewer                 │    │
│                      │                            │    │
│                      │  Groups:                   │    │
│                      │   - dept_sales_north       │    │
│                      │   - dept_sales_south       │    │
│                      │   - dept_finance           │    │
│                      │   - dept_hr                │    │
│                      │   - dept_it                │    │
│                      └──────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                          │
                          ▼ JWT Token chứa:
                    {
                      "sub": "user123",
                      "realm_access": {"roles": ["dept_user"]},
                      "groups": ["/dept_sales_north"],
                      "data_scope": {
                        "region": ["north"],
                        "schemas": ["SALES_NORTH", "COMMON"],
                        "tables_allowed": [...],
                        "columns_masked": [...]
                      }
                    }
                          │
                          ▼
              ┌──────────────────────┐
              │  OPA / Cedar Policy  │
              │  Engine              │
              │                      │
              │  Evaluate:           │
              │  - Can user X        │
              │    access table Y?   │
              │  - Can user X see    │
              │    column Z?         │
              │  - Does query match  │
              │    user's region?    │
              └──────────────────────┘
```

**Chi tiết thiết kế RBAC + ABAC hybrid**:

Bảng `user_data_permissions` (PostgreSQL):
```sql
CREATE TABLE user_data_permissions (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(100) NOT NULL,
    department_id   VARCHAR(50)  NOT NULL,
    role            VARCHAR(50)  NOT NULL,  -- admin, dept_manager, dept_user, viewer
    -- Data Scope (ABAC attributes)
    allowed_db_sources    TEXT[],     -- ['ORACLE_SALES', 'ORACLE_HR']
    allowed_schemas       TEXT[],     -- ['SALES_NORTH', 'COMMON']
    allowed_tables        TEXT[],     -- NULL = all in schema, or explicit list
    denied_columns        TEXT[],     -- columns to mask/hide
    row_filter_conditions JSONB,      -- {"region": "north", "branch_id": [1,2,3]}
    -- Document scope
    allowed_doc_namespaces TEXT[],    -- RAG document namespaces
    -- Restrictions
    max_rows_per_query    INT DEFAULT 10000,
    can_export            BOOLEAN DEFAULT false,
    can_use_forecasting   BOOLEAN DEFAULT false,
    requires_approval     BOOLEAN DEFAULT false,  -- for sensitive queries
    is_active             BOOLEAN DEFAULT true,
    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW()
);
```

### 3.4 AI Orchestration Layer

**Đề xuất: LangGraph (Python) — State Machine-based Agent Framework**

Lý do chọn LangGraph thay vì LangChain Agent thuần:
- Kiểm soát flow rõ ràng, dễ debug
- Hỗ trợ conditional branching, parallel execution
- Dễ thêm guardrail nodes
- State management tường minh

```python
# Simplified LangGraph flow definition
from langgraph.graph import StateGraph, END

class ChatState(TypedDict):
    user_id: str
    user_permissions: dict
    messages: list
    intent: str
    sub_intents: list
    query_plan: dict
    sql_generated: str
    sql_validated: bool
    raw_results: Any
    filtered_results: Any
    response: str
    audit_record: dict
    error: str

graph = StateGraph(ChatState)

# Nodes
graph.add_node("input_guardrail",     check_input_safety)
graph.add_node("load_permissions",    load_user_permissions)
graph.add_node("classify_intent",     classify_user_intent)
graph.add_node("build_context",       build_context_with_memory)
graph.add_node("route_to_pipeline",   route_intent)
graph.add_node("text_to_sql",         generate_sql)
graph.add_node("validate_sql",        validate_and_sanitize_sql)
graph.add_node("execute_query",       execute_on_oracle)
graph.add_node("rag_retrieve",        retrieve_documents)
graph.add_node("analytics_process",   run_analytics)
graph.add_node("format_response",     format_and_explain)
graph.add_node("output_guardrail",    check_output_safety)
graph.add_node("mask_sensitive",      apply_data_masking)
graph.add_node("log_audit",           write_audit_log)

# Edges
graph.set_entry_point("input_guardrail")
graph.add_edge("input_guardrail",   "load_permissions")
graph.add_edge("load_permissions",  "classify_intent")
graph.add_edge("classify_intent",   "build_context")
graph.add_edge("build_context",     "route_to_pipeline")

graph.add_conditional_edges("route_to_pipeline", route_decision, {
    "sql_query":   "text_to_sql",
    "rag_search":  "rag_retrieve",
    "analytics":   "analytics_process",
    "chitchat":    "format_response",
    "blocked":     "output_guardrail",
})

graph.add_edge("text_to_sql",      "validate_sql")
graph.add_edge("validate_sql",     "execute_query")
graph.add_edge("execute_query",    "format_response")
graph.add_edge("rag_retrieve",     "format_response")
graph.add_edge("analytics_process","format_response")
graph.add_edge("format_response",  "output_guardrail")
graph.add_edge("output_guardrail", "mask_sensitive")
graph.add_edge("mask_sensitive",   "log_audit")
graph.add_edge("log_audit",        END)
```

### 3.5 RAG Pipeline

```
Documents Upload          Ingestion Pipeline              Query Pipeline
     │                          │                              │
     ▼                          ▼                              ▼
┌──────────┐           ┌───────────────┐             ┌──────────────────┐
│ PDF/Word │           │ Chunking      │             │ User Question    │
│ Excel    │──────────►│ (Semantic +   │             │                  │
│ Text     │           │  Recursive)   │             └────────┬─────────┘
└──────────┘           │               │                      │
                       │ Metadata:     │                      ▼
                       │ - dept_id     │             ┌──────────────────┐
                       │ - doc_type    │             │ Embed Query      │
                       │ - upload_date │             │ + Metadata Filter│
                       │ - access_level│             │ (dept_id filter) │
                       └───────┬───────┘             └────────┬─────────┘
                               │                              │
                               ▼                              ▼
                       ┌───────────────┐             ┌──────────────────┐
                       │ Embedding     │             │ Vector Search    │
                       │ (BGE-M3 or   │             │ + Hybrid Search  │
                       │  text-embed-  │             │ (dense + sparse) │
                       │  3-large)     │             └────────┬─────────┘
                       └───────┬───────┘                      │
                               │                              ▼
                               ▼                     ┌──────────────────┐
                       ┌───────────────┐             │ Reranker         │
                       │ Vector Store  │             │ (BGE-reranker or │
                       │ (Milvus)      │◄────────────│  Cohere rerank)  │
                       │               │             └────────┬─────────┘
                       │ Collections:  │                      │
                       │ - dept_sales  │                      ▼
                       │ - dept_hr     │             ┌──────────────────┐
                       │ - dept_finance│             │ Context Assembly │
                       │ - common      │             │ (top-k chunks +  │
                       └───────────────┘             │  source metadata)│
                                                     └──────────────────┘
```

**Thiết kế phân quyền RAG**:
- Mỗi document khi upload được gán `namespace` = `dept_{department_id}`
- Metadata filter khi search: chỉ search trong namespace mà user có quyền
- Admin upload document "common" vào namespace `common` — ai cũng xem được
- Trưởng phòng upload document vào namespace phòng ban — chỉ thành viên phòng ban xem

### 3.6 Semantic Layer / Metric Layer

Đây là thành phần **quan trọng nhất** để Text-to-SQL hoạt động chính xác.

```yaml
# Ví dụ cấu hình Semantic Layer cho schema SALES
datasource: ORACLE_SALES
schema: SALES_NORTH

tables:
  - physical_name: DM_DOANH_THU
    business_name: "Bảng doanh thu bán hàng"
    description: "Chứa dữ liệu doanh thu theo ngày, sản phẩm, chi nhánh"
    columns:
      - physical: NGAY_GD
        business: "Ngày giao dịch"
        type: DATE
        format: "DD/MM/YYYY"
      - physical: MA_SP
        business: "Mã sản phẩm"
        type: VARCHAR2
        foreign_key: DM_SAN_PHAM.MA_SP
      - physical: MA_CN
        business: "Mã chi nhánh"
        type: VARCHAR2
        row_level_filter: true  # Dùng để lọc theo quyền user
      - physical: DOANH_THU_RONG
        business: "Doanh thu ròng (sau giảm trừ)"
        type: NUMBER
        sensitivity: "confidential"
      - physical: SO_LUONG
        business: "Số lượng bán"
        type: NUMBER

metrics:
  - name: "Doanh thu ròng"
    formula: "SUM(DM_DOANH_THU.DOANH_THU_RONG)"
    description: "Tổng doanh thu sau giảm trừ"
    granularity: [ngay, tuan, thang, quy, nam]
    dimensions: [chi_nhanh, san_pham, khu_vuc, kenh_ban]
    
  - name: "Tăng trưởng doanh thu MoM"
    formula: >
      (SUM(DM_DOANH_THU.DOANH_THU_RONG) - 
       LAG(SUM(DM_DOANH_THU.DOANH_THU_RONG)) OVER (ORDER BY TRUNC(NGAY_GD, 'MM')))
      / NULLIF(LAG(SUM(DM_DOANH_THU.DOANH_THU_RONG)) OVER (ORDER BY TRUNC(NGAY_GD, 'MM')), 0)
      * 100
    description: "Phần trăm tăng trưởng doanh thu so tháng trước"

  - name: "Số khách hàng mới"
    formula: "COUNT(DISTINCT CASE WHEN DM_KH.NGAY_MO >= :start_date THEN DM_KH.MA_KH END)"
    description: "Số khách hàng mới trong kỳ"

common_filters:
  - name: "Lọc theo kỳ"
    sql_template: "NGAY_GD BETWEEN :start_date AND :end_date"
  - name: "Lọc theo chi nhánh"
    sql_template: "MA_CN IN (:branch_list)"
  - name: "Lọc theo khu vực"
    sql_template: "MA_KV IN (:region_list)"

joins:
  - from: DM_DOANH_THU
    to: DM_SAN_PHAM
    on: "DM_DOANH_THU.MA_SP = DM_SAN_PHAM.MA_SP"
    type: LEFT JOIN
  - from: DM_DOANH_THU
    to: DM_CHI_NHANH
    on: "DM_DOANH_THU.MA_CN = DM_CHI_NHANH.MA_CN"
    type: LEFT JOIN

sample_questions:
  - question: "Doanh thu tháng này bao nhiêu?"
    sql: >
      SELECT SUM(DOANH_THU_RONG) AS doanh_thu
      FROM SALES_NORTH.DM_DOANH_THU
      WHERE NGAY_GD >= TRUNC(SYSDATE, 'MM')
        AND NGAY_GD < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), 1)
        AND MA_CN IN (:user_branches)
  - question: "Top 10 sản phẩm bán chạy nhất quý này"
    sql: >
      SELECT SP.TEN_SP, SUM(DT.SO_LUONG) AS tong_sl
      FROM SALES_NORTH.DM_DOANH_THU DT
      JOIN SALES_NORTH.DM_SAN_PHAM SP ON DT.MA_SP = SP.MA_SP
      WHERE DT.NGAY_GD >= TRUNC(SYSDATE, 'Q')
        AND DT.MA_CN IN (:user_branches)
      GROUP BY SP.TEN_SP
      ORDER BY tong_sl DESC
      FETCH FIRST 10 ROWS ONLY
```

### 3.7 Text-to-SQL Pipeline

```
User Question
      │
      ▼
┌──────────────────────────────────────────────────────────┐
│ Step 1: Schema Selection                                  │
│                                                            │
│ Input: question + user_permissions.allowed_schemas        │
│ Process:                                                   │
│   - Embed question → match relevant tables/metrics        │
│   - Only consider schemas user has access to              │
│ Output: list of relevant tables + columns + metrics       │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ Step 2: SQL Generation                                    │
│                                                            │
│ Prompt = [system_prompt + semantic_layer_context +         │
│           sample_queries + user_question]                  │
│                                                            │
│ System prompt includes:                                    │
│   - Oracle SQL dialect rules                              │
│   - Allowed tables/columns (from Step 1)                  │
│   - Metric definitions                                     │
│   - Row filter conditions (injected automatically)        │
│   - Restrictions: no DDL, no DML, no system tables        │
│   - Max rows: FETCH FIRST {max_rows} ROWS ONLY           │
│                                                            │
│ Output: SQL query string                                   │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ Step 3: SQL Validation & Sanitization                     │
│                                                            │
│ Checks (ALL must pass):                                   │
│   □ Parse SQL AST (sqlglot/sqlparse)                      │
│   □ Only SELECT statements allowed                        │
│   □ No subquery to system tables (ALL_TABLES, DBA_*, V$*) │
│   □ No DDL (CREATE, ALTER, DROP, TRUNCATE)                │
│   □ No DML (INSERT, UPDATE, DELETE, MERGE)                │
│   □ No DCL (GRANT, REVOKE)                                │
│   □ No dynamic SQL (EXECUTE IMMEDIATE)                    │
│   □ Tables referenced ⊆ user's allowed_tables            │
│   □ Columns referenced: mask denied_columns               │
│   □ WHERE clause includes row_filter_conditions           │
│   □ Has FETCH FIRST / ROWNUM limit                        │
│   □ No UNION with unauthorized tables                     │
│   □ No function calls to UTL_*, DBMS_* (prevent OS cmd)  │
│   □ Estimated cost < threshold (via EXPLAIN PLAN)         │
│                                                            │
│ If ANY check fails → block query, log, return error msg  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ Step 4: Query Execution                                   │
│                                                            │
│ - Execute on READ REPLICA (never on production master)   │
│ - Use connection pool per data source                     │
│ - Statement timeout: 30 seconds                           │
│ - Resource consumer group: LOW priority                   │
│ - Bind variables for parameters (prevent SQL injection)   │
│ - Row limit enforced at DB level                          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ Step 5: Result Post-processing                            │
│                                                            │
│ - Apply column masking (e.g., mask CMND, phone number)   │
│ - Verify row count ≤ max_rows_per_query                  │
│ - Format numbers (locale-aware)                           │
│ - Convert Oracle dates to display format                  │
│ - Truncate if too large for LLM context                   │
│ - Prepare chart data if visualization requested           │
└──────────────────────────────────────────────────────────┘
```

### 3.8 Session Memory & Cache

```
┌──────────────────────────────────────────────────────────┐
│                    MEMORY ARCHITECTURE                     │
│                                                            │
│  ┌────────────────┐                                       │
│  │ Short-term     │  Redis (TTL: 30 min idle)             │
│  │ Memory         │                                       │
│  │                │  - Current conversation messages      │
│  │                │  - Current filters/context             │
│  │                │  - Last SQL generated                  │
│  │                │  - Last query results (summary)        │
│  └────────────────┘                                       │
│                                                            │
│  ┌────────────────┐                                       │
│  │ Long-term      │  PostgreSQL                           │
│  │ Memory         │                                       │
│  │                │  - Conversation summaries              │
│  │                │  - Favorite queries / bookmarks        │
│  │                │  - User preferences                    │
│  │                │  - Frequently used reports             │
│  │                │  - Query patterns per user             │
│  └────────────────┘                                       │
│                                                            │
│  ┌────────────────┐                                       │
│  │ Query Cache    │  Redis (TTL: configurable)            │
│  │                │                                       │
│  │                │  Key: hash(SQL + params + user_scope) │
│  │                │  Value: result set (compressed)        │
│  │                │  TTL: 5 min (realtime) / 1h (daily)   │
│  │                │       / 24h (monthly reports)          │
│  └────────────────┘                                       │
│                                                            │
│  ┌────────────────┐                                       │
│  │ Audit Log      │  PostgreSQL + ELK (immutable)         │
│  │                │                                       │
│  │                │  - User ID, timestamp                  │
│  │                │  - Original question                   │
│  │                │  - Intent classified                   │
│  │                │  - SQL generated (full)                │
│  │                │  - SQL validated? result               │
│  │                │  - Data sources accessed               │
│  │                │  - Rows returned                       │
│  │                │  - Response summary (NOT full data)    │
│  │                │  - Guardrail triggers                  │
│  │                │  - Token usage                         │
│  │                │  - Latency breakdown                   │
│  └────────────────┘                                       │
└──────────────────────────────────────────────────────────┘
```

---

## 4. LUỒNG XỬ LÝ END-TO-END

### 4.1 Luồng Chi Tiết: Từ Câu Hỏi Đến Kết Quả

```
User: "Doanh thu tháng 3 so với tháng 2 tăng hay giảm bao nhiêu phần trăm?"

Step 1: INPUT GUARDRAIL (< 50ms)
├─ Check prompt injection patterns (regex + classifier)
├─ Check banned keywords/patterns
├─ Check message length (max 2000 chars)
├─ Sanitize input (strip HTML, script tags)
└─ Result: PASS → continue / BLOCK → return error

Step 2: LOAD PERMISSIONS (< 20ms, cached)
├─ Extract user_id from JWT
├─ Load from cache (Redis) or DB: allowed_schemas, tables, row_filters
└─ Build permission context object

Step 3: CLASSIFY INTENT (< 500ms)
├─ LLM call with few-shot examples:
│   - "sql_query": câu hỏi cần truy vấn DB
│   - "rag_search": câu hỏi về tài liệu/quy trình
│   - "analytics": câu hỏi cần phân tích/dự báo
│   - "comparison": so sánh số liệu (sub-type of sql_query)
│   - "export": yêu cầu xuất báo cáo
│   - "chitchat": chào hỏi, không liên quan dữ liệu
│   - "out_of_scope": không hỗ trợ
├─ Extract entities: time_range, metrics, dimensions, filters
└─ Result: intent="comparison", entities={
     metric: "doanh_thu",
     time_range: ["2024-02", "2024-03"],
     comparison_type: "month_over_month"
   }

Step 4: BUILD CONTEXT (< 100ms)
├─ Load short-term memory (current session)
├─ Check if previous context has relevant filters
│   (ví dụ: user đã lọc theo chi nhánh nào ở câu trước?)
├─ Load relevant semantic layer definitions
├─ Load sample SQL queries for this metric
└─ Compose LLM context prompt

Step 5: TEXT-TO-SQL GENERATION (< 2s)
├─ Prompt = system_prompt + semantic_context + question
├─ LLM generates SQL:
│   SELECT
│     TRUNC(NGAY_GD, 'MM') AS thang,
│     SUM(DOANH_THU_RONG) AS tong_doanh_thu
│   FROM SALES_NORTH.DM_DOANH_THU
│   WHERE NGAY_GD >= TO_DATE('2024-02-01', 'YYYY-MM-DD')
│     AND NGAY_GD < TO_DATE('2024-04-01', 'YYYY-MM-DD')
│     AND MA_CN IN (:user_branches)           -- auto-injected
│   GROUP BY TRUNC(NGAY_GD, 'MM')
│   ORDER BY thang
└─ LLM also generates explanation plan

Step 6: SQL VALIDATION (< 200ms)
├─ Parse with sqlglot
├─ Verify: SELECT only, allowed tables, allowed columns
├─ Inject row_filter if missing: AND MA_CN IN ('CN01', 'CN02')
├─ Add FETCH FIRST 10000 ROWS ONLY if missing
├─ Run EXPLAIN PLAN → check estimated cost < 50000
└─ Result: VALIDATED + modified SQL

Step 7: QUERY EXECUTION (< 5s target)
├─ Select connection pool for ORACLE_SALES read replica
├─ Bind parameters: :user_branches = user's branch list
├─ Execute with 30s timeout
├─ Fetch results
└─ Result: [{thang: '2024-02', tong_doanh_thu: 1500000000},
            {thang: '2024-03', tong_doanh_thu: 1620000000}]

Step 8: FORMAT RESPONSE (< 1s)
├─ LLM generates natural language answer:
│   "Doanh thu tháng 3/2024 đạt 1.62 tỷ, tăng 8% so với
│    tháng 2/2024 (1.5 tỷ). Mức tăng tuyệt đối là 120 triệu."
├─ Generate comparison chart data (bar chart)
├─ Prepare table view
└─ Include metadata: source=SALES_NORTH.DM_DOANH_THU, rows=2

Step 9: OUTPUT GUARDRAIL (< 100ms)
├─ Check response doesn't contain PII/sensitive data
├─ Check response doesn't reference unauthorized schemas
├─ Check response doesn't hallucinate numbers (compare with actual result)
├─ Verify column masking applied correctly
└─ Result: PASS

Step 10: MASK SENSITIVE DATA (< 50ms)
├─ Apply masking rules (if any columns in denied_columns appeared)
└─ Redact any accidentally exposed sensitive values

Step 11: AUDIT LOG (async, non-blocking)
├─ Write to PostgreSQL + ELK
└─ Record: user, question, intent, SQL, execution_time,
   rows_returned, response_summary, guardrail_results, tokens_used

Step 12: RETURN RESPONSE
├─ Stream response text (SSE)
├─ Attach: table data, chart config, SQL used, source info
└─ Update short-term memory with this Q&A pair
```

---

## 5. THIẾT KẾ PHÂN QUYỀN & BẢO MẬT

### 5.1 Mô Hình Phân Quyền Chi Tiết

**Tầng 1 — Authentication (Xác thực danh tính)**:
- Keycloak với LDAP federation (sync user/group từ AD)
- SSO (SAML/OIDC) cho web interface
- JWT token có expiry ngắn (15 min) + refresh token (8 hours)
- MFA bắt buộc cho role admin và dept_manager

**Tầng 2 — Authorization (Phân quyền chức năng)**:
```
Role Hierarchy:
  super_admin
    └─ Can: manage all, view all, configure system
  admin
    └─ Can: manage dept users, configure dept data sources, view dept audit
  dept_manager
    └─ Can: query all data in dept, export, use forecasting, approve
  dept_user
    └─ Can: query assigned data, limited export
  viewer
    └─ Can: view pre-built reports only, no ad-hoc queries
```

**Tầng 3 — Data Authorization (Phân quyền dữ liệu)**:

```
Row-Level Security:
  - User thuộc dept_sales_north → auto-inject: WHERE region = 'NORTH'
  - User thuộc dept_sales_south → auto-inject: WHERE region = 'SOUTH'
  - dept_manager → không inject region filter (xem toàn bộ dept)
  - Giám đốc → không inject filter (xem toàn bộ)

Column-Level Security:
  - dept_hr: salary, CMND/CCCD → masked cho non-HR users
  - dept_finance: lợi nhuận chi tiết → chỉ finance + C-level
  - Mọi PII (phone, email, address) → masked trừ khi explicit permission

Table-Level Security:
  - Mỗi user chỉ thấy tables trong allowed_tables
  - System tables (ALL_TABLES, DBA_USERS, V$SESSION) → blocked cho tất cả
```

### 5.2 SQL Security Enforcement

```python
class SQLSecurityEnforcer:
    """
    Runs AFTER LLM generates SQL, BEFORE execution.
    This is the critical security gate.
    """
    
    def enforce(self, sql: str, user_permissions: dict) -> tuple[bool, str, str]:
        """Returns (is_safe, modified_sql, reason_if_blocked)"""
        
        # 1. Parse SQL AST
        parsed = sqlglot.parse_one(sql, dialect="oracle")
        
        # 2. Block non-SELECT
        if parsed.key != "select":
            return False, "", "Only SELECT queries are allowed"
        
        # 3. Extract referenced tables
        tables = self._extract_tables(parsed)
        for table in tables:
            if table.upper() in SYSTEM_TABLES_BLACKLIST:
                return False, "", f"Access to {table} is not allowed"
            if table not in user_permissions["allowed_tables"]:
                return False, "", f"You don't have access to {table}"
        
        # 4. Check columns
        columns = self._extract_columns(parsed)
        for col in columns:
            if col in user_permissions["denied_columns"]:
                # Replace with masked version instead of blocking
                sql = self._mask_column(sql, col)
        
        # 5. Inject row-level filters
        row_filters = user_permissions.get("row_filter_conditions", {})
        if row_filters:
            sql = self._inject_where_conditions(sql, row_filters)
        
        # 6. Enforce row limit
        if not self._has_row_limit(parsed):
            sql += f"\nFETCH FIRST {user_permissions['max_rows_per_query']} ROWS ONLY"
        
        # 7. Block dangerous functions
        if self._contains_dangerous_functions(parsed):
            return False, "", "Query contains disallowed functions"
        
        # 8. Check query cost
        estimated_cost = self._get_explain_plan_cost(sql)
        if estimated_cost > MAX_QUERY_COST:
            return False, "", f"Query too expensive (cost: {estimated_cost})"
        
        return True, sql, ""
```

### 5.3 Data Masking Rules

```python
MASKING_RULES = {
    "CMND": lambda v: v[:3] + "****" + v[-2:] if v else None,
    "CCCD": lambda v: v[:3] + "*********" if v else None,
    "PHONE": lambda v: v[:3] + "****" + v[-3:] if v else None,
    "EMAIL": lambda v: v[0] + "***@" + v.split("@")[1] if v and "@" in v else None,
    "SALARY": lambda v: "<confidential>" if v else None,
    "BANK_ACCOUNT": lambda v: "****" + v[-4:] if v else None,
    "ADDRESS": lambda v: v.split(",")[0] + ", ***" if v and "," in v else "***",
}
```

---

## 6. THIẾT KẾ SESSION MEMORY & LỊCH SỬ HỘI THOẠI

### 6.1 Chiến Lược Memory

**Câu hỏi: Lưu toàn bộ hay tóm tắt?**

Đề xuất: **Hybrid** — lưu toàn bộ trong short-term, tóm tắt cho long-term.

```
                    Short-term Memory (Redis)
                    ┌────────────────────────────────┐
                    │ Session: user123_conv_abc       │
                    │                                 │
                    │ messages: [                     │
                    │   {role: user, content: "..."}  │  ← Lưu đầy đủ
                    │   {role: assistant, content:... }│    last 10 turns
                    │   ...                           │
                    │ ]                               │
                    │ current_filters: {region: "N"} │
                    │ last_sql: "SELECT ..."          │
                    │ last_tables: ["DM_DOANH_THU"]  │
                    │                                 │
                    │ TTL: 30 min (idle timeout)      │
                    └──────────────┬─────────────────┘
                                   │
                    On session end / TTL expiry
                                   │
                                   ▼
                    Long-term Memory (PostgreSQL)
                    ┌────────────────────────────────┐
                    │ Table: conversation_summaries   │
                    │                                 │
                    │ user_id: "user123"              │
                    │ conversation_id: "conv_abc"     │
                    │ summary: "User asked about      │  ← LLM-generated
                    │   Q1 revenue for North region,  │    summary
                    │   compared with Q4 last year"   │
                    │ key_entities: ["revenue",       │
                    │   "Q1_2024", "north"]           │
                    │ queries_used: ["SELECT ..."]    │
                    │ created_at: "2024-03-15"        │
                    │ tags: ["revenue", "comparison"] │
                    └────────────────────────────────┘
                    
                    ┌────────────────────────────────┐
                    │ Table: user_preferences         │
                    │                                 │
                    │ user_id: "user123"              │
                    │ preferred_charts: "bar"          │
                    │ default_filters: {region: "N"}  │
                    │ favorite_queries: [...]          │
                    │ frequent_metrics: ["revenue"]   │
                    │ language: "vi"                   │
                    └────────────────────────────────┘
```

### 6.2 Khi Nào Đưa Lịch Sử Vào Context

```python
def build_context(user_id: str, current_question: str, session: Session):
    context_parts = []
    
    # ALWAYS include: current session messages (last 5 turns)
    context_parts.append(format_recent_messages(session.messages[-10:]))  # 5 Q&A pairs
    
    # ALWAYS include: current filters/state
    if session.current_filters:
        context_parts.append(f"Current filters: {session.current_filters}")
    
    # CONDITIONALLY include: if question references "trước đó", "vừa nãy", "ở trên"
    if has_coreference(current_question):
        # Include more context
        context_parts.append(format_recent_messages(session.messages[-20:]))
    
    # CONDITIONALLY include: if question is vague, search long-term memory
    if is_ambiguous(current_question):
        relevant_summaries = search_conversation_summaries(
            user_id=user_id,
            query=current_question,
            limit=3
        )
        if relevant_summaries:
            context_parts.append(format_summaries(relevant_summaries))
    
    # NEVER include: other users' conversations
    # NEVER include: raw SQL from long-term memory (could be for different permission level)
    # NEVER include: full result sets from previous queries
    
    return "\n".join(context_parts)
```

### 6.3 Thiết Kế Tối Ưu Chi Phí

- Short-term: Redis — chi phí thấp, TTL tự động cleanup
- Long-term summaries: PostgreSQL — nhỏ (mỗi summary ~500 bytes)
- Full conversation logs: chỉ lưu trong Audit Log (ELK) — không dùng cho context
- Token budget cho memory context: max 2000 tokens (trong tổng 8000-16000 token context)
- Nén context: dùng LLM tóm tắt nếu history quá dài thay vì truncate

### 6.4 Bảo Mật Memory

- Mỗi session key bao gồm user_id: `session:{user_id}:{conversation_id}`
- Long-term memory query LUÔN filter theo user_id
- Admin không thể xem conversation content (chỉ xem audit summary)
- Conversation summaries KHÔNG chứa raw data numbers
- Redis: enable AUTH, disable external access, encrypt at-rest nếu có sensitive context

---

## 7. THIẾT KẾ TRUY VẤN ORACLE ĐA NGUỒN ĐA SCHEMA

### 7.1 Text-to-SQL vs. Semantic Layer — Đề Xuất Kết Hợp

**Phương án đề xuất: Semantic Layer + Template SQL + Guided Text-to-SQL**

```
                 Câu hỏi người dùng
                        │
                        ▼
              ┌──────────────────┐
              │ Phân loại câu hỏi│
              └────────┬─────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐ ┌──────────┐ ┌──────────────┐
   │ Standard   │ │ Custom   │ │ Complex /    │
   │ KPI Query  │ │ Ad-hoc   │ │ Cross-schema │
   │            │ │ Query    │ │ Query        │
   └─────┬──────┘ └────┬─────┘ └──────┬───────┘
         │              │              │
         ▼              ▼              ▼
   ┌────────────┐ ┌──────────┐ ┌──────────────┐
   │ Template   │ │ Guided   │ │ Multi-step   │
   │ SQL (pre-  │ │ Text-to- │ │ Query Plan   │
   │ defined    │ │ SQL with │ │ (orchestrate │
   │ metric     │ │ semantic │ │  multiple    │
   │ formulas)  │ │ context  │ │  single-     │
   │            │ │          │ │  schema      │
   │ SAFEST     │ │ BALANCED │ │  queries)    │
   │ FASTEST    │ │          │ │              │
   └────────────┘ └──────────┘ │ MOST COMPLEX │
                               └──────────────┘
```

**Giải thích 3 tầng**:

**Tầng 1 — Template SQL (ưu tiên cao nhất)**: Khi câu hỏi match với một KPI đã định nghĩa trong semantic layer, dùng template SQL có sẵn, chỉ thay parameters (date range, filters). An toàn nhất, nhanh nhất, không cần LLM generate SQL. Ví dụ: "Doanh thu tháng này" → dùng template metric "doanh_thu_rong" + filter tháng hiện tại.

**Tầng 2 — Guided Text-to-SQL**: Khi câu hỏi không match template nhưng nằm trong scope của 1 schema. LLM sinh SQL với context giới hạn (chỉ thấy tables/columns user có quyền). SQL được validate nghiêm ngặt trước khi chạy.

**Tầng 3 — Multi-step Query Plan**: Khi câu hỏi cần join data từ nhiều schema/DB khác nhau. KHÔNG cho LLM viết cross-schema SQL trực tiếp. Thay vào đó: tách thành nhiều single-schema queries → execute riêng → merge kết quả ở application layer. Ví dụ: "So sánh doanh thu với chi phí nhân sự theo phòng ban" → Query 1 (SALES schema): doanh thu theo phòng ban → Query 2 (HR schema): chi phí nhân sự theo phòng ban → App layer: merge by phòng ban, tính ratio.

### 7.2 Tổ Chức Metadata Catalog

```sql
-- PostgreSQL tables for metadata management

-- Data Sources
CREATE TABLE data_sources (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) UNIQUE NOT NULL,    -- 'ORACLE_SALES'
    db_type         VARCHAR(20) NOT NULL,            -- 'oracle'
    connection_info JSONB NOT NULL,                   -- encrypted connection details
    is_read_replica BOOLEAN DEFAULT true,
    max_connections INT DEFAULT 10,
    statement_timeout_sec INT DEFAULT 30,
    is_active       BOOLEAN DEFAULT true
);

-- Schema Registry
CREATE TABLE schema_registry (
    id              SERIAL PRIMARY KEY,
    data_source_id  INT REFERENCES data_sources(id),
    schema_name     VARCHAR(100) NOT NULL,           -- 'SALES_NORTH'
    business_name   VARCHAR(200),                     -- 'Dữ liệu bán hàng miền Bắc'
    description     TEXT,
    owner_department VARCHAR(50),
    UNIQUE(data_source_id, schema_name)
);

-- Table Catalog
CREATE TABLE table_catalog (
    id              SERIAL PRIMARY KEY,
    schema_id       INT REFERENCES schema_registry(id),
    table_name      VARCHAR(100) NOT NULL,
    business_name   VARCHAR(200),                     -- 'Bảng doanh thu'
    description     TEXT,
    table_type      VARCHAR(20) DEFAULT 'TABLE',      -- TABLE, VIEW, MATERIALIZED_VIEW
    row_count_approx BIGINT,
    is_queryable    BOOLEAN DEFAULT true,
    sensitivity     VARCHAR(20) DEFAULT 'normal',     -- normal, confidential, restricted
    UNIQUE(schema_id, table_name)
);

-- Column Catalog
CREATE TABLE column_catalog (
    id              SERIAL PRIMARY KEY,
    table_id        INT REFERENCES table_catalog(id),
    column_name     VARCHAR(100) NOT NULL,
    business_name   VARCHAR(200),                     -- 'Ngày giao dịch'
    description     TEXT,
    data_type       VARCHAR(50),
    is_pii          BOOLEAN DEFAULT false,
    is_sensitive    BOOLEAN DEFAULT false,
    masking_rule    VARCHAR(50),                       -- 'PHONE', 'EMAIL', 'SALARY', etc.
    is_filterable   BOOLEAN DEFAULT true,
    is_dimension    BOOLEAN DEFAULT false,             -- for grouping
    is_measure      BOOLEAN DEFAULT false,             -- for aggregation
    sample_values   TEXT[],                             -- ['2024-01-01', '2024-01-02']
    UNIQUE(table_id, column_name)
);

-- Business Metrics / KPI Definitions
CREATE TABLE metric_definitions (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,            -- 'Doanh thu ròng'
    description     TEXT,
    formula_sql     TEXT NOT NULL,                     -- 'SUM(DM_DOANH_THU.DOANH_THU_RONG)'
    base_table_id   INT REFERENCES table_catalog(id),
    required_joins  JSONB,                             -- join definitions
    available_dims  TEXT[],                             -- ['chi_nhanh', 'san_pham', 'thoi_gian']
    available_granularities TEXT[],                    -- ['ngay', 'tuan', 'thang', 'quy', 'nam']
    unit            VARCHAR(50),                       -- 'VND', '%', 'units'
    owner_department VARCHAR(50),
    sensitivity     VARCHAR(20) DEFAULT 'normal'
);

-- Sample Questions (Few-shot examples for LLM)
CREATE TABLE sample_questions (
    id              SERIAL PRIMARY KEY,
    question_vi     TEXT NOT NULL,                     -- Vietnamese question
    question_en     TEXT,                               -- English translation
    target_sql      TEXT NOT NULL,                     -- Expected SQL
    metric_ids      INT[],                              -- Related metrics
    schema_id       INT REFERENCES schema_registry(id),
    difficulty      VARCHAR(20) DEFAULT 'simple',     -- simple, medium, complex
    is_active       BOOLEAN DEFAULT true
);

-- Join Definitions
CREATE TABLE join_definitions (
    id              SERIAL PRIMARY KEY,
    from_table_id   INT REFERENCES table_catalog(id),
    to_table_id     INT REFERENCES table_catalog(id),
    join_type       VARCHAR(20) DEFAULT 'LEFT JOIN',
    join_condition  TEXT NOT NULL,                     -- 'T1.MA_SP = T2.MA_SP'
    is_cross_schema BOOLEAN DEFAULT false,
    description     TEXT
);
```

### 7.3 Connection Pool & Query Execution

```python
# Oracle Connection Pool Configuration
ORACLE_POOLS = {
    "ORACLE_SALES": {
        "dsn": "read-replica-sales.internal:1521/SALESDB",
        "user": "chatbot_readonly",         # Dedicated read-only user
        "min_connections": 2,
        "max_connections": 10,
        "timeout": 30,                       # seconds
        "statement_cache_size": 50,
        "session_pool_params": {
            "increment": 1,
            "getmode": oracledb.POOL_GETMODE_TIMEDWAIT,
            "wait_timeout": 5000,            # 5 sec wait for free connection
        }
    },
    "ORACLE_HR": {
        "dsn": "read-replica-hr.internal:1521/HRDB",
        "user": "chatbot_readonly",
        "min_connections": 1,
        "max_connections": 5,
        "timeout": 30,
    },
    "ORACLE_FINANCE": {
        "dsn": "read-replica-fin.internal:1521/FINDB",
        "user": "chatbot_readonly",
        "min_connections": 1,
        "max_connections": 5,
        "timeout": 30,
    }
}

# Query Execution with Safety Controls
async def execute_safe_query(
    pool_name: str,
    sql: str,
    bind_params: dict,
    max_rows: int = 10000
) -> QueryResult:
    pool = connection_pools[pool_name]
    
    async with pool.acquire() as conn:
        # Set resource consumer group (Oracle Resource Manager)
        await conn.execute(
            "BEGIN DBMS_SESSION.SWITCH_CURRENT_CONSUMER_GROUP('CHATBOT_LOW', FALSE); END;"
        )
        
        # Set statement timeout via Oracle profile
        # (configured at DB level: ALTER PROFILE chatbot_profile LIMIT LOGICAL_READS_PER_CALL 100000)
        
        cursor = conn.cursor()
        cursor.arraysize = min(max_rows, 1000)  # Fetch in batches
        
        try:
            await asyncio.wait_for(
                cursor.execute(sql, bind_params),
                timeout=30.0  # Application-level timeout
            )
            
            columns = [col[0] for col in cursor.description]
            rows = await cursor.fetchmany(max_rows)
            
            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=len(rows) >= max_rows
            )
        except asyncio.TimeoutError:
            await conn.cancel()
            raise QueryTimeoutError("Query exceeded 30 second timeout")
        finally:
            await cursor.close()
```

### 7.4 Cache Strategy

```python
CACHE_POLICIES = {
    "realtime_metrics": {
        # Doanh thu hôm nay, số đơn đang xử lý
        "ttl_seconds": 300,          # 5 phút
        "invalidation": "time_based"
    },
    "daily_reports": {
        # Báo cáo ngày hôm qua, tuần trước
        "ttl_seconds": 3600,         # 1 giờ
        "invalidation": "time_based"
    },
    "monthly_reports": {
        # Báo cáo tháng trước, quý trước
        "ttl_seconds": 86400,        # 24 giờ
        "invalidation": "time_based"
    },
    "master_data": {
        # Danh mục sản phẩm, chi nhánh, nhân viên
        "ttl_seconds": 3600,
        "invalidation": "event_based"  # invalidate khi có update
    },
    "historical_data": {
        # Dữ liệu năm cũ (immutable)
        "ttl_seconds": 604800,       # 7 ngày
        "invalidation": "none"
    }
}

def get_cache_key(sql: str, params: dict, user_scope: dict) -> str:
    """
    Cache key includes user scope to prevent data leakage.
    Two users with different regions get different cache entries.
    """
    scope_hash = hashlib.md5(json.dumps(user_scope, sort_keys=True).encode()).hexdigest()
    query_hash = hashlib.md5((sql + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    return f"query_cache:{scope_hash}:{query_hash}"
```

### 7.5 Chống Query Quá Nặng

```
Nhiều tầng bảo vệ:

1. EXPLAIN PLAN check (trước khi chạy):
   - Parse SQL, run EXPLAIN PLAN
   - Reject nếu cost > threshold (ví dụ 50000)
   - Reject nếu FULL TABLE SCAN trên bảng > 10M rows mà không có WHERE
   - Reject nếu Cartesian join detected

2. Oracle Resource Manager (tại DB level):
   - Tạo consumer group "CHATBOT_LOW"
   - Giới hạn: max 5% CPU, max 100K logical reads per call
   - Auto-cancel nếu vượt giới hạn

3. Application timeout:
   - 30 seconds cho queries bình thường
   - 120 seconds cho queries analytics/forecasting (flagged)
   - Cancel connection nếu timeout

4. Connection pool limit:
   - Max 10 connections per data source
   - Nếu pool full → queue request (max wait 5 sec) → reject

5. Rate limiting:
   - Max 10 queries/phút per user
   - Max 100 queries/phút per department
   - Heavy queries (cost > 10000) count as 5 regular queries
```

---

## 8. GUARDRAILS & AI SAFETY

### 8.1 Threat Model Tổng Hợp

```
┌────────────────────────────────────────────────────────────────────────┐
│                      THREAT LANDSCAPE                                  │
│                                                                        │
│  INPUT ATTACKS                    OUTPUT RISKS                         │
│  ─────────────                    ────────────                         │
│  ▪ Prompt Injection              ▪ Hallucination (số liệu sai)       │
│  ▪ Jailbreak Attempts            ▪ Data Leakage (lộ data cross-dept)  │
│  ▪ SQL Injection (via NL)        ▪ PII Exposure                       │
│  ▪ Multi-turn Escalation         ▪ Sensitive data in exports          │
│  ▪ Tool/Function Abuse           ▪ Logs chứa sensitive data           │
│                                                                        │
│  SYSTEMIC RISKS                  INFERENCE ATTACKS                     │
│  ──────────────                  ─────────────────                     │
│  ▪ Schema/Metadata Poisoning     ▪ Cross-source inference             │
│  ▪ Heavy queries → DoS           ▪ Statistical inference              │
│  ▪ Export sai người nhận          ▪ Membership inference               │
│  ▪ Cache poisoning               ▪ Model memorization leak            │
│  ▪ Supply chain (compromised     │                                     │
│    dependencies/models)          │                                     │
└────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Input Guardrails Chi Tiết

```python
class InputGuardrail:
    
    def check(self, user_input: str, user_context: dict) -> GuardrailResult:
        checks = [
            self._check_length(user_input),
            self._check_injection_patterns(user_input),
            self._check_jailbreak_patterns(user_input),
            self._check_sql_injection_patterns(user_input),
            self._check_system_prompt_leak_attempt(user_input),
            self._check_encoding_tricks(user_input),
            self._check_escalation_attempt(user_input, user_context),
        ]
        
        for result in checks:
            if not result.passed:
                return result
        return GuardrailResult(passed=True)
    
    def _check_injection_patterns(self, text: str) -> GuardrailResult:
        """Detect prompt injection attempts"""
        INJECTION_PATTERNS = [
            r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|rules|prompts)",
            r"you\s+are\s+now\s+(a|an|the)\s+",
            r"system\s*:\s*",
            r"<\s*system\s*>",
            r"###\s*(system|instruction|prompt)",
            r"forget\s+(everything|all|your)\s+(you|instructions|rules)",
            r"pretend\s+(you\s+are|to\s+be|that)",
            r"act\s+as\s+(if|a|an|the)",
            r"bypass\s+(security|filter|restriction|permission)",
            r"override\s+(permission|access|security|restriction)",
            r"show\s+me\s+(all|every)\s+(table|schema|database|user|password)",
            r"UNION\s+SELECT",
            r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|GRANT|EXEC)",
            r"--\s*$",  # SQL comment at end
        ]
        
        text_lower = text.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return GuardrailResult(
                    passed=False,
                    reason="potential_injection",
                    severity="high"
                )
        
        # LLM-based classifier as second layer
        injection_score = self.injection_classifier.predict(text)
        if injection_score > 0.8:
            return GuardrailResult(
                passed=False,
                reason="ai_detected_injection",
                severity="high"
            )
        
        return GuardrailResult(passed=True)
    
    def _check_escalation_attempt(self, text: str, context: dict) -> GuardrailResult:
        """Detect multi-turn privilege escalation"""
        recent_messages = context.get("recent_messages", [])
        
        # Pattern: user gradually asking for more sensitive data
        escalation_signals = [
            # User was asking about sales, now asking about HR data
            self._topic_shift_to_sensitive(recent_messages, text),
            # User trying to remove filters that were auto-applied
            self._trying_to_remove_filters(recent_messages, text),
            # User asking about other departments' data
            self._cross_department_request(text, context["user_permissions"]),
        ]
        
        if sum(escalation_signals) >= 2:
            return GuardrailResult(
                passed=False,
                reason="multi_turn_escalation_suspected",
                severity="medium"
            )
        
        return GuardrailResult(passed=True)
```

### 8.3 Output Guardrails Chi Tiết

```python
class OutputGuardrail:
    
    def check(self, response: str, query_result: Any, user_permissions: dict,
              original_question: str) -> GuardrailResult:
        
        checks = [
            self._check_pii_in_response(response),
            self._check_unauthorized_data_reference(response, user_permissions),
            self._check_hallucination(response, query_result),
            self._check_cross_dept_leak(response, user_permissions),
            self._check_sensitive_numbers(response, query_result),
        ]
        
        for result in checks:
            if not result.passed:
                return result
        return GuardrailResult(passed=True)
    
    def _check_hallucination(self, response: str, actual_data: Any) -> GuardrailResult:
        """
        Verify numbers in response match actual query results.
        This is CRITICAL for financial/business reporting.
        """
        # Extract all numbers from response
        response_numbers = self._extract_numbers(response)
        
        # Extract numbers from actual query results
        data_numbers = self._extract_numbers_from_result(actual_data)
        
        # Check each significant number in response exists in data
        for num in response_numbers:
            if num > 100:  # Only check significant numbers
                if not self._number_exists_or_derivable(num, data_numbers):
                    return GuardrailResult(
                        passed=False,
                        reason=f"Potential hallucination: {num} not found in query results",
                        severity="high",
                        action="regenerate_with_data_only"
                    )
        
        return GuardrailResult(passed=True)
    
    def _check_cross_dept_leak(self, response: str, permissions: dict) -> GuardrailResult:
        """Check if response accidentally reveals other departments' data"""
        user_dept = permissions["department_id"]
        allowed_schemas = permissions["allowed_schemas"]
        
        # Check if response mentions schemas/tables outside user's scope
        for schema in ALL_SCHEMAS:
            if schema not in allowed_schemas and schema.lower() in response.lower():
                return GuardrailResult(
                    passed=False,
                    reason=f"Response references unauthorized schema: {schema}",
                    severity="high"
                )
        
        return GuardrailResult(passed=True)
```

### 8.4 Anti-Inference Attack

```python
class InferenceAttackPrevention:
    """
    Prevent users from inferring unauthorized data by combining
    multiple authorized queries.
    
    Example attack:
    1. "Total revenue for all branches" → 100M
    2. "Revenue for Branch A" → 30M
    3. "Revenue for Branch B" → 25M
    4. "Revenue for Branch C" → 20M
    → User can infer Branch D (unauthorized) = 100M - 30M - 25M - 20M = 25M
    """
    
    def check_inference_risk(self, current_query: dict, 
                              query_history: list, 
                              user_permissions: dict) -> bool:
        # Rule 1: If user queries aggregate for ALL + individual parts,
        # and some parts are outside their permission, flag it
        if self._is_complement_attack(current_query, query_history, user_permissions):
            return True
        
        # Rule 2: Limit granularity of results when data points are too few
        # (e.g., if grouping by department yields only 2 rows, 
        #  individual values might be identifiable)
        if self._is_small_group_risk(current_query):
            return True
        
        return False
    
    def _is_small_group_risk(self, query: dict) -> bool:
        """
        If a GROUP BY query returns fewer than K rows (e.g., K=5),
        individual values might reveal personal/confidential info.
        Apply k-anonymity principle.
        """
        result_count = query.get("result_row_count", 0)
        has_sensitive_measure = query.get("has_sensitive_measure", False)
        
        if has_sensitive_measure and result_count < 5:
            return True
        return False
```

### 8.5 Audit Log Design

```sql
CREATE TABLE audit_logs (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id             VARCHAR(100) NOT NULL,
    department_id       VARCHAR(50),
    session_id          VARCHAR(100),
    conversation_id     VARCHAR(100),
    
    -- Request
    user_question       TEXT NOT NULL,
    detected_intent     VARCHAR(50),
    detected_entities   JSONB,
    
    -- Processing
    pipeline_used       VARCHAR(50),    -- 'text_to_sql', 'rag', 'analytics'
    sql_generated       TEXT,
    sql_validated       BOOLEAN,
    sql_validation_errors TEXT[],
    data_sources_accessed TEXT[],
    schemas_accessed    TEXT[],
    tables_accessed     TEXT[],
    
    -- Guardrails
    input_guardrail_result  VARCHAR(20),  -- 'pass', 'block', 'warn'
    input_guardrail_details JSONB,
    output_guardrail_result VARCHAR(20),
    output_guardrail_details JSONB,
    
    -- Results
    rows_returned       INT,
    response_summary    TEXT,            -- NOT full response (avoid storing sensitive data)
    response_type       VARCHAR(50),    -- 'text', 'table', 'chart', 'export'
    
    -- Performance
    total_latency_ms    INT,
    llm_latency_ms      INT,
    db_query_latency_ms INT,
    tokens_input        INT,
    tokens_output       INT,
    estimated_cost_usd  DECIMAL(10,6),
    
    -- Feedback
    user_feedback       VARCHAR(20),    -- 'positive', 'negative', null
    feedback_comment    TEXT
);

-- Indexes for common queries
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, timestamp DESC);
CREATE INDEX idx_audit_dept_time ON audit_logs(department_id, timestamp DESC);
CREATE INDEX idx_audit_guardrail ON audit_logs(input_guardrail_result) 
    WHERE input_guardrail_result != 'pass';
CREATE INDEX idx_audit_intent ON audit_logs(detected_intent, timestamp DESC);

-- IMPORTANT: Audit logs are IMMUTABLE - no UPDATE or DELETE allowed
-- Use separate retention policy (keep 1 year online, archive to cold storage)
REVOKE UPDATE, DELETE ON audit_logs FROM chatbot_app;
```

---

## 9. DỰ BÁO & PHÂN TÍCH NÂNG CAO

### 9.1 Bài Toán Dự Báo Phù Hợp

| Bài toán | Input | Phương pháp | Độ phức tạp |
|-----------|-------|-------------|-------------|
| Dự báo doanh thu tháng/quý tới | Time series doanh thu | Prophet / ARIMA / ETS | Thấp-TB |
| Dự báo nhu cầu sản phẩm | Lịch sử bán hàng + mùa vụ | Prophet + external regressors | TB |
| Phát hiện giao dịch bất thường | Dữ liệu giao dịch | Isolation Forest / Z-score | Thấp |
| Phát hiện xu hướng chi phí | Time series chi phí | Trend decomposition | Thấp |
| Dự báo churn khách hàng | Features khách hàng | Logistic Regression / XGBoost | TB-Cao |
| Phân loại khách hàng | RFM + demographics | K-Means / RFM scoring | TB |
| Dự báo dòng tiền | Cashflow history | ARIMA / Prophet | TB |

### 9.2 Khi Nào Dùng Gì

```
Quy tắc chọn phương pháp:

1. Rule-based / Simple Statistics:
   ├─ So sánh kỳ này vs kỳ trước (growth rate)
   ├─ Moving average (7-day, 30-day)
   ├─ Z-score cho phát hiện outlier
   ├─ Percentile/ranking
   └─ Khi nào: Câu hỏi đơn giản, real-time, không cần dự đoán tương lai

2. Statistical Models (Prophet, ARIMA, ETS):
   ├─ Dự báo time series (doanh thu, chi phí, nhu cầu)
   ├─ Phân tích seasonality
   ├─ Trend analysis
   └─ Khi nào: Cần dự báo 1-12 tháng, có ≥ 2 năm dữ liệu, pattern rõ ràng

3. ML Models (XGBoost, LightGBM):
   ├─ Classification (churn, risk, fraud)
   ├─ Scoring (customer value, credit score)
   └─ Khi nào: Có nhiều features, bài toán phi tuyến, cần accuracy cao

4. Deep Learning:
   ├─ NLP tasks (document classification, sentiment)
   ├─ Complex time series (nhiều biến phụ thuộc)
   └─ Khi nào: Có đủ dữ liệu (>100K samples), bài toán phức tạp
```

### 9.3 Giải Thích Kết Quả Dự Báo

```python
class ForecastExplainer:
    """
    Luôn kèm giải thích khi trả kết quả dự báo/phân tích.
    Người dùng nghiệp vụ cần hiểu WHY, không chỉ WHAT.
    """
    
    def explain_forecast(self, forecast_result: dict) -> str:
        explanation = []
        
        # 1. Kết quả chính
        explanation.append(
            f"Dự báo doanh thu tháng {forecast_result['target_month']}: "
            f"{format_vnd(forecast_result['predicted_value'])}"
        )
        
        # 2. Khoảng tin cậy
        explanation.append(
            f"Khoảng tin cậy 80%: {format_vnd(forecast_result['lower_80'])} "
            f"đến {format_vnd(forecast_result['upper_80'])}"
        )
        
        # 3. Giải thích xu hướng
        if forecast_result['trend'] == 'up':
            explanation.append(
                f"Xu hướng tăng {forecast_result['trend_pct']:.1f}% "
                f"so với cùng kỳ năm trước, chủ yếu do:"
            )
        
        # 4. Yếu tố ảnh hưởng (feature importance)
        for factor in forecast_result['top_factors'][:3]:
            explanation.append(f"  - {factor['name']}: tác động {factor['direction']} "
                             f"{abs(factor['impact_pct']):.1f}%")
        
        # 5. Caveats
        explanation.append(
            f"\n⚠️ Lưu ý: Dự báo dựa trên dữ liệu {forecast_result['data_range']}. "
            f"Độ chính xác model (MAPE): {forecast_result['mape']:.1f}%. "
            f"Kết quả có thể thay đổi nếu có yếu tố bất thường (lễ, COVID, chính sách mới)."
        )
        
        return "\n".join(explanation)
```

### 9.4 Anomaly Detection

```python
class AnomalyDetector:
    """
    Phát hiện bất thường trong dữ liệu và tự động cảnh báo.
    """
    
    def detect(self, data: pd.DataFrame, metric: str, 
               method: str = "zscore") -> list[Anomaly]:
        
        if method == "zscore":
            # Simple but effective for most business metrics
            mean = data[metric].rolling(30).mean()
            std = data[metric].rolling(30).std()
            z_scores = (data[metric] - mean) / std
            anomalies = data[abs(z_scores) > 3]
            
        elif method == "isolation_forest":
            # Better for multivariate anomalies
            from sklearn.ensemble import IsolationForest
            clf = IsolationForest(contamination=0.05, random_state=42)
            predictions = clf.fit_predict(data[[metric]])
            anomalies = data[predictions == -1]
            
        elif method == "prophet":
            # Best for time series with seasonality
            from prophet import Prophet
            model = Prophet(interval_width=0.99)
            model.fit(data.rename(columns={"date": "ds", metric: "y"}))
            forecast = model.predict(data.rename(columns={"date": "ds"}))
            anomalies = data[
                (data[metric] < forecast['yhat_lower']) | 
                (data[metric] > forecast['yhat_upper'])
            ]
        
        return [
            Anomaly(
                date=row['date'],
                value=row[metric],
                expected_range=(row.get('expected_low'), row.get('expected_high')),
                severity=self._classify_severity(row, mean_val, std_val),
                description=self._generate_description(row, metric)
            )
            for _, row in anomalies.iterrows()
        ]
```

---

## 10. YÊU CẦU PHI CHỨC NĂNG

### 10.1 Hiệu Năng

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Thời gian phản hồi đầu tiên (TTFB) | < 1s | 3s |
| Thời gian trả kết quả hoàn chỉnh (simple query) | < 5s | 10s |
| Thời gian trả kết quả (complex query/analytics) | < 15s | 30s |
| LLM inference latency | < 2s | 5s |
| Oracle query execution | < 3s | 10s |
| RAG retrieval + rerank | < 1s | 3s |
| Concurrent users | 50 | 100 |
| Requests/second (peak) | 20 | 50 |

### 10.2 Khả Năng Mở Rộng

```
Horizontal Scaling Strategy:

API Layer:        Stateless → scale với K8s HPA (CPU/memory based)
AI Orchestration: Stateless → scale pods, limit by LLM API concurrency
Redis:            Redis Cluster (3 master + 3 replica) hoặc Redis Sentinel
PostgreSQL:       Primary-Replica, pgBouncer for connection pooling
Vector Store:     Milvus cluster (separate query/index nodes)
Oracle:           Read replicas (managed by DBA team)
LLM:              
  - API-based (OpenAI/Anthropic): scale by API key quota
  - Self-hosted (vLLM/TGI): GPU autoscaling (more complex)
```

### 10.3 HA / DR / Backup

```
HA Design:
├─ API + Orchestration: Min 2 pods, anti-affinity across nodes
├─ Redis: Sentinel (3 nodes) hoặc Cluster mode
├─ PostgreSQL: Streaming replication, automatic failover (Patroni)
├─ Milvus: Replicated deployment
├─ Load Balancer: Active-Active (HAProxy / cloud LB)
└─ Health checks: /health endpoint, 10s interval, 3 failures → restart

DR Strategy:
├─ RPO (Recovery Point Objective): 1 hour
├─ RTO (Recovery Time Objective): 4 hours
├─ Backup: PostgreSQL WAL archiving (continuous), daily full backup
├─ Redis: RDB snapshots every 15 min + AOF
├─ Milvus: Daily collection backup to S3/MinIO
├─ Config: GitOps (all config in Git, reproducible deploy)
└─ DR drill: Quarterly
```

### 10.4 Bảo Mật Dữ Liệu

```
At-Rest Encryption:
├─ PostgreSQL: Transparent Data Encryption (TDE) hoặc disk-level (LUKS)
├─ Redis: redis-encrypted (Enterprise) hoặc disk encryption
├─ MinIO/S3: Server-side encryption (AES-256)
├─ Oracle: Oracle TDE (managed by DBA)
├─ Secrets: HashiCorp Vault hoặc K8s Secrets (encrypted etcd)
└─ Audit logs: encrypted partition

In-Transit Encryption:
├─ All internal communication: mTLS (service mesh - Istio/Linkerd)
├─ User → API Gateway: TLS 1.3
├─ API Gateway → Services: mTLS
├─ Services → Oracle: Oracle Net encryption (SQLNET.ENCRYPTION_SERVER=REQUIRED)
├─ Services → Redis: TLS
└─ Services → PostgreSQL: SSL required

Network Security:
├─ Separate VLANs: DMZ (frontend), App (services), Data (databases)
├─ Firewall rules: whitelist-based
├─ No direct DB access from DMZ
├─ VPN required for admin access
└─ Egress filtering: services cannot call external endpoints 
   (except LLM API — whitelist specific domains)
```

### 10.5 Giám Sát Chi Phí LLM

```python
class CostMonitor:
    """
    Track and control LLM API costs.
    """
    
    PRICING = {
        "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
        "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
        "claude-sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    }
    
    # Budget controls
    DAILY_BUDGET_USD = 100.0
    PER_USER_DAILY_LIMIT_USD = 5.0
    ALERT_THRESHOLD_PCT = 80  # Alert at 80% of budget
    
    async def track_usage(self, user_id: str, model: str, 
                           input_tokens: int, output_tokens: int):
        cost = (input_tokens * self.PRICING[model]["input"] + 
                output_tokens * self.PRICING[model]["output"])
        
        # Atomic increment in Redis
        daily_key = f"cost:{datetime.now().strftime('%Y-%m-%d')}"
        user_key = f"cost:{user_id}:{datetime.now().strftime('%Y-%m-%d')}"
        
        daily_total = await redis.incrbyfloat(daily_key, cost)
        user_total = await redis.incrbyfloat(user_key, cost)
        
        if daily_total > self.DAILY_BUDGET_USD:
            await self._alert("CRITICAL: Daily LLM budget exceeded!")
            raise BudgetExceededError("Daily budget exceeded. Contact admin.")
        
        if user_total > self.PER_USER_DAILY_LIMIT_USD:
            raise BudgetExceededError(
                "Bạn đã sử dụng hết quota hôm nay. Vui lòng thử lại ngày mai."
            )
        
        if daily_total > self.DAILY_BUDGET_USD * self.ALERT_THRESHOLD_PCT / 100:
            await self._alert(f"WARNING: Daily budget at {daily_total/self.DAILY_BUDGET_USD*100:.0f}%")
```

### 10.6 Monitoring Dashboard

```
Grafana Dashboards:

1. System Overview:
   - Request rate, error rate, latency percentiles (p50, p95, p99)
   - Active users, concurrent sessions
   - LLM token usage, cost accumulation

2. AI Quality:
   - Intent classification accuracy (based on feedback)
   - SQL generation success rate
   - Guardrail trigger rate (input blocked, output flagged)
   - User feedback score (thumbs up/down ratio)
   - Hallucination detection rate

3. Database Performance:
   - Oracle query latency distribution
   - Connection pool utilization
   - Slow queries (> 5s)
   - Failed queries (timeout, error)

4. Security:
   - Blocked requests by type
   - Suspicious activity alerts
   - Failed authentication attempts
   - Cross-department access attempts

5. Cost:
   - Daily/weekly/monthly LLM spend
   - Cost per department
   - Cost per query type
   - Token efficiency (useful output / total tokens)
```

### 10.7 Rate Limit & Approval Workflow

```python
RATE_LIMITS = {
    "viewer":       {"rpm": 10,  "rpd": 100,  "max_export_per_day": 0},
    "dept_user":    {"rpm": 30,  "rpd": 500,  "max_export_per_day": 10},
    "dept_manager": {"rpm": 60,  "rpd": 1000, "max_export_per_day": 50},
    "admin":        {"rpm": 120, "rpd": 5000, "max_export_per_day": 100},
}

# Approval workflow for sensitive queries
APPROVAL_TRIGGERS = [
    # Queries touching salary/compensation data
    {"tables": ["HR_SALARY", "HR_COMPENSATION"], "requires": "hr_manager_approval"},
    # Queries returning > 5000 rows for export
    {"condition": "export AND rows > 5000", "requires": "dept_manager_approval"},
    # Cross-department queries
    {"condition": "cross_department", "requires": "admin_approval"},
    # Queries on restricted tables
    {"sensitivity": "restricted", "requires": "data_owner_approval"},
]
```

---

## 11. SO SÁNH PHƯƠNG ÁN KIẾN TRÚC

### 11.1 LLM Deployment: API vs. Self-hosted

| Tiêu chí | Cloud API (OpenAI/Anthropic) | Self-hosted (vLLM + open model) |
|-----------|-----------------------------|---------------------------------|
| Chi phí ban đầu | Thấp (pay-per-use) | Cao (GPU servers) |
| Chi phí dài hạn | Tăng theo usage | Cố định (amortized) |
| Bảo mật dữ liệu | Data gửi ra ngoài | Data ở nội bộ |
| Hiệu năng | Ổn định, low latency | Phụ thuộc hardware |
| Độ chính xác (Text-to-SQL) | GPT-4o/Claude rất tốt | Open models kém hơn ~10-15% |
| Customization | Limited (fine-tuning tốn kém) | Full control (LoRA, fine-tune) |
| Compliance | Cần đánh giá DPA | Đáp ứng tốt yêu cầu nội bộ |

**Đề xuất**: Bắt đầu với Cloud API (GPT-4o hoặc Claude) cho MVP. Song song evaluate self-hosted option (Qwen2.5-72B hoặc Llama 3.1-70B) để chuyển đổi nếu cần compliance strict hoặc chi phí quá cao. Nếu doanh nghiệp thuộc ngành tài chính/ngân hàng với yêu cầu dữ liệu không ra ngoài → ưu tiên self-hosted ngay từ đầu.

### 11.2 Vector Store

| Tiêu chí | Milvus | pgvector | Weaviate | Qdrant |
|-----------|--------|----------|----------|--------|
| Scale | Tốt (distributed) | TB (single node) | Tốt | Tốt |
| Filtering | Tốt | SQL-native | Tốt | Tốt |
| Hybrid search | Có | Limited | Có | Có |
| Ops complexity | Cao | Thấp (dùng PG sẵn) | TB | TB |
| Enterprise ready | Có (Zilliz Cloud) | Có | Có | TB |

**Đề xuất**: pgvector nếu đã có PostgreSQL và document volume < 1M chunks. Milvus nếu volume lớn hoặc cần hybrid search tốt.

### 11.3 Orchestration Framework

| Tiêu chí | LangGraph | LangChain Agent | Custom (FastAPI) | Haystack |
|-----------|-----------|-----------------|------------------|----------|
| Flow control | Tường minh | Implicit | Full control | Tường minh |
| Debugging | Tốt (LangSmith) | Khó | Tự implement | TB |
| Guardrail integration | Dễ (add node) | Khó | Tự implement | TB |
| Learning curve | TB | Thấp | Thấp | TB |
| Production stability | TB | TB (breaking changes) | Cao | Tốt |
| Vendor lock-in | LangChain ecosystem | LangChain ecosystem | Không | Haystack |

**Đề xuất**: LangGraph cho orchestration logic, FastAPI cho API layer. Tránh dùng LangChain Agent mode cho production vì khó kiểm soát flow và debug.

---

## 12. STACK CÔNG NGHỆ ĐỀ XUẤT

### 12.1 Core Stack

```
FRONTEND:
  ├─ Chat UI:         React + TypeScript + TanStack Query
  ├─ UI Components:   Ant Design (phù hợp enterprise)
  ├─ Charts:          ECharts (rich chart types, good for dashboards)
  ├─ Tables:          ag-Grid Community (sorting, filtering, export)
  └─ Admin Panel:     React Admin hoặc custom React

BACKEND:
  ├─ API Framework:   FastAPI (Python) — async, typed, fast
  ├─ AI Orchestration: LangGraph
  ├─ Task Queue:      Celery + Redis (for async jobs: export, forecasting)
  ├─ Workflow:        Temporal (optional, for complex approval flows)
  └─ WebSocket/SSE:   FastAPI StreamingResponse (for chat streaming)

AI / ML:
  ├─ LLM:             GPT-4o (primary) + GPT-4o-mini (for classification, simple tasks)
  │                    OR Claude 3.5 Sonnet / Claude Opus 4 (alternative)
  ├─ Embedding:       text-embedding-3-large (OpenAI) OR BGE-M3 (self-hosted, multilingual)
  ├─ Reranker:        BGE-reranker-v2-m3 (self-hosted) OR Cohere Rerank
  ├─ SQL Parser:      sqlglot (Python, multi-dialect)
  ├─ Forecasting:     Prophet + statsmodels
  ├─ Anomaly:         scikit-learn (IsolationForest) + custom z-score
  └─ Doc Processing:  Unstructured.io OR LlamaParse OR Docling

DATA STORES:
  ├─ Primary DB:      PostgreSQL 16 (metadata, config, audit, permissions)
  ├─ Cache + Session: Redis 7 (Cluster mode for HA)
  ├─ Vector Store:    Milvus 2.x OR pgvector (if volume small)
  ├─ Document Store:  MinIO (S3-compatible, on-premise)
  ├─ Search/Log:      OpenSearch / ELK (audit log search, analytics)
  └─ Source DBs:      Oracle (existing, read replicas)

AUTH & SECURITY:
  ├─ IdP:             Keycloak 24+ (OIDC, SAML, LDAP federation)
  ├─ Policy Engine:   OPA (Open Policy Agent) — hoặc bắt đầu với code-based
  ├─ Secret Mgmt:     HashiCorp Vault OR K8s Sealed Secrets
  └─ API Gateway:     Kong Gateway OR Apache APISIX

INFRASTRUCTURE:
  ├─ Container:       Docker + Kubernetes
  ├─ CI/CD:           GitLab CI OR Jenkins + ArgoCD
  ├─ Monitoring:      Prometheus + Grafana
  ├─ Logging:         Fluentd/Fluent-bit → OpenSearch
  ├─ Tracing:         Jaeger OR OpenTelemetry
  └─ IaC:             Terraform + Helm charts
```

---

## 13. LỘ TRÌNH TRIỂN KHAI

### Phase 1: MVP (8-10 tuần)

```
Mục tiêu: Chatbot có thể trả lời câu hỏi dữ liệu cơ bản cho 1 phòng ban pilot

Tuần 1-2: Foundation
  ├─ Setup infrastructure (K8s, PostgreSQL, Redis)
  ├─ Setup Keycloak + LDAP integration
  ├─ Setup FastAPI project structure
  ├─ Basic Chat UI (React)
  └─ API Gateway (Kong basic setup)

Tuần 3-4: Semantic Layer + Metadata
  ├─ Thiết kế metadata catalog cho 1 schema pilot
  ├─ Định nghĩa 10-15 KPI chính
  ├─ Viết 30-50 sample questions + expected SQL
  ├─ Setup Oracle read replica connection
  └─ Implement connection pool + query executor

Tuần 5-6: AI Pipeline (Core)
  ├─ Intent classifier (LLM-based)
  ├─ Text-to-SQL generator (with semantic context)
  ├─ SQL validator (whitelist tables, block dangerous patterns)
  ├─ Row-level filter injection
  ├─ Response formatter (table + text)
  └─ Basic input guardrails (regex + pattern matching)

Tuần 7-8: Auth + Audit
  ├─ JWT-based authentication flow
  ├─ Permission loading from config/DB
  ├─ Audit logging (PostgreSQL)
  ├─ Basic session memory (Redis)
  └─ Error handling + retry logic

Tuần 9-10: Testing + Polish
  ├─ End-to-end testing with real data
  ├─ SQL safety testing (adversarial prompts)
  ├─ Performance testing
  ├─ UI polish
  └─ Documentation

Deliverables:
  ✓ Chat interface for 1 dept (e.g., Sales)
  ✓ 15+ KPIs queryable via natural language
  ✓ Basic RBAC (dept-level)
  ✓ Audit log
  ✓ SQL validation
  ✓ Session memory (current conversation)
```

### Phase 2: Pilot (6-8 tuần)

```
Mục tiêu: Mở rộng cho 2-3 phòng ban, thêm RAG + export

Tuần 1-2: Multi-schema Support
  ├─ Thêm 2-3 schemas (HR, Finance)
  ├─ Mở rộng metadata catalog
  ├─ Cross-schema query planning (app-level merge)
  └─ Column-level security + data masking

Tuần 3-4: RAG Pipeline
  ├─ Document ingestion pipeline
  ├─ Vector store setup (Milvus/pgvector)
  ├─ Embedding + chunking strategy
  ├─ Namespace-based access control
  └─ Hybrid retrieval (vector + keyword)

Tuần 5-6: Export + Advanced Features
  ├─ Export to Excel/PDF
  ├─ Chart generation (ECharts)
  ├─ Long-term memory (conversation summaries)
  ├─ Favorite queries / bookmarks
  └─ Admin panel (user mgmt, metadata mgmt)

Tuần 7-8: Security Hardening
  ├─ LLM-based injection classifier
  ├─ Output guardrails (hallucination check, PII check)
  ├─ Multi-turn escalation detection
  ├─ Penetration testing
  ├─ Performance optimization (caching, query optimization)
  └─ Monitoring setup (Grafana dashboards)

Deliverables:
  ✓ 3 departments onboarded
  ✓ RAG for department documents
  ✓ Export (Excel, PDF)
  ✓ Charts/visualizations
  ✓ Row + column level security
  ✓ Data masking
  ✓ LLM-based guardrails
  ✓ Admin panel
  ✓ Monitoring
```

### Phase 3: Production (8-12 tuần)

```
Mục tiêu: Production-ready, tất cả phòng ban, analytics nâng cao

Tuần 1-3: Scale + HA
  ├─ All departments onboarded
  ├─ HA setup (Redis Cluster, PG replication)
  ├─ Load testing + capacity planning
  ├─ DR plan + backup automation
  └─ Rate limiting + quota management

Tuần 4-6: Analytics & Forecasting
  ├─ Forecasting engine (Prophet)
  ├─ Anomaly detection
  ├─ Trend analysis
  ├─ Scheduled reports
  └─ Explainability for analytics results

Tuần 7-9: Governance & Compliance
  ├─ OPA policy engine integration
  ├─ Approval workflow for sensitive queries
  ├─ Cost monitoring + budget controls
  ├─ Inference attack prevention
  ├─ Comprehensive audit reporting
  └─ Compliance documentation

Tuần 10-12: Optimization
  ├─ Fine-tune LLM prompts based on feedback data
  ├─ Optimize cache hit rate
  ├─ Reduce token usage (prompt compression)
  ├─ A/B testing framework for prompt variants
  ├─ User training + documentation
  └─ Operational runbook

Deliverables:
  ✓ All departments live
  ✓ Forecasting + anomaly detection
  ✓ Scheduled reports
  ✓ HA/DR tested
  ✓ Full governance framework
  ✓ Cost under control
  ✓ < 5s average response time
  ✓ > 90% user satisfaction
```

---

## 14. CHECKLIST RỦI RO

### 14.1 Rủi Ro Kỹ Thuật

| # | Rủi ro | Xác suất | Impact | Mitigation |
|---|--------|----------|--------|------------|
| 1 | LLM sinh SQL sai → báo cáo sai số liệu | Cao | Cao | Semantic layer + template SQL ưu tiên; hallucination check; user feedback loop |
| 2 | Prompt injection bypass guardrails | TB | Cao | Multi-layer defense (regex + LLM classifier + SQL validator); red-team testing định kỳ |
| 3 | Oracle query quá nặng → ảnh hưởng production | TB | Cao | Read replica bắt buộc; Resource Manager; EXPLAIN PLAN check; timeout |
| 4 | Data leakage giữa phòng ban | Thấp | Rất cao | Row-level filter injection; output guardrail; audit; penetration test |
| 5 | LLM API downtime | Thấp | Cao | Fallback model (GPT-4o → GPT-4o-mini → template-only mode); retry with exponential backoff |
| 6 | Token cost vượt budget | TB | TB | Per-user quota; daily budget; cost monitoring; prompt optimization |
| 7 | Context window overflow | TB | TB | Smart context management; summarization; relevant-only inclusion |
| 8 | Schema changes break queries | Cao | TB | Metadata catalog versioning; automated testing after schema update; alerts |

### 14.2 Rủi Ro Tổ Chức

| # | Rủi ro | Mitigation |
|---|--------|------------|
| 1 | User không tin kết quả AI | Luôn show SQL + nguồn dữ liệu + logic tính toán; cho phép verify thủ công |
| 2 | Phòng ban không cung cấp đủ metadata/KPI definition | Phân công data steward mỗi phòng ban; template chuẩn; workshop |
| 3 | Resistance to change | Training; demo value early; champion users; gradual rollout |
| 4 | DBA team không hỗ trợ read replica | Escalate lên CTO/CIO; document performance impact nếu query production |
| 5 | Compliance/legal concerns | Involve legal team early; document data flow; DPA with LLM vendor |

---

## 15. USE CASE THỰC TẾ

### 15.1 Phòng Kinh Doanh

**User (Trưởng phòng KD miền Bắc)**: "Doanh thu tuần này so với tuần trước thế nào? Chi tiết theo từng chi nhánh."

```
System Processing:
1. Intent: sql_query + comparison
2. Entities: metric=revenue, period=this_week vs last_week, dimension=branch
3. Permission: region=NORTH → auto-filter MA_KV='NORTH'
4. SQL (via template):
   WITH this_week AS (
     SELECT MA_CN, SUM(DOANH_THU_RONG) AS dt
     FROM SALES.DM_DOANH_THU
     WHERE NGAY_GD >= TRUNC(SYSDATE, 'IW')
       AND MA_KV = 'NORTH'
     GROUP BY MA_CN
   ), last_week AS (
     SELECT MA_CN, SUM(DOANH_THU_RONG) AS dt
     FROM SALES.DM_DOANH_THU
     WHERE NGAY_GD >= TRUNC(SYSDATE, 'IW') - 7
       AND NGAY_GD < TRUNC(SYSDATE, 'IW')
       AND MA_KV = 'NORTH'
     GROUP BY MA_CN
   )
   SELECT t.MA_CN, CN.TEN_CN,
          t.dt AS doanh_thu_tuan_nay,
          l.dt AS doanh_thu_tuan_truoc,
          ROUND((t.dt - l.dt) / NULLIF(l.dt, 0) * 100, 1) AS tang_truong_pct
   FROM this_week t
   LEFT JOIN last_week l ON t.MA_CN = l.MA_CN
   LEFT JOIN SALES.DM_CHI_NHANH CN ON t.MA_CN = CN.MA_CN
   ORDER BY tang_truong_pct DESC

5. Response:
   "Doanh thu tuần này (14-20/3) đạt 2.3 tỷ, tăng 5.2% so với tuần trước.
   
   Chi tiết theo chi nhánh:
   | Chi nhánh    | Tuần này    | Tuần trước  | Tăng trưởng |
   |-------------|-------------|-------------|-------------|
   | Hà Nội      | 980 triệu  | 900 triệu  | +8.9%       |
   | Hải Phòng   | 650 triệu  | 680 triệu  | -4.4%       |
   | Quảng Ninh  | 420 triệu  | 380 triệu  | +10.5%      |
   | Nam Định    | 250 triệu  | 230 triệu  | +8.7%       |
   
   📊 [Biểu đồ cột so sánh]
   
   Nguồn: SALES.DM_DOANH_THU | Cập nhật: 20/3/2024 23:59"
```

### 15.2 Phòng Nhân Sự

**User (Trưởng phòng HR)**: "Tỷ lệ nghỉ việc 3 tháng gần nhất có bất thường gì không?"

```
System Processing:
1. Intent: analytics + anomaly_detection
2. Pipeline: Text-to-SQL → fetch data → Anomaly detection → Response
3. SQL: Query turnover rate monthly from HR schema
4. Analytics: Z-score analysis on monthly turnover rate
5. Response:
   "Tỷ lệ nghỉ việc 3 tháng gần nhất:
   - Tháng 1: 2.1% (bình thường)
   - Tháng 2: 2.3% (bình thường)  
   - Tháng 3: 4.8% ⚠️ (BẤT THƯỜNG - cao hơn 2.5 lần trung bình 12 tháng)
   
   Phân tích chi tiết tháng 3:
   - Phòng IT: 8 người nghỉ (vs trung bình 2/tháng) ← điểm bất thường chính
   - Phòng KD: 5 người nghỉ (vs trung bình 3/tháng) 
   - Các phòng khác: bình thường
   
   Đề xuất: Kiểm tra lại phòng IT - có thể có vấn đề về 
   môi trường làm việc hoặc cạnh tranh tuyển dụng từ bên ngoài."
```

### 15.3 Phòng Tài Chính

**User (Kế toán trưởng)**: "Dự báo dòng tiền tháng tới dựa trên xu hướng 6 tháng gần đây."

```
System Processing:
1. Intent: analytics + forecasting
2. Pipeline: Text-to-SQL (fetch 6 months cashflow) → Prophet forecasting → Response
3. Response includes:
   - Predicted cashflow value + confidence interval
   - Seasonal pattern explanation
   - Key factors affecting forecast
   - Comparison with same period last year
   - Visual: line chart with forecast band
```

### 15.4 Câu Hỏi Về Tài Liệu (RAG)

**User (Nhân viên KD)**: "Chính sách chiết khấu cho khách hàng VIP hiện tại là gì?"

```
System Processing:
1. Intent: rag_search
2. RAG pipeline:
   - Search in namespace: dept_sales + common
   - Retrieved chunks from "Chinh_sach_chiet_khau_2024_Q1.pdf"
   - Reranked → top 3 relevant chunks
3. Response:
   "Theo Chính sách chiết khấu Q1/2024 (cập nhật 15/01/2024):
   
   Khách hàng VIP (doanh số ≥ 500 triệu/quý):
   - Chiết khấu cơ bản: 8%
   - Thêm 2% nếu thanh toán trong 15 ngày
   - Thêm 1% cho đơn hàng ≥ 100 triệu
   - Tối đa: 11%
   
   📎 Nguồn: Chinh_sach_chiet_khau_2024_Q1.pdf, trang 5-6
   ⚠️ Lưu ý: Đây là chính sách Q1. Vui lòng kiểm tra với quản lý 
   nếu cần chính sách mới nhất."
```

---

## 16. BEST PRACTICES & SAI LẦM CẦN TRÁNH

### 16.1 Best Practices

**Semantic Layer là yếu tố quyết định thành bại**: Đầu tư 30-40% effort vào việc xây dựng metadata catalog, KPI definitions, sample questions. LLM chỉ tốt khi có context tốt. Một semantic layer nghèo nàn = SQL sai liên tục = mất niềm tin user.

**Defense in depth cho security**: Không bao giờ tin một layer duy nhất. Input guardrail CÓ THỂ bị bypass → SQL validator phải catch. SQL validator CÓ THỂ miss → row-level filter phải enforce ở mức query. Output guardrail là lớp bảo vệ cuối.

**Read replica là bắt buộc, không phải optional**: Không bao giờ cho chatbot query trực tiếp production DB. Một query sai có thể lock bảng, tốn resource, ảnh hưởng giao dịch.

**Bắt đầu với template SQL, mở rộng dần sang freeform**: Template SQL cho 80% câu hỏi thường gặp (an toàn, nhanh, chính xác). Guided text-to-SQL cho 15% câu hỏi ad-hoc. 5% câu hỏi phức tạp → đề xuất user liên hệ BI team.

**Feedback loop là bắt buộc**: Thumbs up/down cho mỗi câu trả lời. Weekly review kết quả sai → cải thiện prompt/semantic layer. Monthly eval accuracy trên test set.

**Log ENOUGH nhưng đừng log SENSITIVE**: Log question, intent, SQL, latency, token count → YES. Log full query results (chứa dữ liệu kinh doanh) → NO. Log chỉ summary (row count, column names) → YES.

**Giải thích kết quả luôn đi kèm**: User nghiệp vụ cần biết "số này từ đâu ra". Luôn show: nguồn dữ liệu, SQL đã dùng (nếu user muốn xem), logic tính toán KPI, thời điểm dữ liệu cập nhật, caveats/limitations.

### 16.2 Sai Lầm Cần Tránh

**Sai lầm 1: Cho LLM truy cập toàn bộ schema information**. LLM không cần biết tất cả 500 tables. Chỉ cung cấp tables/columns liên quan đến câu hỏi + thuộc quyền user. Cung cấp quá nhiều context = tốn token + tăng risk hallucination + tăng risk data leak.

**Sai lầm 2: Tin tưởng SQL do LLM sinh ra mà không validate**. LLM THƯỜNG XUYÊN sinh SQL có logic sai (sai điều kiện join, quên GROUP BY, sai hàm aggregate). Phải có SQL validator + kết quả phải sanity-check với expected range.

**Sai lầm 3: Dùng LangChain Agent mode cho production**. Agent mode cho LLM tự quyết tool calling → không kiểm soát được flow → khó debug → khó đảm bảo security. Dùng explicit state machine (LangGraph) thay thế.

**Sai lầm 4: Cache không tính đến user scope**. Cache key phải bao gồm user's data scope. Nếu không, user A query "doanh thu tháng này" → cache → user B (khác region) lấy từ cache → xem sai dữ liệu.

**Sai lầm 5: Không có plan cho schema changes**. Oracle schema SỐNG và THAY ĐỔI. Thêm cột, đổi tên bảng, thêm view → semantic layer phải update → sample SQL phải update. Cần automation: detect schema changes → alert → update metadata.

**Sai lầm 6: Cố gắng làm chatbot trả lời mọi thứ**. Chatbot KHÔNG nên thay thế BI dashboard hoặc data analyst. Scope rõ ràng: câu hỏi dữ liệu định lượng, tra cứu tài liệu, phân tích trend cơ bản. Câu hỏi phức tạp → escalate đến BI team.

**Sai lầm 7: Bỏ qua UX cho user nghiệp vụ**. User không phải data engineer. Nếu chatbot trả lời "Error: ORA-01722: invalid number" thì vô nghĩa. Phải translate mọi error thành ngôn ngữ người dùng: "Xin lỗi, tôi không thể truy vấn dữ liệu này. Vui lòng thử lại hoặc liên hệ support."

**Sai lầm 8: Deploy xong rồi mới nghĩ đến monitoring**. Monitoring setup phải ĐI CÙNG application code từ Sprint 1. Bạn không thể tối ưu cái bạn không đo lường được.

---

## PHỤ LỤC

### A. Checklist Triển Khai MVP

```
□ Infrastructure
  □ K8s cluster provisioned
  □ PostgreSQL deployed + initialized
  □ Redis deployed
  □ MinIO/S3 bucket created
  □ Oracle read replica accessible
  □ Network connectivity verified

□ Authentication
  □ Keycloak deployed
  □ LDAP federation configured
  □ Realm + clients created
  □ Test users created with different roles

□ Semantic Layer
  □ Metadata catalog tables created
  □ At least 1 schema fully documented
  □ 10+ KPIs defined with SQL formulas
  □ 30+ sample questions with expected SQL
  □ Row-level filter rules defined

□ AI Pipeline
  □ LLM API key configured
  □ Intent classifier tested (90%+ accuracy on test set)
  □ Text-to-SQL tested on sample questions (85%+ accuracy)
  □ SQL validator implemented and tested
  □ Row-level filter injection verified
  □ Input guardrails active
  □ Output guardrails active

□ Security
  □ JWT validation working
  □ Permission loading from DB
  □ SQL whitelist enforced
  □ System tables blocked
  □ Audit logging active
  □ TLS everywhere

□ Testing
  □ Unit tests: guardrails, SQL validator, permission enforcer
  □ Integration tests: full flow from question to answer
  □ Adversarial tests: 50+ prompt injection attempts blocked
  □ Performance tests: < 5s for simple queries
  □ Data accuracy tests: compare chatbot vs manual query

□ Documentation
  □ API documentation
  □ Admin guide
  □ User guide
  □ Security documentation
  □ Runbook for operations
```

### B. Oracle-Specific Considerations

```sql
-- 1. Create dedicated read-only user for chatbot
CREATE USER chatbot_readonly IDENTIFIED BY "<strong-password>";
GRANT CREATE SESSION TO chatbot_readonly;

-- 2. Grant SELECT only on specific schemas/tables
GRANT SELECT ON SALES.DM_DOANH_THU TO chatbot_readonly;
GRANT SELECT ON SALES.DM_SAN_PHAM TO chatbot_readonly;
GRANT SELECT ON SALES.DM_CHI_NHANH TO chatbot_readonly;
-- ... (whitelist each table explicitly)

-- 3. Create resource consumer group
BEGIN
  DBMS_RESOURCE_MANAGER.CREATE_CONSUMER_GROUP(
    consumer_group => 'CHATBOT_LOW',
    comment => 'Low priority for chatbot queries'
  );
END;
/

-- 4. Set resource limits
BEGIN
  DBMS_RESOURCE_MANAGER.CREATE_PLAN_DIRECTIVE(
    plan => 'DEFAULT_PLAN',
    group_or_subplan => 'CHATBOT_LOW',
    max_utilization_limit => 10,        -- Max 10% CPU
    parallel_degree_limit_p1 => 2,      -- Max parallelism
    switch_time => 30,                   -- Kill after 30 sec
    switch_group => 'CANCEL_SQL'
  );
END;
/

-- 5. Map chatbot user to consumer group
BEGIN
  DBMS_RESOURCE_MANAGER.SET_CONSUMER_GROUP_MAPPING(
    attribute => DBMS_RESOURCE_MANAGER.ORACLE_USER,
    value => 'CHATBOT_READONLY',
    consumer_group => 'CHATBOT_LOW'
  );
END;
/

-- 6. Oracle Net encryption (sqlnet.ora on client side)
-- SQLNET.ENCRYPTION_CLIENT = REQUIRED
-- SQLNET.ENCRYPTION_TYPES_CLIENT = (AES256)
```

---

*Tài liệu này cung cấp blueprint kiến trúc đủ chi tiết để đội ngũ kỹ thuật bắt đầu thiết kế và triển khai. Các phần cụ thể (prompt templates, detailed API specs, deployment manifests) sẽ được elaborated trong tài liệu thiết kế chi tiết (Detailed Design Document) cho từng component.*
