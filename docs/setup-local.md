# Hướng dẫn cài đặt và chạy local

Tài liệu này dành cho người muốn dựng môi trường dev local để chạy app và backend.

## 1. Bạn sẽ có gì sau khi hoàn tất

Sau khi làm xong hướng dẫn này, bạn sẽ có:

- frontend chat chạy ở `http://localhost:3000`
- backend orchestration chạy ở `http://localhost:8090`
- Kong gateway chạy ở `http://localhost:8000`
- Keycloak ở `http://localhost:8080`
- Grafana ở `http://localhost:3001`
- Weaviate ở `http://localhost:8081`

## 2. Yêu cầu cài đặt

Máy local cần có:

- Python 3.12
- Node.js 20+ và npm
- Docker Desktop
- Git

Khuyến nghị thêm:

- `uv`
- GNU Make
- Git Bash hoặc WSL nếu bạn dùng Windows

Lý do: `Makefile` hiện gọi một số script `bash`.

## 3. Clone và cài dependency

Ở root repo:

```powershell
cd D:\WORKING\AIAL
```

Nếu đã có `uv`:

```powershell
uv sync --all-packages
npm install
```

Nếu chưa có `uv`, bạn vẫn có thể dùng virtualenv hiện có trong repo nếu nó đã được tạo sẵn:

```powershell
.\.venv\Scripts\python -m pip install -r requirement.txt
npm install
```

## 4. Cấu hình môi trường

Repo có file mẫu [`.env.example`](../.env.example).

Trong local dev, phần lớn biến môi trường được bơm từ Vault khi chạy `make infra-up`.

Các biến quan trọng:

- `KEYCLOAK_URL`
- `CERBOS_URL`
- `REDIS_URL`
- `DATABASE_URL`
- `WEAVIATE_URL`
- `AIAL_KEYCLOAK_CLIENT_SECRET`
- `AIAL_ORACLE_USERNAME`
- `AIAL_ORACLE_PASSWORD`
- `AIAL_ORACLE_DSN`
- `OTEL_EXPORTER_OTLP_ENDPOINT`

Frontend có thể cần thêm:

- `VITE_API_BASE_URL`
- `VITE_KEYCLOAK_URL`
- `VITE_KEYCLOAK_REALM`
- `VITE_KEYCLOAK_CLIENT_ID`

Giá trị mặc định trong code đã hỗ trợ local khá nhiều:

- Keycloak URL mặc định: `http://localhost:8080`
- realm mặc định: `aial`
- client mặc định frontend: `aial-frontend`
- API base mặc định: rỗng, Vite sẽ proxy `/v1`

## 5. Dựng hạ tầng local

### Cách khuyến nghị

Chạy bằng Git Bash hoặc WSL:

```bash
make infra-up
```

Lệnh này sẽ:

- bật Vault
- seed secrets
- sinh `.env.infra`
- bật phần còn lại của stack
- cấu hình Kong JWT
- init schema Weaviate

### Nếu không dùng `make`

Bạn có thể chạy `docker compose` trực tiếp, nhưng sẽ phải tự xử lý:

- seed secrets
- export env từ Vault
- cấu hình Kong JWT
- init Weaviate schema

Do đó, dùng `make infra-up` vẫn là cách nên dùng nhất.

## 6. Chạy backend orchestration

Backend chính là `services/orchestration`.

Chạy bằng virtualenv trong repo:

```powershell
$env:PYTHONPATH="services;shared/src;infra"
.\.venv\Scripts\python -m uvicorn orchestration.main:app --reload --host 0.0.0.0 --port 8090
```

Kiểm tra nhanh:

```powershell
curl http://localhost:8090/health
```

Nếu backend lên đúng, bạn sẽ gọi được các route `/v1/...`.

## 7. Chạy frontend chat

Mở terminal mới:

```powershell
cd apps\chat
npm install
npm run dev
```

Mặc định Vite chạy ở:

```text
http://localhost:3000
```

Vite proxy `/v1` sang:

```text
http://localhost:8000
```

Tức là frontend local đang đi qua Kong, còn Kong forward tiếp tới orchestration host `:8090`.

## 8. Cổng dịch vụ local

- Frontend chat: `http://localhost:3000`
- Kong proxy: `http://localhost:8000`
- Kong admin: `http://localhost:8001`
- Keycloak: `http://localhost:8080`
- Backend orchestration: `http://localhost:8090`
- Vault: `http://localhost:8200`
- Weaviate: `http://localhost:8081`
- Redis: `localhost:6379`
- Postgres: `localhost:5432`
- Grafana: `http://localhost:3001`
- Prometheus: `http://localhost:9090`
- Tempo: `http://localhost:3200`

## 9. Chạy test

### Backend

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

Hoặc chạy focused suites:

```powershell
.\.venv\Scripts\python -m pytest tests/test_sse_streaming.py tests/test_langgraph_stub_graph.py -q
```

### Frontend

```powershell
cd apps\chat
npm run test
```

Ví dụ chạy focused:

```powershell
npm run test -- useSSEStream.test.ts ExportResultsConsole.test.tsx Epic5BWorkspace.test.tsx
```

## 10. Luồng khởi động khuyến nghị

Trình tự khởi động mỗi ngày:

1. `make infra-up`
2. chạy backend orchestration ở port `8090`
3. chạy frontend `apps/chat`
4. mở `http://localhost:3000`

## 11. Sự cố thường gặp

### Frontend mở được nhưng API lỗi

Kiểm tra:

- backend có đang chạy ở `8090` không
- Kong có đang chạy ở `8000` không
- Keycloak/Cerbos có healthy không

### Test Python báo không export được traces

Nếu thấy log kiểu OTLP export tới `localhost:4317` bị lỗi, đó thường chỉ là cảnh báo observability local, không nhất thiết làm fail test.

### `make infra-up` lỗi trên Windows

Nguyên nhân phổ biến:

- không có `bash`
- không có `make`

Giải pháp:

- chạy bằng Git Bash hoặc WSL
- hoặc dịch từng bước trong `Makefile` sang lệnh PowerShell tương ứng

### Đăng nhập không hoạt động

Kiểm tra:

- Keycloak đã lên chưa
- realm `aial` đã import chưa
- client frontend có khớp cấu hình không
- frontend có dùng đúng `VITE_KEYCLOAK_*` không

## 12. Muốn chạy dữ liệu thật thì cần gì thêm

Để thay local skeleton bằng dữ liệu nghiệp vụ thật, cần cung cấp thêm:

- thông tin database/schema/table/view
- credential truy cập
- semantic metric catalog
- user/role test
- policy masking/approval
- sample query và expected result

## 13. Template cấu hình chuẩn mới

Repo hiện có template nhập liệu chuẩn tại:

- [docs/templates/config-catalog.template.json](../docs/templates/config-catalog.template.json)

Backend cũng expose template qua admin API:

- `GET /v1/admin/config-catalog/template`

Và hỗ trợ import 1 lần cho cả:

- `data_sources`
- `semantic_metrics`
- `role_mappings`

qua endpoint:

- `POST /v1/admin/config-catalog/import`
