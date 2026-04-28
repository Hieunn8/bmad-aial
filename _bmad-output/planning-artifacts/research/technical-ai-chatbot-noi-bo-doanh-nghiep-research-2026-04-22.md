---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: ["requirement.txt"]
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Enterprise Internal AI Chatbot - Data Q&A, Analytics, Reporting từ Oracle DB'
research_goals: 'Thiết kế end-to-end hệ thống AI Chatbot nội bộ doanh nghiệp: phân quyền RBAC/ABAC, text-to-SQL Oracle multi-schema, RAG tài liệu nội bộ, session memory, AI safety guardrails, forecasting/analytics, audit logging'
user_name: 'Admin'
date: '2026-04-22'
web_research_enabled: true
source_verification: true
---

# Research Report: Enterprise Internal AI Chatbot

**Date:** 2026-04-22
**Author:** Admin
**Research Type:** Technical

---

## Research Overview

**Chủ đề:** Enterprise Internal AI Chatbot — Hỏi đáp dữ liệu, thống kê, báo cáo, phân tích & dự báo từ Oracle DB đa nguồn

**Phương pháp:** Web search đa nguồn, cross-validation, confidence-level framework. Tất cả technical claims được verify qua ít nhất 2 nguồn độc lập.

**Phạm vi:** Architecture design, security/RBAC, Text-to-SQL, RAG, session memory, forecasting, AI safety, technology stack, deployment roadmap.

---

## Technical Research Scope Confirmation

**Research Topic:** Enterprise Internal AI Chatbot — Data Q&A, Analytics, Reporting từ Oracle DB đa nguồn

**Research Goals:** Thiết kế end-to-end hệ thống AI Chatbot nội bộ doanh nghiệp: phân quyền RBAC/ABAC, text-to-SQL an toàn trên Oracle multi-DB/multi-schema, RAG tài liệu nội bộ, session memory, AI safety guardrails, forecasting/analytics, audit logging, export báo cáo.

**Technical Research Scope:**

- Architecture Analysis — design patterns, frameworks, system architecture
- Implementation Approaches — development methodologies, coding patterns
- Technology Stack — languages, frameworks, tools, platforms
- Integration Patterns — APIs, protocols, interoperability
- Performance Considerations — scalability, optimization, patterns

**Research Methodology:**

- Current web data với rigorous source verification
- Multi-source validation cho critical technical claims
- Confidence level framework cho uncertain information
- Comprehensive technical coverage với architecture-specific insights

**Scope Confirmed:** 2026-04-22

---

## Technology Stack Analysis

### 1. AI/LLM Layer

**LLM Options (Confidence: HIGH — verified qua multiple enterprise deployments 2025-2026):**

| Model | Provider | Dùng cho | Điểm mạnh |
|-------|----------|----------|-----------|
| claude-sonnet-4-6 | Anthropic | Main reasoning, SQL gen | Coding + safety, 200K context |
| claude-opus-4-7 | Anthropic | Complex analysis, forecasting | Deepest reasoning |
| GPT-4o | OpenAI | Fallback/backup | Function calling mạnh |
| LLaMA 3.x 70B+ | Meta (self-host) | On-premise, air-gapped | Full data control |
| Qwen2.5-72B | Alibaba | On-premise alternative | Multilingual, cost-effective |

**Khuyến nghị:** Dùng Claude Sonnet 4.6 làm primary (tốt nhất cho coding + SQL generation theo Anthropic benchmarks 2026). Giữ LLaMA 3 làm on-premise fallback nếu data sensitivity cao.

_Source: [Oracle AI Database 26ai announcement](https://blogs.oracle.com/database/oracle-announces-oracle-ai-database-26ai), [Enterprise Chatbots 2026](https://www.kernshell.com/building-enterprise-chatbots-with-conversational-ai-in-2026/)_

---

### 2. AI Orchestration & Agent Framework

**Framework Comparison (Confidence: HIGH):**

| Framework | Strengths | Weaknesses | Dùng khi nào |
|-----------|-----------|------------|--------------|
| **LangGraph** (LangChain) | Multi-agent workflows, stateful graphs, tool routing | Learning curve | Complex multi-step reasoning, agent coordination |
| **LlamaIndex** | RAG-optimized, 35% better retrieval vs LangChain (2025 benchmarks), query planning | Less flexible for agent chains | Document-heavy RAG, multi-index routing |
| **Haystack** (deepset) | Production-ready pipelines, declarative | Smaller community | Pipeline-centric architectures |
| **Semantic Kernel** | Microsoft ecosystem, .NET/Python | Microsoft lock-in | Azure-native deployments |
| **Custom** | Full control | High maintenance | When frameworks don't fit |

**Khuyến nghị:** Kết hợp **LlamaIndex** (cho RAG/retrieval) + **LangGraph** (cho agent orchestration và multi-step SQL planning). Pattern này đang được dùng rộng rãi nhất trong enterprise 2025.

_Source: [LangChain vs LlamaIndex 2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langchain-vs-llamaindex-2025-complete-rag-framework-comparison), [LlamaIndex Complete Guide](https://galileo.ai/blog/llamaindex-complete-guide-rag-data-workflows-llms)_

---

### 3. Semantic Layer & Text-to-SQL Stack

**Phương án A: Direct Text-to-SQL (không có Semantic Layer)**
- LLM nhận schema metadata → sinh SQL trực tiếp
- Ưu: đơn giản, ít component
- Nhược: hallucination cao, khó kiểm soát, SQL phức tạp dễ sai, security risk cao

**Phương án B: Semantic Layer + Text-to-SQL (KHUYẾN NGHỊ)**
- User query → Semantic Layer (business terms) → SQL generation → Validated query → Oracle
- Accuracy có thể đạt 90%+ với headless semantic layer (VentureBeat 2025)

**Semantic Layer Tools:**

| Tool | License | Điểm mạnh | Phù hợp |
|------|---------|-----------|---------|
| **Cube.dev (Cube Cloud)** | Open source + SaaS | REST/GraphQL API, caching built-in, headless | Production enterprise, API-first |
| **dbt MetricFlow** | Open source (Apache 2.0) | Git-based, version controlled metrics | Data team centric, dbt ecosystem |
| **AtScale** | Commercial | Enterprise, OLAP acceleration | Large-scale BI |
| **Custom YAML Catalog** | Internal | Full control, Oracle-specific | Khi các tool trên không fit |

**Khuyến nghị:** **Cube.dev** làm semantic layer headless API + custom business glossary YAML cho Oracle-specific KPIs.

_Source: [Headless Semantic Layer VentureBeat](https://venturebeat.com/ai/headless-vs-native-semantic-layer-the-architectural-key-to-unlocking-90-text), [Semantic Layer Architectures 2025](https://www.typedef.ai/resources/semantic-layer-architectures-explained-warehouse-native-vs-dbt-vs-cube)_

---

### 4. RAG & Vector Database

**Vector DB Comparison (Confidence: HIGH):**

| DB | License | RBAC | Self-host | Phù hợp Enterprise |
|----|---------|------|-----------|-------------------|
| **Weaviate** | Open source | Yes (RBAC built-in) | Yes | Tốt nhất cho enterprise security |
| **Qdrant** | Open source | Yes | Yes | High performance, Rust-based |
| **pgvector** | Open source | Qua PostgreSQL | Yes | Nếu đã có Postgres infra |
| **Chroma** | Open source | Hạn chế | Yes | Dev/prototype |
| **Azure AI Search** | Commercial | Document-level RBAC | Azure | Azure ecosystem |
| **Elasticsearch** | Commercial | Yes | Yes | Nếu đã có ELK stack |

**Khuyến nghị:** **Weaviate** (self-hosted) cho production vì có native RBAC + document-level ACL phù hợp yêu cầu multi-department isolation.

**Document Processing Stack:**
- PDF/DOCX parsing: `unstructured.io` hoặc `pypdf2` + `python-docx`
- Chunking: Recursive chunking với overlap, semantic chunking cho accuracy cao hơn
- Embedding: `text-embedding-3-large` (OpenAI) hoặc `bge-m3` (BAAI, open source, multilingual)

_Source: [Securing Internal RAG Systems](https://dasroot.net/posts/2026/03/securing-internal-rag-systems-enterprises/), [RAG & RBAC Elasticsearch](https://www.elastic.co/search-labs/blog/rag-and-rbac-integration)_

---

### 5. Security & Access Control Stack

**Layered Security Model (2025 Enterprise Best Practice — Confidence: HIGH):**

Theo research từ Cerbos, Petronella Cybersecurity, và Oracle Deep Data Security 2026:

```
Layer 1: Authentication    → Keycloak (LDAP/AD integration, OIDC, JWT)
Layer 2: Authorization     → Cerbos (ABAC/RBAC policy engine, OPA alternative)
Layer 3: Data Access       → Oracle VPD + Row-Level Security (RLS)
Layer 4: Query Validation  → Custom SQL validator + whitelist
Layer 5: Result Sanitizer  → PII detection + data masking before LLM response
Layer 6: Audit Logging     → Immutable audit trail (PostgreSQL + event streaming)
```

**Key findings:**
- RBAC alone không đủ cho AI agents — cần **ABAC** (Attribute-Based) để handle dynamic context như "user thuộc region X chỉ xem data region X trong business hours"
- **Identity passthrough**: mỗi LLM query phải carry user identity, không dùng shared service account
- **Cerbos** là policy engine mạnh nhất cho RAG RBAC hiện tại (2025), support query plan filtering trước khi vector search
- **Oracle VPD (Virtual Private Database)** enforce RLS ngay tại DB layer — LLM không thể bypass dù SQL được inject

**ABAC Policy Example (Rego/OPA-style):**
```
allow if {
  user.department == data.department
  user.clearance >= data.sensitivity_level
  time.now() within user.allowed_hours
  not data.requires_approval
}
```

_Source: [Policy-as-Code for AI Security](https://petronellatech.com/blog/beyond-rbac-policy-as-code-to-secure-llms-vector-dbs-and-ai-agents/), [Oracle Deep Data Security 26ai](https://blogs.oracle.com/database/introducing-oracle-deep-data-security-identity-aware-data-access-control-for-agentic-ai-in-oracle-ai-database-26ai), [Cerbos RAG RBAC](https://www.cerbos.dev/blog/access-control-for-rag-llms)_

---

### 6. Oracle Data Connector Stack

**Connection Layer:**

| Component | Technology | Ghi chú |
|-----------|-----------|---------|
| Oracle driver | `cx_Oracle` / `python-oracledb` (Oracle official) | Python; hỗ trợ Oracle 12c+ |
| Connection pool | SQLAlchemy + Oracle dialect | ORM + raw SQL support |
| Multi-schema routing | Custom DataSourceRouter service | Route query đến đúng DB/schema theo user context |
| Query executor | Async (asyncpg pattern) | Non-blocking I/O |
| VPD enforcement | Oracle Virtual Private Database | RLS tại DB level, không bypass được |
| Query timeout | `cx_Oracle statement_cache_size` + query governor | Chống full scan |

**Multi-DB/Multi-Schema Strategy:**
```
DataSourceRegistry:
  - source_id: "erp_oracle_prod"
    host: erp-db.internal
    port: 1521
    service: ERPDB
    allowed_schemas: ["HR", "FINANCE"]
    allowed_roles: ["hr_manager", "finance_analyst"]
    
  - source_id: "sales_oracle_prod"  
    host: sales-db.internal
    port: 1521
    service: SALESDB
    allowed_schemas: ["SALES", "CUSTOMER"]
    allowed_roles: ["sales_manager", "regional_director"]
```

**Oracle 23ai Select AI (Native Option):**
Oracle AI Database 26ai có native Select AI hỗ trợ NL2SQL, RAG, và agent workflows ngay trong database. Nếu đang dùng Oracle 23ai+, đây là option đáng xem xét để giảm infrastructure complexity.

_Source: [Oracle Select AI](https://www.oracle.com/autonomous-database/select-ai/), [Oracle Deep Data Security](https://blogs.oracle.com/database/introducing-oracle-deep-data-security-identity-aware-data-access-control-for-agentic-ai-in-oracle-ai-database-26ai)_

---

### 7. Session Memory & Conversation History Stack

**Memory Architecture (Confidence: HIGH — verified qua Mem0, AWS samples, Temporal.io 2025):**

```
Short-term Memory  → Redis (in-memory, TTL 24h, current session)
Medium-term Memory → PostgreSQL (compressed summaries, last 30 sessions)
Long-term Memory   → PostgreSQL + Vector search (user preferences, frequent queries)
Audit Log          → Immutable append-only store (separate from memory)
```

**Thực tế từ research:**
- Mem0 (2025) cắt giảm 80-90% token cost trong khi vẫn tăng response quality 26% so với full history injection
- Hierarchical memory với summarization là pattern phổ biến nhất trong enterprise 2025
- **Không nên inject toàn bộ history vào context** — chỉ inject relevant turns + compressed summary
- Memory **phải được tag với user_id + department_id** để tránh cross-user leakage

**Memory Schema:**
```sql
CREATE TABLE conversation_memory (
  id UUID PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  department_id VARCHAR NOT NULL,
  session_id UUID NOT NULL,
  memory_type ENUM('short_term', 'long_term', 'preference'),
  content_summary TEXT,
  context_vector VECTOR(1536),  -- for semantic search
  sensitivity_level INT DEFAULT 0,
  created_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ
);
-- Row-level security: user can only SELECT WHERE user_id = current_user
```

_Source: [LLM Chat History Summarization 2025](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025), [AWS Managing Chat History](https://github.com/aws-samples/managing-chat-history-and-context-at-scale-in-generative-ai-chatbots), [Context Window Management](https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots/)_

---

### 8. Forecasting & Analytics Engine

**Tooling (Confidence: HIGH):**

| Use Case | Tool | Approach |
|----------|------|---------|
| Time-series forecasting | **Nixtla (TimeGPT)** / Prophet / SARIMA | Statistical cho < 1 năm data; TimeGPT cho zero-shot |
| Anomaly detection | **Isolation Forest** + LLM explanation | Statistical detect + LLM explain |
| Trend analysis | **statsmodels** + Pandas | Reliable, explainable |
| ML forecasting | **scikit-learn**, LightGBM | Khi có đủ historical data (>2 năm) |
| Explainability | **SHAP** + LLM narration | Business-friendly explanation |
| Visualization | **Plotly** (interactive) + Matplotlib | Chart rendering |

**Khi nào dùng gì:**
- **Rule/Statistical (Prophet, SARIMA)**: data < 2 năm, cần explainability cao, budget thấp
- **ML (LightGBM, XGBoost)**: data > 2 năm, nhiều features, accuracy ưu tiên hơn explainability
- **Foundation models (TimeGPT/Nixtla)**: zero-shot, không có historical data, cần nhanh
- **LLM narration**: luôn dùng để explain kết quả bằng ngôn ngữ tự nhiên cho business users

_Source: [Nixtla Time Series](https://www.nixtla.io), [LLMs + Anomaly Detection](https://towardsdatascience.com/boosting-your-anomaly-detection-with-llms/), [Time Series AI 2025](https://tensorblue.com/blog/time-series-forecasting-ai-demand-prediction-sales-forecasting-2025)_

---

### 9. Infrastructure & Deployment Stack

**Backend:**
- **Python 3.11+** — ecosystem tốt nhất cho AI/ML
- **FastAPI** — async, high performance, tự động OpenAPI docs
- **Celery + Redis** — background tasks (báo cáo định kỳ, heavy queries)

**Frontend:**
- **React 18 + TypeScript** — Admin portal & User chat interface
- **Ant Design Pro** hoặc **shadcn/ui** — enterprise UI components
- **Recharts / Plotly React** — data visualization
- **Socket.IO** — streaming LLM responses

**Infrastructure:**
- **Kong Gateway** — API gateway với rate limiting, auth, logging plugin
- **Keycloak** — Identity Provider (LDAP/AD integration, OIDC/OAuth2, JWT)
- **Redis 7+** — Session cache, query result cache, rate limiting
- **PostgreSQL 16+** — Metadata store, audit log, memory store
- **Nginx** — Reverse proxy, SSL termination

**Observability:**
- **Prometheus + Grafana** — metrics, alerting
- **ELK Stack** (Elasticsearch + Logstash + Kibana) — log aggregation
- **OpenTelemetry** — distributed tracing
- **LangSmith** hoặc **Langfuse** (self-hosted) — LLM observability, token cost tracking

**Container & Orchestration:**
- **Docker + Docker Compose** (dev/staging)
- **Kubernetes** (production)
- **Helm charts** cho deployment management

_Source: [Enterprise Chatbots Guide 2026](https://www.kernshell.com/building-enterprise-chatbots-with-conversational-ai-in-2026/), [LLM Chatbot Architecture](https://rasa.com/blog/llm-chatbot-architecture)_

---

### 10. AI Safety & Guardrails Stack

**Prompt Injection Defense (Confidence: HIGH — OWASP LLM Top 10 #1 Risk):**

Theo NCSC UK (2025): "Prompt injection là vấn đề có thể không bao giờ được fix hoàn toàn — mọi mitigation đều probabilistic." Vì vậy cần defense-in-depth:

| Layer | Giải pháp | Ghi chú |
|-------|-----------|---------|
| Input sanitization | Custom filter + regex | Loại bỏ obvious injection patterns |
| System prompt hardening | Constrained instructions | Không dùng system prompt làm sole control |
| Query validator | SQL whitelist + AST parser | Validate SQL trước khi execute |
| Output scanner | PII detector (Presidio) + sensitivity check | Scan kết quả trước khi trả về |
| Rate limiting | Kong + Redis counter | Chống brute-force jailbreak |
| Audit trail | Immutable log | Forensics khi incident |

**Tools:**
- **Microsoft Presidio** — PII detection và anonymization
- **Guardrails AI** — output validation framework
- **LLM Guard** (Protect AI) — input/output scanning
- **NeMo Guardrails** (NVIDIA) — conversational guardrails

_Source: [OWASP LLM Prompt Injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [Cisco: Prompt Injection is the new SQL Injection](https://blogs.cisco.com/ai/prompt-injection-is-the-new-sql-injection-and-guardrails-arent-enough), [Amazon Bedrock Prompt Injection](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-injection.html)_

---

## Integration Patterns Analysis

### Step 3. Integration Patterns — API Design, Oracle Multi-DB Connectors, Cross-Schema Query Patterns

**Mục tiêu của Step 3:** Xác định integration contract giữa UI, orchestration layer, policy engine, semantic layer, Oracle data sources, RAG/vector layer, và forecasting services sao cho vừa mở rộng được vừa không để LLM truy cập dữ liệu thô ngoài kiểm soát.

**Kết luận chính (Confidence: HIGH cho security/API shape, MEDIUM-HIGH cho Oracle-native feature fit):**
- Dùng **API-first, headless integration pattern** cho agent layer thay vì để UI hoặc LLM gọi Oracle trực tiếp. Với hệ đa nguồn/multi-schema, semantic layer đóng vai trò "metrics API", còn orchestration layer chịu trách nhiệm decomposition, authorization, và result merge.
- Với Oracle, pattern phù hợp nhất là **DataSource Registry + Connector Gateway + identity/context propagation**. Nếu tổ chức dùng Oracle AI Database 26ai, có thể tận dụng thêm AI Vector Search, SQL Firewall, Select AI, True Cache, external table/Iceberg support, và Globally Distributed Database để giảm độ phân mảnh integration.
- **Không cho LLM sinh cross-schema hoặc cross-DB SQL trực tiếp** như mặc định. Chỉ cho phép: single-domain SQL đã validate, hoặc query plan đa bước gồm nhiều truy vấn đơn miền rồi ghép ở application layer.

#### 3.1 API Design Pattern

**Recommended API topology:**

```
Client/UI
  -> API Gateway
  -> Chat/Query API
  -> Orchestrator
     -> Policy Decision Point (Cerbos/OPA)
     -> Semantic Layer API
     -> Oracle Connector Gateway
     -> RAG Retrieval API
     -> Forecast API
```

**Khuyến nghị API contract:**
- `POST /v1/chat/query`: entrypoint chính cho business question, trả về `request_id`, `trace_id`, `mode` (`sql`, `rag`, `hybrid`, `forecast`).
- `GET /v1/chat/query/{request_id}`: polling cho status nếu request dài hoặc cần human approval.
- `GET /v1/chat/stream/{request_id}`: SSE cho partial reasoning-safe updates, không stream raw chain-of-thought.
- `POST /v1/sql/preview`: chỉ cho admin/power user, trả lại SQL đã sanitize + nguồn dữ liệu + policy obligations.
- `POST /v1/reports/export`: async export CSV/XLSX/PDF với audit tag bắt buộc.
- `POST /v1/forecast/run`: route dữ liệu tổng hợp sang analytics/forecast service; không expose raw table access cho client.

**Contract requirements bắt buộc:**
- Mọi request mang `user_id`, `department_id`, `roles`, `region`, `session_id`.
- Mọi tool/API call nội bộ mang `trace_id`, `policy_decision_id`, `data_scope`, `sensitivity_level`.
- Response phải trả về `sources`, `data_domains`, `applied_policies`, `generated_at`, `confidence_note`.
- Mọi API có side effect hoặc export phải hỗ trợ idempotency key.

**Vì sao chọn API-first:**
- VentureBeat đánh giá headless semantic layer là contract "`API-first`" rõ nhất cho agent đa hệ thống và external apps; pattern này phù hợp hơn platform-native khi bài toán là multi-cloud hoặc multi-source.
- Oracle 26ai hỗ trợ gọi capability qua APIs/private instances và truy cập dữ liệu ngoài Oracle, gồm Apache Iceberg, nên phù hợp với mô hình connector gateway thay vì hard-code integration trong từng agent.

#### 3.2 Oracle Multi-DB Connector Pattern

**Pattern khuyến nghị: `Connector Gateway`**

```
ConnectorGateway
  -> DataSourceRegistry
  -> ConnectionPoolManager
  -> IdentityContextInjector
  -> SQL Validator / AST Checker
  -> Query Executor
  -> Result Sanitizer
  -> Audit Publisher
```

**Thiết kế registry:**
- Mỗi `source_id` ánh xạ tới `host`, `service`, `schema allowlist`, `network zone`, `query timeout`, `max rows`, `allowed_roles`, `supported_domains`.
- Tách `logical_domain` khỏi `physical_schema`. Ví dụ `finance.revenue` có thể map tới view ở schema `FINANCE_ANALYTICS`, không để LLM nhìn thẳng tên bảng gốc.
- Version hóa metadata và business glossary riêng; agent chỉ thấy semantic entities, không thấy toàn bộ catalog vật lý.

**Identity propagation & authorization:**
- Oracle Deep Data Security 26ai nhấn mạnh identity/context propagation xuống database runtime; đây nên là chuẩn mặc định cho connector layer.
- Database cần tự enforce row/column/cell-level rules; application chỉ làm pre-check, không phải điểm enforcement duy nhất.
- Với domain nhạy cảm, connector gateway nên mint short-lived credentials/token theo từng invocation thay vì dùng shared service account lâu dài. Petronella mô tả pattern ngắn hạn này cho agent/tool security; nó khớp với zero-trust integration tốt hơn.

**Khi nào dùng Oracle-native capability:**
- Dùng **SQL Firewall** để chặn unauthorized SQL và tăng visibility trên toàn bộ SQL traffic.
- Dùng **True Cache** cho workload hỏi đáp lặp lại, dashboard-like, hoặc heavy read bursts từ AI.
- Dùng **External Table/Iceberg support** khi cần truy cập governed datasets ngoài Oracle mà vẫn muốn giữ SQL contract thống nhất.
- Dùng **Globally Distributed Database** khi dữ liệu phân vùng theo vùng địa lý nhưng vẫn cần consistency model rõ ràng.
- Dùng **Select AI** như một accelerator bên trong Oracle nếu phạm vi dữ liệu chủ yếu ở Oracle ecosystem; nhưng vẫn cần policy + semantic layer ở ngoài cho bài toán multi-source enterprise.

#### 3.3 Cross-Schema Query Patterns

**Pattern 1 — Same-domain, same-policy schema join: CHẤP NHẬN CÓ ĐIỀU KIỆN**
- Chỉ cho phép nếu join nằm trong cùng data domain, đã có semantic definition, và dùng governed views/materialized views do data team publish.
- SQL phải là `SELECT` read-only, có row limit, không dùng dynamic DDL/DML, không gọi stored procedure side effect.
- Ví dụ hợp lệ: `FINANCE_ANALYTICS.v_revenue_monthly` join `FINANCE_ANALYTICS.v_budget_monthly`.

**Pattern 2 — Cross-schema, khác policy boundary: KHUYẾN NGHỊ DECOMPOSE**
- Tách câu hỏi thành nhiều single-schema queries.
- Chạy từng query qua connector/policy riêng.
- Merge kết quả ở application layer theo business key chuẩn hóa (`department_id`, `branch_code`, `month_key`...).
- Đây là pattern an toàn nhất cho câu hỏi như "so sánh doanh thu SALES với chi phí nhân sự HR theo phòng ban".

**Pattern 3 — Cross-database federation: KHÔNG CHO LLM TỰ VIẾT**
- Không cho agent tự sinh SQL dạng database link hoặc federated SQL trực tiếp giữa các nguồn.
- Thay vào đó dùng federated query plan:
  1. Intent classification
  2. Semantic metric resolution
  3. Policy check theo từng domain
  4. Single-source SQL generation
  5. Per-source execution
  6. Result normalization
  7. Application-layer join/aggregation
  8. Result-level masking và explanation
- Nếu khối lượng dữ liệu lớn hoặc join thường xuyên, tạo curated data mart/materialized integration view thay vì lặp lại federated runtime joins.

**Pattern 4 — Cross-schema retrieval + RAG hybrid: DÙNG PRE-FILTER**
- Cerbos khuyến nghị generate query plan trước retrieval và áp native filters trước khi fetch; điều này cần áp dụng cho cả vector retrieval lẫn metadata/document lookup.
- Với internal RAG, Dasroot khuyến nghị ingestion pipeline phải validate source và metadata ngay từ đầu; retrieval chỉ dùng tài liệu đã được trusted-source tagging.

#### 3.4 Guardrails Cho Integration Layer

**Bắt buộc trước khi gọi connector hoặc retriever:**
- Validate input và sanitize external content theo hướng dẫn OWASP, đặc biệt với tài liệu RAG, web snippets, code comments, và encoded payloads.
- Tách rõ `SYSTEM_INSTRUCTIONS` và `USER_DATA_TO_PROCESS` trong prompt/tool context, không trộn rule và data vào cùng một blob text.
- Validate tool parameters theo session context và permission hiện tại.
- Áp dụng least privilege cho DB account, API scopes, tool catalog, export permission.

**Bắt buộc sau khi có kết quả:**
- Mask/redact theo obligations từ policy engine.
- Ghi audit tuple: subject, action, resource, purpose, policy version, source ids, rows returned.
- Nếu là kết quả tổng hợp từ nhiều nguồn, trả thêm `data lineage` để người dùng biết kết quả được merge từ đâu.

#### 3.5 Integration Recommendation Cho Bài Toán Này

**Recommended target architecture:**
- **FastAPI/Kong** làm northbound API facade.
- **LangGraph** điều phối multi-step workflow và branching theo mode `sql/rag/hybrid/forecast`.
- **LlamaIndex** tập trung cho document retrieval/integration, không làm nơi thực thi authorization.
- **Cube.dev hoặc custom headless semantic layer** làm "metrics API" cho business terms, KPI definitions, join paths chuẩn.
- **Oracle Connector Gateway** quản lý pools, schema/domain routing, SQL validation, context propagation, audit.
- **Cerbos/OPA** ra quyết định policy và obligations trước mỗi retrieval/tool step.
- **Nixtla TimeGPT** tích hợp như một downstream analytics API riêng qua Python SDK hoặc REST API; không nhúng forecasting logic vào query connector.

**Anti-patterns cần tránh:**
- Cho frontend gọi thẳng Oracle hoặc vector DB.
- Cho LLM nhìn full schema catalog của toàn doanh nghiệp.
- Dùng shared DBA-like account cho mọi user query.
- Lọc quyền sau khi đã fetch dữ liệu.
- Dùng cross-schema SQL trực tiếp như default answer path cho câu hỏi multi-domain.
- Trộn memory, RAG context, và live SQL results vào cùng một trust boundary không gắn policy metadata.

**Tóm tắt quyết định kiến trúc:**
Step 3 nên chốt theo hướng **API-first, policy-enforced, domain-decomposed integration**. Semantic layer là contract nghiệp vụ; connector gateway là contract dữ liệu vật lý; policy engine là contract an toàn. Oracle 26ai là accelerator mạnh ở database core, nhưng không thay thế orchestration và policy decomposition cho bài toán multi-DB/multi-schema toàn doanh nghiệp.

_Source: [Oracle AI Database 26ai](https://blogs.oracle.com/database/oracle-ai-database-26ai-a-comprehensive-foundation-of-enterprise-ai-for-data), [Oracle Deep Data Security 26ai](https://blogs.oracle.com/database/introducing-oracle-deep-data-security-identity-aware-data-access-control-for-agentic-ai-in-oracle-ai-database-26ai), [Cerbos Access Control for RAG](https://www.cerbos.dev/features-benefits-and-use-cases/access-control-for-rag), [VentureBeat Semantic Layer](https://venturebeat.com/ai/headless-vs-native-semantic-layer-the-architectural-key-to-unlocking-90-text), [Petronella Policy-as-Code](https://petronellatech.com/blog/compliance/beyond-rbac-policy-as-code-to-secure-llms-vector-dbs-and-ai-agents/), [OWASP LLM Prompt Injection Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [Securing Internal RAG Systems](https://dasroot.net/posts/2026/03/securing-internal-rag-systems-enterprises/), [LangChain vs LlamaIndex 2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langchain-vs-llamaindex-2025-complete-rag-framework-comparison), [Mem0 Chat History Summarization 2025](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025), [Nixtla TimeGPT FAQ](https://www.nixtla.io/docs/introduction/faq)_

---

## Performance Considerations Analysis

### Step 4. Performance Considerations — Latency, Throughput, Scalability, Cost Efficiency

**Mục tiêu của Step 4:** Xác định cách hệ thống đạt latency chấp nhận được cho truy vấn hội thoại doanh nghiệp, đồng thời giữ Oracle production an toàn trước query storms, scaling được cho multi-user, RAG, và forecasting workloads.

**Kết luận chính (Confidence: HIGH cho cache/memory/orchestration patterns, MEDIUM-HIGH cho Oracle-specific performance assumptions):**
- Hệ thống này phải được tối ưu theo **3 lớp hiệu năng khác nhau**: interactive query latency, batch analytics/forecast throughput, và background ingestion/indexing throughput.
- Bottleneck lớn nhất thường không nằm ở model inference đơn lẻ mà ở **join path sai, over-fetch data, vector retrieval không lọc trước, và full-history prompt inflation**.
- Hiệu năng tốt nhất đến từ việc **giảm scope trước khi tăng compute**: semantic layer để giảm ambiguity, policy pre-filter để giảm retrieval set, application-layer decomposition để tránh cross-domain SQL nặng, và memory compression để giảm token load.

#### 4.1 SLO / SLA Gợi Ý

**Phân loại theo workload:**

| Workload | P50 Target | P95 Target | Ghi chú |
|----------|------------|------------|--------|
| Intent classification / routing | < 300ms | < 700ms | Không gọi DB nặng |
| Single-domain SQL Q&A | < 3s | < 8s | Đã cache metadata + dùng read replica |
| Hybrid SQL + RAG answer | < 5s | < 12s | Có retrieval + synthesis |
| Cross-domain decomposed query | < 8s | < 20s | Multi-step orchestration |
| Forecast request (interactive summary) | < 10s | < 30s | Chỉ summary; heavy jobs async |
| Export/report generation | async | async | Trả job id thay vì block UI |

**Nguyên tắc:** đừng cố ép mọi use case vào cùng một latency budget. Interactive Q&A, export, và forecasting hàng loạt là ba lớp khác nhau và phải tách queue/capacity riêng.

#### 4.2 Các Bottleneck Hiệu Năng Chính

**1. Oracle query path**
- LLM sinh SQL đúng cú pháp nhưng scan quá rộng.
- Join cross-schema làm query optimizer khó dự đoán cardinality.
- Truy vấn đụng DB production thay vì read replica / cache node.

**2. Retrieval path**
- Vector search không pre-filter theo department/region/classification.
- Chunk quá nhỏ gây over-retrieval; chunk quá lớn làm prompt nặng.
- Metadata nghèo nàn khiến reranking phải gánh việc lọc không đúng chỗ.

**3. LLM context path**
- Inject full schema + full history + full retrieved chunks vào một prompt.
- Multi-turn session giữ toàn bộ lịch sử thay vì summary + selective recall.

**4. Orchestration path**
- Agent loop gọi tool dư thừa.
- Cross-domain query merge ở Python nhưng không chuẩn hóa key/data types từ đầu.
- Thiếu result cache theo semantic intent nên cùng một câu hỏi bị recompute nhiều lần.

#### 4.3 Oracle Performance Patterns

**Khuyến nghị cho Oracle data workloads:**
- Tất cả AI read workloads đi qua **read replica / reporting replica / cache node**, không bắn thẳng vào OLTP primary nếu không có lý do rõ ràng.
- Dùng **True Cache** cho read-heavy Q&A. Oracle công bố True Cache có thể cho phản hồi query nhanh hơn tới `10x` và cải thiện read/write hiệu quả tới `2x` nhờ giảm tải cho primary.
- Với dữ liệu đa vùng, dùng **Globally Distributed Database** hoặc local read topology để giảm độ trễ mạng và tránh remote-read cost.
- Với vector search trên Oracle, ưu tiên kiến trúc tận dụng **AI Vector Search** và trên Exadata có thể hưởng lợi từ **AI Smart Scan** để offload tính toán vector distance xuống storage layer.

**Thiết kế query-friendly data model:**
- Publish governed views/materialized views cho KPI phổ biến thay vì để agent join nhiều bảng transaction.
- Dùng summary tables theo grain chuẩn: `day`, `month`, `department`, `branch`, `product`.
- Những câu hỏi multi-domain lặp lại nhiều lần nên được materialize thành integration mart thay vì decomposition runtime mỗi lần.

**Query governor cần có:**
- `row_limit`, `statement_timeout`, `cost ceiling`, cấm full table scan trên bảng lớn nếu không có partition predicate.
- Chỉ cho phép `SELECT`.
- Chặn recursive/self-join bất thường và Cartesian products.

#### 4.4 Semantic Layer và Query Planning Cho Hiệu Năng

**Semantic layer không chỉ để tăng accuracy mà còn để tăng performance:**
- VentureBeat lập luận semantic layer là lớp contract cho agent; thực tế nó còn giúp giảm số lần LLM thử-sai vì metric logic đã được chuẩn hóa.
- Thay vì để model tìm đường join động, semantic layer nên cung cấp:
  - metric definitions
  - allowed dimensions
  - canonical join paths
  - cache keys theo business intent

**Query planning rules đề xuất:**
- Ưu tiên **single-domain answer path**.
- Nếu câu hỏi cần nhiều domain, planner phải quyết định:
  - decomposition runtime
  - hay trả về partial answer + đề nghị export async
  - hay route sang curated mart đã có sẵn
- Chỉ bật heavy cross-domain merge khi estimated row counts nhỏ và key alignment rõ ràng.

#### 4.5 RAG Retrieval Performance

**Hiệu năng retrieval tốt nhất = retrieve ít hơn nhưng đúng hơn.**

**Best practices:**
- Áp **pre-retrieval filtering** theo policy như Cerbos khuyến nghị; vừa an toàn vừa giảm payload và rerank cost.
- Gắn metadata phong phú ngay lúc ingestion: `department`, `owner`, `region`, `classification`, `document_type`, `effective_date`, `source_trust`.
- Dùng two-stage retrieval:
  1. metadata filter + ANN vector search
  2. rerank top-K nhỏ
- Chỉ đưa top chunks cần thiết vào prompt; không inject cả document.

**Ingestion throughput:**
- Tách ingestion thành pipeline async: parse -> classify -> chunk -> embed -> index -> verify.
- Dasroot nhấn mạnh ingestion cần validate source đáng tin cậy; điều này cũng giảm chi phí re-indexing do dữ liệu bẩn hoặc poisoned content.

#### 4.6 Conversation Memory và Token Efficiency

**Memory là performance feature, không chỉ là UX feature.**

Theo Mem0, memory systems tốt có thể giảm token cost `80-90%` trong khi vẫn giữ hoặc tăng chất lượng phản hồi. Điều đó có nghĩa:
- Giảm latency ở prompt build + inference
- Giảm cost trên mỗi query
- Giảm xác suất vượt context window

**Pattern khuyến nghị:**
- Short-term memory trong Redis TTL ngắn
- Medium-term summaries trong PostgreSQL
- Selective recall bằng semantic lookup thay vì full replay

**Không nên:**
- Đưa toàn bộ chat history vào mỗi request
- Trộn audit log với conversational memory
- Lưu memory không gắn sensitivity/owner metadata

#### 4.7 Forecasting & Analytics Scale

**Forecasting là workload throughput-oriented, không phải chat latency-oriented.**

Nixtla tài liệu hóa pattern scale-out qua Spark, Dask, và Ray; với bài toán hàng chục nghìn đến hàng triệu time series, distributed forecasting có thể cho cải thiện `10-100x` so với single-machine processing.

**Khuyến nghị triển khai:**
- Interactive forecast: chỉ chạy horizon ngắn, top metrics quan trọng, sample visualization.
- Bulk forecast / scenario planning: chạy async qua Spark/Dask/Ray workers.
- Cache feature-engineered aggregates thay vì tính lại từ raw SQL cho từng lần forecast.
- Tách service forecasting khỏi chat API bằng queue/job model.

#### 4.8 Caching Strategy

**Cần ít nhất 4 lớp cache:**

1. **Metadata cache**
   - schema summary, business glossary, policy-translated scopes
   - TTL dài, invalidate theo catalog version

2. **Semantic result cache**
   - cache theo normalized intent + filters + role scope
   - ví dụ: "doanh thu tháng này của miền Bắc"

3. **Retrieval cache**
   - top-K doc ids hoặc embedding search candidates cho query lặp lại
   - phải gắn policy scope vào cache key

4. **Rendered answer cache**
   - chỉ dùng cho câu hỏi ít thay đổi, dữ liệu không real-time
   - cache cả chart spec/table schema, không nhất thiết cache raw prose

**Cache key bắt buộc có:**
- `tenant/department`
- `role scope`
- `data freshness class`
- `query normalization hash`
- `semantic layer version`

#### 4.9 Capacity Planning Gợi Ý

**Tách pool theo loại việc:**
- `chat-low-latency`
- `sql-heavy`
- `rag-ingestion`
- `forecast-batch`
- `export-jobs`

**Concurrency controls:**
- Giới hạn số SQL-heavy requests đồng thời trên mỗi source Oracle.
- Dùng token bucket/rate limit theo user và theo department.
- Với batch/export, dùng queue depth thresholds và backpressure thay vì cho nổ thẳng vào DB.

**Chiến lược scale:**
- Scale ngang orchestration/API nodes trước.
- Scale retrieval/index workers theo ingestion rate.
- Scale forecasting workers riêng khỏi chat path.
- Scale Oracle read capacity bằng replica/cache/distribution, không chỉ bằng app servers.

#### 4.10 Monitoring và Tối Ưu Liên Tục

**Metrics cần theo dõi:**
- P50/P95/P99 latency theo mode `sql`, `rag`, `hybrid`, `forecast`
- query rows scanned vs rows returned
- cache hit ratio theo từng lớp
- tokens per answer
- retrieval candidate count và rerank depth
- Oracle wait events / timeout rate
- number of decomposed subqueries per request
- forecast job queue time và execution time

**Cần trace end-to-end cho mỗi request:**
- route decision
- policy decision
- semantic resolution
- per-source query execution time
- merge time
- LLM generation time

**Heuristic tối ưu thực tế:**
- Nếu `rows_scanned >> rows_returned`: cần semantic pruning hoặc materialized view.
- Nếu `retrieved_chunks >> injected_chunks`: metadata filter còn yếu.
- Nếu `tokens_per_answer` tăng dần theo session: memory compaction chưa tốt.
- Nếu P95 tăng nhưng DB CPU không tăng tương ứng: bottleneck có thể ở orchestration/network/model queue chứ không phải SQL.

#### 4.11 Performance Recommendation Cho Bài Toán Này

**Target design:**
- Dùng **Oracle True Cache/read replicas** cho interactive analytics reads.
- Dùng **semantic layer + governed marts** cho top 20-50 KPI hay hỏi.
- Dùng **decomposed multi-step plan** cho cross-domain query thay vì cross-DB SQL trực tiếp.
- Dùng **policy pre-filtered retrieval** để giảm vector/doc payload.
- Dùng **hierarchical memory** để cắt token load.
- Dùng **async job model** cho forecasting hàng loạt và export.

**Kiến trúc hiệu năng hợp lý cho giai đoạn đầu:**
- MVP: single-region, read replica, Redis cache, PostgreSQL metadata, RAG top-K nhỏ, no heavy forecasting in request path.
- Pilot: thêm semantic result cache, curated marts, async exports, monitoring P95/P99.
- Production: True Cache, distributed Oracle topology nếu đa vùng, forecast cluster riêng, adaptive query planner, materialized integration views cho cross-domain hot paths.

**Tóm tắt quyết định kiến trúc:**
Step 4 nên chốt theo hướng **reduce work before scaling work**. Muốn hệ thống nhanh và ổn định thì phải giới hạn data scope, chuẩn hóa metric path, cache đúng tầng, và tách interactive path khỏi batch path. Oracle 26ai cung cấp accelerator rất mạnh cho cache, distribution, vector search, nhưng lợi ích chỉ phát huy đầy đủ khi orchestration layer không bơm các truy vấn mơ hồ hoặc quá rộng xuống DB.

_Source: [Oracle AI Database 26ai](https://blogs.oracle.com/database/oracle-ai-database-26ai-a-comprehensive-foundation-of-enterprise-ai-for-data), [Oracle Announces Oracle AI Database 26ai](https://blogs.oracle.com/support/oracle-announces-oracle-ai-database-26ai), [Raising the Standard for Mission-Critical Availability and Security in the Age of AI](https://blogs.oracle.com/database/raising-the-standard-for-mission-critical-availability-and-security-in-the-age-of-ai), [Building Scalable Vector Search with Oracle Globally Distributed Database](https://blogs.oracle.com/database/building-scalable-vector-search-with-oracle-globally-distributed-database), [Exadata AI Smart Scan Deep Dive](https://blogs.oracle.com/exadata/exadata-ai-smart-scan-deep-dive), [VentureBeat Semantic Layer](https://venturebeat.com/ai/headless-vs-native-semantic-layer-the-architectural-key-to-unlocking-90-text), [Cerbos Access Control for RAG](https://www.cerbos.dev/features-benefits-and-use-cases/access-control-for-rag), [Securing Internal RAG Systems](https://dasroot.net/posts/2026/03/securing-internal-rag-systems-enterprises/), [Mem0 Research](https://mem0.ai/research), [Mem0 Chat History Summarization 2025](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025), [Nixtla Computing at Scale](https://www.nixtla.io/docs/tutorials-computing_at_scale)_

---

## Recommended Target Architecture & Phased Roadmap

### Step 5. Recommended Target Architecture + Phased Roadmap

**Mục tiêu của Step 5:** Tổng hợp các quyết định ở Steps 1-4 thành một kiến trúc mục tiêu nhất quán, có thể triển khai theo pha, với rủi ro và dependency rõ ràng.

**Executive recommendation (Confidence: HIGH):**
- Kiến trúc mục tiêu phù hợp nhất cho bài toán này là **governed AI data access platform** thay vì một chatbot đơn thuần.
- Trục thiết kế cần khóa theo 4 nguyên tắc:
  - **API-first** thay vì DB-first
  - **Semantic-layer-first** thay vì direct text-to-SQL
  - **Policy-enforced retrieval** thay vì filter sau khi fetch
  - **Decomposed multi-domain execution** thay vì cross-DB SQL tự do

#### 5.1 Recommended Target Architecture

**Target-state high level:**

```
Users / Systems
  -> Web Chat UI / Admin Portal / External API Consumers
  -> API Gateway (auth, rate limit, logging)
  -> AI Orchestration Layer (LangGraph)
     -> Intent Router
     -> Policy Check Layer (Cerbos/OPA + Oracle DB-native enforcement)
     -> Semantic Layer API
     -> SQL Planning & Validation
     -> RAG Retrieval Service
     -> Forecast Service
     -> Response Composer

  -> Data Access Layer
     -> Oracle Connector Gateway
     -> Oracle Read Replica / True Cache / Distributed Oracle topology
     -> Vector Store / Oracle AI Vector Search
     -> PostgreSQL (metadata, audit, memory)
     -> Redis (session, cache, rate control)
```

**Vai trò từng lớp:**
- **Presentation layer**: chat UI, admin UI, API consumers.
- **Gateway layer**: auth, rate limiting, request tracing, request normalization.
- **Orchestration layer**: quyết định mode `sql`, `rag`, `hybrid`, `forecast`, quản lý multi-step workflows.
- **Policy layer**: enforce quyền trước retrieval/tool execution; DB layer tiếp tục enforce row/column/cell rules.
- **Semantic layer**: business contract cho metrics, dimensions, join paths, glossary.
- **Connector layer**: quản lý pools, routing, query validation, audit, identity propagation.
- **Data layer**: Oracle governed reads, vector retrieval, metadata/memory/audit stores.

#### 5.2 Recommended Technology Choices

**Khuyến nghị mặc định cho bài toán hiện tại:**
- **Backend API**: FastAPI
- **Gateway**: Kong hoặc APISIX
- **IdP**: Keycloak + LDAP/AD
- **Agent orchestration**: LangGraph
- **RAG framework**: LlamaIndex
- **Semantic layer**: Cube.dev hoặc custom headless semantic catalog
- **Policy engine**: Cerbos hoặc OPA
- **Primary DB access**: Oracle read replicas / True Cache
- **Vector path**: Weaviate hoặc Oracle AI Vector Search nếu muốn tập trung nhiều hơn vào Oracle stack
- **Metadata/Audit/Memory**: PostgreSQL
- **Session/Cache**: Redis
- **Forecasting**: Nixtla TimeGPT cho accelerator; Spark/Dask/Ray cho bulk scale
- **Observability**: OpenTelemetry + Prometheus/Grafana + Langfuse/LangSmith

**Khuyến nghị chọn mặc định thực tế:**
- Nếu doanh nghiệp đã đầu tư mạnh vào Oracle 23ai/26ai: ưu tiên Oracle-native hơn ở vector, caching, distributed topology.
- Nếu đội data đã có dbt/Cube mạnh: semantic layer nên do data team sở hữu, không để app team tự phát minh metric logic.
- Nếu dữ liệu nội bộ nhạy cảm cao: chuẩn bị đường on-prem/self-hosted cho model fallback và vector store.

#### 5.3 Core Decision Log

**Decision 1 — Không cho direct NL2SQL trên raw schema**
- Lý do: accuracy không đủ, security risk cao, khó scale governance.

**Decision 2 — Semantic layer là thành phần bắt buộc**
- Lý do: vừa tăng trust/accuracy vừa giảm latency và query drift.

**Decision 3 — Cross-domain query phải đi theo query plan decomposition**
- Lý do: an toàn hơn, kiểm soát policy tốt hơn, dễ tối ưu hơn.

**Decision 4 — Authorization phải có cả application-layer và database-layer**
- Lý do: AI workflows động không thể chỉ dựa vào app-level checks.

**Decision 5 — Forecast/export là async-first**
- Lý do: không phá hỏng latency budget của conversational path.

**Decision 6 — Memory phải hierarchical**
- Lý do: giảm token load và tránh context inflation.

#### 5.4 Phased Roadmap

**Phase 0 — Foundation Alignment (1-2 tuần)**
- Chốt owner giữa app team, data team, security team.
- Kiểm kê data sources Oracle, schema boundaries, role mapping, sensitivity classes.
- Chọn semantic layer strategy: Cube/custom/dbt MetricFlow.
- Chọn policy engine và chuẩn hóa attributes: `user`, `region`, `classification`.
- Chốt top 20-50 business questions và top 20 KPI priority.

**Exit criteria:**
- Có source inventory
- Có policy attribute model
- Có KPI shortlist
- Có target integration boundaries

**Phase 1 — MVP Governed Chat (3-5 tuần)**
- Dựng FastAPI + Gateway + Keycloak.
- Dựng LangGraph orchestration đơn giản: `sql`, `rag`, `fallback`.
- Tạo Oracle Connector Gateway với read-only validation.
- Dựng semantic catalog bản đầu cho KPI ưu tiên.
- Tích hợp PostgreSQL audit + Redis session cache.
- Chỉ hỗ trợ single-domain SQL và RAG cơ bản theo department.

**Phạm vi MVP nên có:**
- hỏi đáp dữ liệu trong 1 domain
- xem nguồn dữ liệu đã dùng
- audit request/response metadata
- export nhẹ

**Không nên nhét vào MVP:**
- cross-domain federated merge phức tạp
- forecasting hàng loạt
- approval workflow nhiều tầng
- auto-generated dashboard đa chiều

**Phase 2 — Pilot Multi-Domain Intelligence (4-8 tuần)**
- Bật decomposed cross-domain query plans.
- Thêm Cerbos/OPA obligations trước retrieval/tool calls.
- Bổ sung RAG metadata filtering + ingestion validation.
- Thêm semantic result cache và curated marts cho hot paths.
- Thêm SQL preview/explainability cho power users/admin.
- Thêm async exports và basic scheduled reporting.

**Exit criteria:**
- cross-domain queries hoạt động qua decomposition
- P95 trong ngưỡng pilot
- audit đủ để truy vết data lineage
- policy enforcement có test coverage cơ bản

**Phase 3 — Production Hardening (6-12 tuần)**
- Bật Oracle True Cache hoặc topology read scaling tương đương.
- Tách workload pools: chat, sql-heavy, ingestion, export, forecast.
- Thêm hierarchical memory + selective recall.
- Tăng observability: end-to-end tracing, model cost tracking, cache hit dashboards.
- Thêm approval workflow cho sensitive queries và export controls.
- Chuẩn hóa materialized integration views cho truy vấn lặp lại nhiều.

**Exit criteria:**
- P95/P99 ổn định
- no shared privileged path
- capacity plan rõ ràng
- rollback/recovery runbook đầy đủ

**Phase 4 — Advanced Analytics & Enterprise Scale (tuỳ chọn)**
- Bulk forecasting với Spark/Dask/Ray hoặc cluster riêng.
- Scenario planning, anomaly detection, scheduled executive reporting.
- Distributed Oracle topology đa vùng nếu có data residency/latency requirement.
- Agent-assisted analytics workflows có human checkpoint cho tác vụ nhạy cảm.

#### 5.5 Delivery Priorities

**Ưu tiên build theo thứ tự:**
1. Auth + audit + connector safety
2. Semantic layer cho KPI cốt lõi
3. Single-domain SQL path
4. RAG với policy pre-filter
5. Cross-domain decomposition
6. Async export/reporting
7. Forecasting scale-out

**Nếu nguồn lực hạn chế:**
- Cắt forecasting khỏi phase đầu
- Không xây multi-agent phức tạp từ đầu
- Không cố cover toàn bộ schema Oracle
- Tập trung vào 20 câu hỏi và 20 KPI có business value cao nhất

#### 5.6 Risks and Mitigations

**Rủi ro 1 — Semantic layer làm chậm tiến độ**
- Mitigation: bắt đầu bằng 10-20 metrics tier-0; không model hóa toàn enterprise ngay.

**Rủi ro 2 — Data governance không đủ tốt**
- Mitigation: ép mọi query production đi qua connector gateway + audit; không bypass bằng ad hoc SQL.

**Rủi ro 3 — Cross-domain answers sai do key mismatch**
- Mitigation: chuẩn hóa canonical business keys và curated integration marts.

**Rủi ro 4 — RAG leakage**
- Mitigation: metadata-rich ingestion, pre-retrieval filtering, source trust tagging.

**Rủi ro 5 — Chi phí model tăng mạnh**
- Mitigation: hierarchical memory, retrieval pruning, caching, async jobs cho workload nặng.

#### 5.7 Final Architecture Recommendation

**Kiến trúc nên chốt để triển khai:**
- Một **FastAPI + LangGraph orchestration core**
- Một **semantic layer headless** do data team quản trị
- Một **Oracle Connector Gateway** read-only, identity-aware, auditable
- Một **policy engine** áp trước retrieval và tool execution
- Một **RAG stack** có metadata filtering và memory hierarchy
- Một **forecast service** chạy tách khỏi conversational path

**Kết luận cuối cùng:**
Nếu làm đúng hướng, hệ thống này không chỉ là chatbot hỏi đáp Oracle mà là một lớp truy cập dữ liệu doanh nghiệp có governance dành cho AI. Recommended target architecture nên ưu tiên tính kiểm soát, explainability, và operational stability trước khi theo đuổi agent autonomy cao. Lộ trình đúng là bắt đầu hẹp nhưng governed, sau đó mở rộng domain coverage, retrieval intelligence, và analytics scale theo các phase rõ ràng.

_Source: tổng hợp từ các phần Technology Stack, Integration Patterns, và Performance Considerations trong tài liệu này; các nguồn nền chính gồm [Oracle AI Database 26ai](https://blogs.oracle.com/database/oracle-ai-database-26ai-a-comprehensive-foundation-of-enterprise-ai-for-data), [Oracle Deep Data Security 26ai](https://blogs.oracle.com/database/introducing-oracle-deep-data-security-identity-aware-data-access-control-for-agentic-ai-in-oracle-ai-database-26ai), [VentureBeat Semantic Layer](https://venturebeat.com/ai/headless-vs-native-semantic-layer-the-architectural-key-to-unlocking-90-text), [Cerbos Access Control for RAG](https://www.cerbos.dev/features-benefits-and-use-cases/access-control-for-rag), [OWASP LLM Prompt Injection Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [Mem0 Chat History Summarization 2025](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025), [Nixtla Computing at Scale](https://www.nixtla.io/docs/tutorials-computing_at_scale)_

---

## Final Recommendation & Implementation Checklist

### Step 6. Executive Summary for Leadership + Delivery Checklist for Engineering

#### 6.1 Final Recommendation for Leadership

**Khuyến nghị chốt để ra quyết định đầu tư:**

Doanh nghiệp nên triển khai bài toán này như một **nền tảng truy cập dữ liệu doanh nghiệp có governance cho AI** thay vì xem nó là một chatbot hỏi đáp đơn giản. Giá trị thực nằm ở việc kết nối an toàn giữa người dùng, tài liệu nội bộ, và nhiều nguồn Oracle DB dưới cùng một lớp kiểm soát, audit, và giải thích được.

**Quyết định kiến trúc nên chốt:**
- Không cho AI truy cập trực tiếp raw schema hoặc sinh SQL tự do trên toàn hệ thống.
- Dùng **semantic layer** để chuẩn hóa KPI, business terms, và join paths.
- Dùng **API gateway + orchestration layer + connector gateway** để kiểm soát mọi truy cập dữ liệu.
- Dùng **policy engine + Oracle DB-native security** để enforce quyền trước và trong lúc truy cập dữ liệu.
- Dùng **RAG có metadata filtering** cho tài liệu nội bộ.
- Tách **forecasting / export / reporting** khỏi luồng chat tương tác.

**Lợi ích kinh doanh kỳ vọng:**
- Giảm phụ thuộc vào đội kỹ thuật/data cho các câu hỏi phân tích lặp lại.
- Tăng tốc độ ra quyết định nhờ self-service data Q&A có kiểm soát.
- Giảm rủi ro lộ dữ liệu so với việc để người dùng hoặc AI truy vấn ad hoc.
- Tạo nền tảng mở rộng cho analytics, reporting, forecasting, và agent workflows sau này.

**Điều kiện để dự án thành công:**
- Có owner rõ giữa business, data, security, và engineering.
- Bắt đầu hẹp với tập KPI và use case ưu tiên cao.
- Chấp nhận đầu tư vào semantic layer và governance từ đầu.
- Đo hiệu quả theo adoption, answer quality, latency, và auditability, không chỉ theo demo quality.

**Khuyến nghị triển khai cấp điều hành:**
- Phê duyệt theo mô hình **phased rollout**.
- Giai đoạn đầu chỉ nên cover các domain ít rủi ro hơn nhưng có giá trị cao.
- Không mở rộng toàn enterprise trước khi MVP/pilot chứng minh được governance, độ đúng, và hiệu năng.

#### 6.2 One-Page Architecture Recommendation

**Nên xây:**
- `FastAPI` làm backend API
- `Kong/APISIX` làm gateway
- `Keycloak + LDAP/AD` làm identity
- `LangGraph` làm orchestration
- `Cube.dev/custom semantic layer` làm business contract
- `Oracle Connector Gateway` làm data access control plane
- `Cerbos/OPA + Oracle security controls` làm authorization
- `LlamaIndex + filtered RAG stack` cho tài liệu nội bộ
- `PostgreSQL + Redis` cho metadata, audit, memory, cache
- `Nixtla/forecast workers` cho analytics nâng cao

**Không nên xây theo hướng:**
- chatbot gọi DB trực tiếp
- direct text-to-SQL trên raw schema toàn doanh nghiệp
- filter quyền sau khi dữ liệu đã được fetch
- trộn interactive chat với batch export/forecasting trong cùng execution path

#### 6.3 Implementation Checklist for Engineering

**A. Governance & Scope**
- [ ] Chốt business owner, data owner, security owner, engineering owner
- [ ] Lập inventory cho Oracle sources, schemas, data classes, refresh cadence
- [ ] Chọn 20-50 business questions ưu tiên
- [ ] Chọn 10-20 KPI tier-0 để đưa vào semantic layer
- [ ] Chuẩn hóa canonical business keys giữa các domain

**B. Security & Identity**
- [ ] Tích hợp Keycloak với LDAP/AD
- [ ] Định nghĩa user attributes: `department`, `region`, `role`, `clearance`
- [ ] Chọn policy engine: Cerbos hoặc OPA
- [ ] Bật DB-native enforcement cho row/column/cell-level controls nếu có
- [ ] Chặn shared privileged account cho AI query path
- [ ] Thiết kế audit tuple chuẩn cho mọi request/tool call

**C. API & Orchestration**
- [ ] Dựng API Gateway với auth, rate limit, logging, trace id
- [ ] Tạo `POST /v1/chat/query`
- [ ] Tạo `GET /v1/chat/query/{request_id}` và streaming endpoint
- [ ] Thiết kế mode routing: `sql`, `rag`, `hybrid`, `forecast`
- [ ] Định nghĩa internal contract giữa orchestrator, policy layer, semantic layer, connector layer

**D. Semantic Layer**
- [ ] Chọn Cube.dev hoặc custom semantic catalog
- [ ] Khai báo metrics, dimensions, allowed joins, freshness rules
- [ ] Tạo alias/business glossary cho thuật ngữ nghiệp vụ
- [ ] Tạo versioning cho metric definitions
- [ ] Thiết kế semantic cache key

**E. Oracle Connector Layer**
- [ ] Tạo `DataSourceRegistry`
- [ ] Tách logical domains khỏi physical schemas
- [ ] Thiết lập read replicas hoặc reporting sources
- [ ] Áp row limit, timeout, query governor
- [ ] Chỉ cho phép `SELECT`
- [ ] Thêm SQL validator / AST checker
- [ ] Thêm identity/context propagation xuống DB layer

**F. RAG Pipeline**
- [ ] Thiết kế metadata schema cho documents/chunks
- [ ] Tạo ingestion pipeline: parse -> classify -> chunk -> embed -> index -> verify
- [ ] Gắn `source_trust`, `classification`, `department`, `effective_date`
- [ ] Áp pre-retrieval filtering theo policy
- [ ] Giới hạn top-K và rerank depth

**G. Memory & Conversation**
- [ ] Dùng Redis cho short-term session state
- [ ] Dùng PostgreSQL cho medium-term summaries
- [ ] Gắn user/department/sensitivity metadata vào memory
- [ ] Áp selective recall thay vì full-history replay
- [ ] Theo dõi token cost theo session

**H. Performance**
- [ ] Chốt SLO cho `sql`, `rag`, `hybrid`, `forecast`
- [ ] Bật cache cho metadata, semantic results, retrieval candidates
- [ ] Tách workload pools: chat, sql-heavy, ingestion, export, forecast
- [ ] Thiết kế async job model cho export/reporting/forecasting
- [ ] Xác định hot paths cần materialized views hoặc curated marts

**I. Observability & Quality**
- [ ] Bật OpenTelemetry tracing end-to-end
- [ ] Thu metrics P50/P95/P99 theo từng mode
- [ ] Log policy decisions, source ids, rows returned, prompt size
- [ ] Tạo dashboard cho cache hit ratio, token usage, timeout rate
- [ ] Thiết kế eval set cho top business questions
- [ ] Thiết kế regression tests cho policy, SQL validation, RAG leakage

**J. Release Readiness**
- [ ] Review security trước pilot
- [ ] Review data quality cho tier-0 metrics
- [ ] Review rollback/runbook cho connector failures
- [ ] Review approval flow cho sensitive exports
- [ ] Review capacity plan trước production rollout

#### 6.4 Suggested Decision Gate

**Go / No-Go cho MVP:**
- Có semantic definitions cho KPI tier-0
- Có audit log đầy đủ
- Có read-only connector path an toàn
- Có ít nhất một domain chạy đúng end-to-end
- Có policy enforcement trước retrieval/query execution

**Go / No-Go cho Pilot:**
- Cross-domain decomposition hoạt động ổn định
- P95 nằm trong ngưỡng mục tiêu
- Không có đường bypass policy đã biết
- Có monitoring và incident response cơ bản

**Go / No-Go cho Production:**
- Đã chứng minh answer quality trên tập câu hỏi thật
- Đã chứng minh governance và auditability
- Đã có cache/read-scaling strategy rõ ràng
- Đã có runbook cho Oracle, RAG, model, và policy failures

#### 6.5 Final Closing Statement

Nếu cần một câu chốt ngắn gọn cho lãnh đạo: **hãy đầu tư vào một lớp truy cập dữ liệu có governance cho AI, không phải một chatbot tự do truy vấn Oracle**. Nếu cần một câu chốt cho kỹ thuật: **hãy build semantic layer, connector gateway, policy-first retrieval, rồi mới mở rộng sang multi-domain intelligence và forecasting scale**.

---

### Technology Adoption Trends (2025-2026)

- **Semantic Layer** từ "nice-to-have" → "mandatory" cho AI data access (Gartner 2025)
- **LangGraph** đang dần thay thế LangChain chains cho agentic workflows
- **LlamaIndex** đang thống lĩnh RAG-specific use cases với 35% accuracy improvement
- **Oracle 23ai/26ai** đưa AI native vào database (Select AI, VPD enforcement)
- **ABAC over RBAC** cho AI: trend mạnh 2025 vì RBAC không đủ expressive cho AI agent context
- **Open-source LLMs** (LLaMA 3, Qwen2.5): growing adoption trong on-premise enterprise deployments
- **Mem0-style hierarchical memory** đang trở thành standard thay vì full-history injection

_Source: [Semantic Layer AI Future](https://cube.dev/blog/semantic-layer-and-ai-the-future-of-data-querying-with-natural-language), [Enterprise RAG Platforms 2026](https://atlan.com/know/enterprise-rag-platforms-comparison/), [Open Source MetricFlow](https://www.getdbt.com/blog/open-source-metricflow-governed-metrics)_

---

<!-- Content will be appended sequentially through research workflow steps -->
