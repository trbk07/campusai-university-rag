# Performance và UX checklist

Tài liệu này là checklist triển khai để hệ thống nhanh và mượt khi người dùng
tự upload PDF. Các mục đã làm được đánh dấu `[x]`; các mục còn lại là phạm vi
cần hoàn thành trước khi gọi là production-ready.

## Đã hoàn thành trong backend

- [x] Cache ingestion theo SHA-256 và không parse lại cùng một file.
- [x] `IngestionJobManager` chạy parse/index nền, giới hạn worker, có state,
  stage, progress, lỗi và dedupe.
- [x] Job ingestion lỗi có thể retry; job thành công vẫn dedupe.
- [x] Dense encoder và reranker dùng runtime singleton theo model/device,
  tránh tạo bản sao nhiều GB cho mỗi request.
- [x] Có lệnh warm model lúc startup:
  `python scripts/warm_retrieval.py --dense-model BAAI/bge-m3
  --reranker-model BAAI/bge-reranker-v2-m3`.
- [x] Một query embedding được dùng lại khi tìm trên nhiều tài liệu cùng model.
- [x] Có LRU query-result cache và tự invalidation khi load/remove index.
- [x] Reranker chỉ nhận tối đa 8 ứng viên mặc định.
- [x] Có cấu hình `device`, `batch_size`, cache size và rerank candidate limit.
- [x] PyMuPDF là parser production nhanh; Docling chỉ chạy trong job layout/table
  review explicit, không nằm trên request path.
- [x] Test regression, acceptance validator và compile đều chạy xanh.

## P0 — cần làm để UX thực sự mượt

### Upload và xử lý tài liệu

- [ ] Tạo UI upload bất đồng bộ: trả `job_id` ngay, không khóa request.
- [ ] Poll trạng thái job mỗi 250–500 ms; hiển thị từng stage: validate,
  parse, extract table, persist, index.
- [ ] Hiển thị thời gian ước tính, số trang đã xử lý và nút retry khi lỗi.
- [ ] Disable nút hỏi trong lúc tài liệu chưa ở trạng thái `succeeded`.
- [ ] Cho phép hủy job và giải phóng worker/memory.
- [ ] Hiển thị rõ file trùng, file hỏng, scan không có text, vượt MB/số trang.
- [ ] OCR là nhánh opt-in có cảnh báo thời gian; không âm thầm chạy OCR hàng
  trăm trang trong request người dùng.

### Query và câu trả lời

- [ ] Route Easy/Medium/Hard bằng rule trước; chỉ dùng agent/LLM cho Hard.
- [x] Dùng BM25/dense cho fast path; chỉ rerank top 8 khi gọi explicit
  `mode="hybrid_rerank"` cho câu Medium/Hard.
- [ ] Cache câu hỏi theo `query + doc_ids + filters + model/config` và có nút
  refresh khi người dùng muốn bỏ cache.
- [ ] Streaming token câu trả lời để người dùng thấy phản hồi đầu tiên sớm.
- [ ] Đặt timeout riêng cho retrieval, tool và LLM; hiển thị fallback có ích
  thay vì spinner vô hạn.
- [ ] Hiển thị citation dạng `document / page / excerpt`, cho phép mở đúng
  trang PDF.
- [ ] Không cho submit nhiều request giống nhau đồng thời; gom request trùng
  thành một single-flight job.

### UI và trạng thái

- [ ] Có danh sách tài liệu: ready/processing/failed, dung lượng, số trang,
  ngôn ngữ, thời điểm index.
- [ ] Có multi-select tài liệu và hiển thị phạm vi tìm kiếm hiện tại.
- [ ] Giữ lịch sử hội thoại và trạng thái khi rerun UI.
- [ ] Dùng skeleton/progress thay cho màn hình trắng; không render toàn bộ
  kết quả dài cùng lúc, dùng pagination/expand.
- [ ] Có thông báo privacy: nội dung nào đi qua API LLM và cách xóa dữ liệu.
- [ ] Kiểm tra responsive, keyboard navigation, contrast và thông báo lỗi dễ
  hiểu bằng tiếng Việt/tiếng Anh.

## P1 — cần làm để ổn định khi nhiều người dùng

### Runtime và triển khai

- [ ] Preload model một lần khi process khởi động và expose readiness probe;
  không tải model trong request đầu tiên.
- [ ] Chọn GPU nếu có; nếu CPU thì giới hạn `torch` threads để tránh tranh
  chấp CPU khi có nhiều request.
- [ ] Giới hạn concurrency theo RAM: một job Docling/OCR nặng và số query
  rerank đồng thời phải có queue riêng.
- [ ] Version hóa index theo model, chunker và config; config đổi phải
  invalidate index đúng cách.
- [ ] Dọn file tạm, cache TTL/LRU, quota theo user và giới hạn tổng dung lượng.
- [ ] Health/readiness/liveness endpoint và graceful shutdown cho executor,
  model runtime, SQLite cache.

### Quan sát và vận hành

- [ ] Ghi metrics p50/p95/p99 cho upload, parse, table extraction, index,
  retrieval, rerank, first token và hoàn tất LLM.
- [ ] Ghi cache hit rate, queue depth, lỗi theo stage, RSS/VRAM và số worker.
- [ ] Gắn `request_id`/`job_id` vào log; không log API key hoặc nội dung nhạy cảm.
- [ ] Có cảnh báo khi p95 vượt ngưỡng hoặc memory gần giới hạn 8 GB.
- [ ] Có endpoint/admin view để xem job lỗi, retry và xóa dữ liệu.

## P1 — chất lượng và an toàn không được bỏ qua

- [ ] Test PDF tiếng Việt/Anh, bảng nhiều trang, layout trộn, font lỗi và scan.
- [ ] Test tải 1/5/20 người dùng đồng thời; đo cold start và warm start riêng.
- [ ] Giữ holdout test không dùng để tune; theo dõi Recall@5, MRR, citation,
  hallucination và latency.
- [ ] Test prompt injection trong PDF; nội dung PDF chỉ là dữ liệu, tool chỉ
  nhận DSL JSON đã validate.
- [ ] Quét secret, kiểm tra upload path traversal, file type thật và giới hạn
  decompression bomb.
- [ ] Kiểm tra xóa dữ liệu thật sự xóa store, index, cache và metadata liên quan.

## Ngưỡng nghiệm thu đề xuất

- Upload được acknowledge trong dưới 300 ms.
- File text thông thường dưới 50 trang: parse/index nền, không khóa UI.
- Query warm không rerank: p95 dưới 1 s trên CPU hoặc dưới 300 ms trên GPU.
- Query có rerank: p95 dưới 2,5 s trên CPU hoặc dưới 800 ms trên GPU.
- First token LLM: p95 dưới 2 s khi provider khỏe; timeout rõ ràng khi provider lỗi.
- Không duplicate model trong cùng process; RSS nằm trong ngân sách đã đo ở T2.
- Không có spinner vô hạn, lỗi luôn có stage, nguyên nhân và hành động tiếp theo.

## Cách chạy kiểm tra hiện tại

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\benchmark_t2.py --input-dir <university-pdf-dir> --output evaluation\t2_results.json
.\.venv\Scripts\python.exe scripts\validate_t2.py evaluation\t2_results.json
.\.venv\Scripts\python.exe scripts\warm_retrieval.py --dense-model fallback-hash-256
```
