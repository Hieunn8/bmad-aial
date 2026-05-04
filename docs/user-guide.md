# Hướng dẫn sử dụng

Tài liệu này dành cho người dùng nội bộ muốn hiểu app đang làm được gì và dùng như thế nào trong môi trường local/dev.

## 1. Bắt đầu ở đâu

Mở app tại:

```text
http://localhost:3000
```

Màn hình chính hiện render `Epic5BWorkspace`, tức một workspace tổng hợp nhiều khu vực thay vì một chat window đơn lẻ.

## 2. Các khu vực chính trong app

### Semantic / Memory / History studio

Khu vực này là phần trung tâm của workspace hiện tại.

Bạn có thể dùng để:

- gửi query
- xem kết quả trả về
- quan sát memory context / history / suggestions
- làm việc với semantic metric và query flow ở mức demo/dev

### Export studio

Khu vực này cho phép:

- chạy query có stream
- xem row trả về dần qua SSE
- xem answer summary
- xem cache freshness nếu kết quả đến từ cache
- tạo export preview
- tạo export job
- tải report khi job hoàn tất

Luồng sử dụng:

1. nhập câu hỏi
2. bấm `Run Query`
3. chờ rows và answer về
4. chọn định dạng `xlsx`, `pdf`, hoặc `csv`
5. bấm `Generate Report`
6. xác nhận export
7. chờ job hoàn tất rồi tải file

### Forecast studio

Khu vực này dùng để chạy forecast time-series.

Bạn có thể:

- tạo forecast job
- theo dõi trạng thái job
- xem result
- tải xuống output

Lưu ý: hiện phần này vẫn dùng result/service mô phỏng.

### Anomaly alerts

Khu vực này cho phép:

- chạy phát hiện bất thường
- xem danh sách alert
- mở chi tiết
- acknowledge hoặc dismiss alert

### Trend analysis

Khu vực này cho phép:

- chạy phân tích xu hướng
- xem summary và presentation dạng panel

### Drilldown explainability

Khu vực này cho phép:

- tạo explainability job
- poll trạng thái
- xem kết quả giải thích

Một số path hiện có fallback nếu provider explainability không khả dụng.

## 3. Các API/flow người dùng sẽ chạm tới nhiều nhất

### Chat query + stream

Luồng cơ bản:

1. frontend gọi `POST /v1/chat/query`
2. backend trả về `request_id`
3. frontend mở `GET /v1/chat/stream/{request_id}`
4. backend stream `row`, `done`, hoặc `error`

Hiện tại SSE đã được sửa để:

- chờ event thật từ producer
- không còn đóng stream sớm bằng `done("stub")` giả
- surface `error` event đúng ra UI

### SQL explanation

Sau khi query chạy xong, có thể gọi:

```text
GET /v1/chat/query/{request_id}/sql-explanation
```

để xem mô tả SQL / metric explanation.

### Export

Các route chính:

- `GET /v1/chat/query/{request_id}/export-preview`
- `POST /v1/chat/query/{request_id}/export`
- `GET /v1/chat/exports/{job_id}`
- `GET /v1/chat/exports/{job_id}/download`

## 4. Những gì người dùng nên biết trước khi dùng

### Đây chưa phải dữ liệu production thật

App hiện phù hợp để:

- demo flow
- dev/test
- kiểm thử UI/API

Không nên hiểu đây là:

- kết quả báo cáo doanh nghiệp thật
- semantic layer production thật
- forecast thật trên dữ liệu thật

### Một số nội dung vẫn là stub

Ví dụ:

- chat graph hiện còn walking skeleton
- cross-domain conflict hiện dùng dữ liệu mẫu
- forecast dùng dữ liệu dựng sẵn
- document ingestion/reindex chưa chạy queue worker thật

## 5. Hồ sơ người dùng và quyền

Hệ thống có phân biệt quyền theo role.

Một số nhóm vai trò thường gặp:

- `user`
- `admin`
- `data_owner`

Các chức năng admin/document không mở cho user thường.

## 6. Nếu muốn dùng với dữ liệu thật thì cần cung cấp gì thêm

Nếu bạn muốn biến tài liệu này thành SOP triển khai thực tế hoặc UAT guide hoàn chỉnh, cần bổ sung:

- danh sách database, schema, table, view thực tế
- mapping business metric
- tài khoản mẫu theo role
- sample queries và expected outputs
- policy masking / approval
- quy trình nạp dữ liệu / đồng bộ semantic layer
- quy trình quản trị documents

## 7. Tài liệu nào nên viết tiếp sau bộ này

Nếu dự án đi tiếp, nên bổ sung thêm:

- runbook production
- deployment guide theo môi trường
- API reference
- data source catalog
- semantic metric catalog
- admin operations guide
- UAT checklist
