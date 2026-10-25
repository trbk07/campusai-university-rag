# CampusAI — Kế hoạch phát triển dự án

Cập nhật: **25/10/2026 — Asia/Bangkok**. Đây là roadmap hiện hành của dự án.
`plan.md` luôn ở root và được Git theo dõi. Nhật ký thử nghiệm nằm trong hồ sơ
bằng chứng, không được nối thêm vào roadmap này.

## 1. Mục tiêu sản phẩm

CampusAI giúp người dùng tải tài liệu đại học, đặt câu hỏi bằng tiếng Việt/Anh
và nhận câu trả lời có thể kiểm tra đến đúng tài liệu, trang và đoạn trích.
Phạm vi gồm học phần, tín chỉ, học kỳ, quy chế, học phí, phiên bản theo năm và
câu hỏi cần kết hợp nhiều nguồn. Khi nguồn thiếu hoặc mâu thuẫn chưa giải quyết
được, ứng dụng phải thông báo rõ và từ chối kết luận.

Luồng MVP: **upload PDF → xử lý nền → tài liệu sẵn sàng → hỏi đáp → xem nguồn →
gửi phản hồi**. Tài liệu mẫu trong repository phục vụ đánh giá; sản phẩm phải
hoạt động trên tài liệu người dùng tải lên, không phụ thuộc tên/hash của mẫu.

### Ưu tiên hiện tại — hỏi liên tục, không quá tải, chi phí dịch vụ 0

**GOAL COMPLETE — phạm vi local đã đo, ngày 16/10/2026.** Đã nghiên cứu và áp
dụng nhiều repo/ý tưởng, bật Gemini 3.5 Flash-Lite Free ở 10 RPM, kiểm chứng
hội thoại qua app thật và dừng phép đo ngay khi Google báo quota. Giới hạn
Free thực quan sát được: 15 RPM; TPM/RPD chưa đo, không cam kết hỏi vô hạn.

| Bước | Trạng thái | Điều kiện hoàn tất |
|---|---|---|
| GQ-01 — Baseline và chẩn đoán | DONE — phạm vi quan sát | Giữ lỗi provider 503 câu ba; tách lỗi quota/overload với lỗi chọn evidence rank 6 và guard “thế nào” quá rộng. Không suy nguyên nhân nội bộ Google. Phép đo riêng nhận typed Free RPM 15 từ lỗi 429. |
| GQ-02 — Nghiên cứu giải pháp | DONE — source review | So sánh source chính thức của nhiều repo, ghi ý tưởng áp dụng/loại bỏ và chi phí/giới hạn; xem [hồ sơ nghiên cứu](docs/deployment/phase13/free-continuity-goal.md). |
| GQ-03 — Giảm số lần gọi và token | DONE — workload đã khóa | Cache bền qua restart, scope/version/history/provider giữ tách biệt. Tám candidates/cửa sổ nguyên văn: đủ facts 10/10; giảm 20,9% ký tự offline và 9,58% input token ở sáu câu live đối sánh. Cache/negative 20 lượt dùng 0 provider calls, tách khỏi 10 đáp án mới. |
| GQ-04 — Quản lý quota và tải | DONE — giới hạn quan sát + bảo vệ quota | Dừng đúng 429 đầu tiên, metadata Free 15 RPM; 35 POST trên cap 60, không gửi mới sau lỗi. Runtime 10 RPM/1 sender, giữ counter 70 qua restart. Quota ngày/DST/recovery kiểm giả lập; TPM/RPD UNKNOWN. Theo yêu cầu owner, không gọi tiếp để đo quota ngày. |
| GQ-05 — Đường sinh đáp án miễn phí bền vững | SELECTED — bounded local PASS | `configs/free_llm.yaml`: Gemini 3.5 Flash-Lite, một inference, operator 10 RPM, chờ tối đa 6s; owner xác nhận Free. Đã bật default và chạy app. Giữ lỗi Gemma/lượt ngắt; không nhận quota cao nhất toàn cầu hoặc miễn phí vô hạn. |
| GQ-06 — Kiểm chứng hội thoại | DONE — 30/30 ở 10 RPM | 10 đáp án mới qua API thật, 10 cache, 10 negative; đúng 10 POST, không 429/503. Report/quality review riêng từng run, giữ 37 attempts selection gồm lỗi/ngắt; không gộp thành SLO. Bổ sung smoke scope trên app đang chạy, 0 provider attempts. |
| GQ-07 — Bàn giao và cleanup | DONE — goal local | App localhost/hướng dẫn, receipt mới ràng buộc source và 1.770 offline PASS/2 live SKIP, 18 targeted PASS, 37 browser checks. Package đủ source/UI, test/build/dependency tạm đã dọn. Giữ failures/receipts/archive/wheel và plan.md tracked. |

Mỗi kết quả chỉ áp dụng scope đã ghi. Một chuỗi chỉ trả cache,
negative hoặc trích đoạn không hoàn tất GQ-06. Nếu budget đã xác minh không đủ
cho workload mục tiêu thì báo giới hạn và đánh giá phương án khác, không ép
Free Tier thành cam kết hỏi vô hạn. R-01/R-02 và các gate cloud vẫn giữ trạng thái
cũ; kết quả local không thay cho cloud acceptance. Chi tiết quyết định, nguồn
tham khảo và phần còn thiếu nằm trong hồ sơ liên kết, không nối log vào roadmap.

GQ-04 đã triển khai admission SQLite dùng chung qua worker/restart, reservation
RPM/input TPM/RPD/token ngày và circuit phân biệt 429/503. Default hiện là
`configs/free_llm.yaml`; `continuity_llm.yaml` và receipt quota cũ là mốc lịch sử,
profile nghiệm thu cũ giữ nguyên byte/hash. Admission/state, fault/cache/recovery,
config/package và runtime/hội thoại đã có bằng chứng. RPM Free thực quan sát là
15, runtime giữ 10; TPM/RPD chưa đo và đã dừng theo chỉ thị owner. Xem
[quota và bàn giao](docs/deployment/phase13/quota-exhaustion.md),
[review model](docs/deployment/phase13/model-selection.md)
và [receipt hiện hành](docs/deployment/phase13/evidence/quota-exhaustion-20261016/receipt.json). Chưa tăng %
Phase 13, chưa đổi R-01/R-02 hoặc nhận là đã hết overload provider.

Đối chiếu [repo → phần áp dụng và kiểm thử](docs/deployment/phase13/repo-application-review.md)
và [sàng lọc/kiểm chứng model](docs/deployment/phase13/model-selection.md).
Không cập nhật receipts lịch sử để gắn chúng vào source mới; kết quả model và
hồi quy mới được ghi riêng. Source cũ có archive đúng hash; goal local đã đóng,
các giới hạn chưa đo được ghi rõ trong hồ sơ bàn giao.

### Sửa hiểu câu hỏi và tổng hợp tài liệu — 16/10/2026

**DONE — phạm vi kiểm tra đã ghi.** Đã tái hiện 16/21 lỗi mới và sửa route số
trang PDF, topic/history, tổng hợp theo phần, trích dẫn từ nguồn, chào/cảm ơn,
fragment vô nghĩa trước dense retrieval và thuật ngữ thứ tự. Không FAQ gắn PDF
hoặc hạ validator. Kết quả cuối: 1.827 regression PASS/2 live SKIP, 39 browser
checks; tám loại câu hỏi model thật có evidence, lượt kiểm cuối 3/3 dùng 1 POST,
24 replay turns dùng 0 external POST. Giữ các run native NOT PASSED, tổng đợt
16 POST; không gộp thành native 24/24/SLO. App đã restart ở 10 RPM/1 sender.
Xem [ma trận, kết quả và giới hạn](docs/deployment/phase13/natural-conversation.md)
và [receipt hiện tại](docs/deployment/phase13/evidence/natural-conversation-20261016/receipt.json).
Các receipt chọn model/quota phía trên là mốc lịch sử có source archive;
nghiệm thu cloud/R-01/R-02 và % phase không thay đổi.

### Kiểm tra mở rộng human-natural — 16/10/2026

**IN PROGRESS.** Mở rộng khỏi workload một PDF: câu nhiều ý/tự có chủ đề,
viết tắt và câu hỏi tiếp, nhiều tài liệu, phạm vi trang, gây nhiễu và kiểm phần
trả lời hiển thị so với claims. Đã tái hiện thêm 28/32 lỗi mới; đang sửa và
chạy chẩn đoán 480 raw queries/7 PDF offline. Bộ 480 là AI-authored, chưa được
human review; không gọi là 480 đáp án model thật hoặc nghiệm thu toàn diện.
Giữ profile Free, quota/state và lịch sử thất bại; không đổi % các phase cloud.

## 2. Trạng thái hiện tại

| Phase | Phạm vi | Trạng thái hiện hành | Căn cứ / giới hạn |
|---|---|---|---|
| 0 | Tên dự án, package, cấu hình nền | IMPLEMENTED | Đã có package `campusai`, README, cấu hình và `.env.example`; không suy thành nghiệm thu public deployment. |
| 1 | Ingestion PDF, metadata, lifecycle | DONE — acceptance đã có | Report Phase 1/2 có 16/16 tiêu chí đúng trên corpus thật và holdout. |
| 2 | Chunking, bảng, provenance | DONE — acceptance đã có | Golden fixtures, giới hạn chunk và citation nằm trong acceptance Phase 1/2. |
| 3 | Embedding, dense index, persistence | IMPLEMENTED; report gốc CONDITIONAL | Báo cáo dense độc lập còn giới hạn corpus/negative; hybrid có evidence riêng ở Phase 6. Không tự đổi report gốc thành PASS. |
| 4 | Basic RAG, context budget, cache | DONE — offline contract | Benchmark 30 câu PASS; chất lượng model được kiểm tra riêng trong Phase 7/8. |
| 5 | Citation, grounding, abstention | **DONE -100%,10/10 tasks** | Internal Phase5 acceptance PASS400/400 on a21a4cd5/grounding-v29; all5 gates PASS. Grounding/citation/abstention P/R100%, leakage0, reason97.67%; holdout calibration/risk0. Three consecutive full suites each2,663 PASS/2 live SKIP. Exposed benchmark disclosed; public fresh-holdout requirement stays separate. |
| 6 | BM25 + dense + RRF | DONE — release lịch sử | RC3 PASS trên profile đã khóa; không thay cho qualification của deployment mới. |
| 7 | Hoàn thiện core product quality | **DONE — 100% scope Chat** | 68/68 trường hợp đúng; live performance chuyển sang điều kiện release bên dưới. |
| 8 | Benchmark và đánh giá sản phẩm | **DONE — 100% scope Chat** | 300/300 trường hợp đúng nội dung/negative qua replay ứng dụng. |
| 9 | Temporal RAG | **DONE — 100% scope Phase 9** | 6/6 task DONE, 5/5 gate PASS; 24/24 quality/replay, tests/coverage/regression và cleanup đã kiểm tra. |
| 10 | Multi-document / multi-hop | DONE — 5/5 task (100%), 5/5 gate PASS | Actual replay/source review 24/24; 1.550 tests PASS, coverage 91,09%; raw/normalization và API limitations báo riêng. |
| 11 | Knowledge Graph có nguồn chứng minh | **DONE — 5/5 task (100%), 5/5 gate PASS** | Candidate16/16, quality benefit, hồi quy68/300/24/24, 1.582 tests PASS, coverage90,99%; opt-in, mặc định OFF. |
| 12 | Web app MVP | **DONE - 100% (5/5 task, 8/8 UI work item)** | Local MVP remains accepted through `start-campusai.cmd`. Post-acceptance batch optimization supports up to 5 concurrent PDF uploads, per-file progress/failure retention, 3 ingestion workers + 8 queued jobs, and 4 concurrent queries. Latest local verification: 2,384 offline PASS, 2 opt-in live SKIP, 41 browser checks PASS (including manual local OCR with recovery, six-PDF rejection and five-PDF upload/ready), plus a BGE-M3 offline 5-PDF/100-question HTTP workload. Real provider quality and public SLO remain separate and unqualified. |
| 13 | Deployment cloud miễn phí | **IN PROGRESS — 5/64 tiêu chí (7,8%), 0/16 task DONE** | Target Oracle Always Free; provider/UX recovery đã kiểm tra offline, chưa thay cloud acceptance. |
| 14 | Production hardening | PLANNED — chưa nghiệm thu phase | Vận hành, dữ liệu, bảo mật, quan sát và độ tin cậy trước public release. |

`IMPLEMENTED` nghĩa là đã có code, chưa đủ căn cứ đóng mọi yêu cầu nghiệm thu
độc lập. Phần trăm chỉ áp dụng cho scope đã ghi; không tính phần trăm toàn dự án
bằng cách cộng các phase có khối lượng khác nhau. Các phase chưa mở có thể đã có
code nền, nhưng chưa được tính là đã nghiệm thu.

### Kết quả chất lượng đã chốt

| Kiểm tra | Kết quả |
|---|---|
| Phase 7 — trả lời khi đủ bằng chứng | 42/42 đúng |
| Phase 7 — từ chối khi thiếu bằng chứng | 26/26 đúng |
| Phase 7 — claim / liên kết claim-citation được hỗ trợ | 74/74 và 90/90 |
| Phase 7 — fault/restart qua hai process | 60/60 PASS |
| Phase 8 — đáp án được đối chiếu nguồn | 145/145 đúng |
| Phase 8 — negative chạy nhánh local | 155/155 từ chối đúng |
| Phase 8 — schema phản hồi ứng dụng | 300/300 hợp lệ |
| Kiểm tra offline cuối | 1.473 PASS, 2 live test SKIP; coverage 90,60% |

[Audit hoàn tất Phase 7/8](evaluation/results/phase78-chat-quality-completion-20261013.json)
ràng buộc runtime, source và 93 artifact bindings. Hai live integration đã PASS
ở lượt riêng; hai test SKIP trong suite offline không phải kết quả live mới.

## 3. Quyết định phạm vi và giới hạn nghiệm thu

Owner đã thay yêu cầu Phase 7 ban đầu 20 task / 19 gate bằng core product quality,
giữ optional reranker tắt. Ngày 13/10/2026, owner chốt dùng output Gemini Chat,
đối chiếu nguồn và replay ứng dụng để hoàn tất chất lượng Phase 7/8, không chờ
API hoặc quota reset. **Hai phase đã đóng trong phạm vi điều chỉnh này.**

Giới hạn phải đi cùng kết quả:

- 100% là tỷ lệ trên các mẫu regression đã kiểm tra và đã exposure, không phải
  bảo đảm mọi câu hỏi tương lai. Review do **Codex — Automated AI Review**,
  không giả chữ ký hay nhãn độc lập của con người.
- Chat output được đưa qua ứng dụng thật bằng replay; đây không phải phép đo
  thời gian sinh đáp án qua API. Danh tính model/settings Chat chưa xác minh.
- Phase 8 có 17 raw record hợp format và 128 record lỗi escape. Bản normalized
  bàn giao đạt 145/145 schema, giữ nguyên giá trị; lịch sử raw lỗi vẫn là lỗi.
- Exact-gold citation match là 144/145 (99,31%); một citation trỏ tới chunk nguồn
  khác gold nhưng được kiểm chứng hợp lệ. Giữ nguyên gold và các proxy lexical.
- Các lượt HTTP 503 và workload live chưa hoàn tất vẫn giữ nguyên trong audit.

### Điều kiện release còn mở — không phải backlog đóng lại Phase 7/8

| ID | Việc cần nghiệm thu | Trạng thái | Điều kiện xử lý |
|---|---|---|---|
| R-01 | C7-05: workload hiệu năng thật đã khóa, 100 HTTP / 54 provider calls | DEFERRED — NOT PASSED | Đủ cold/warm, cache on/off, lỗi, timeout và RSS trên cùng profile; không loại lỗi khỏi denominator. Ngưỡng gốc: HTTP p95 ≤10 giây, timeout ≤0,5%, RSS ≤75% RAM. |
| R-02 | Phase 8: latency, availability và native API format | DEFERRED — NOT PASSED | Thu đủ workload thật và review theo protocol đã khóa; Chat/replay không thay thế. Lịch sử 6/18 case đã thử, 3 thành công, 3 HTTP 503; không gộp nhiều runtime thành một SLO. |
| R-03 | Profile public deployment và vận hành | PLANNED | Khóa profile ở Phase 13; nghiệm thu bảo mật, quota, dữ liệu và vận hành ở Phase 14 trước public release. |

R-01/R-02 chỉ mở lại khi có cơ sở provider hoạt động và phạm vi gọi được phép,
trong giới hạn **Free Tier, không phát sinh chi phí**. Không tự tạo vòng manifest
mới, đổi key/model hoặc resume lượt đã đóng để retry 503. Nếu chọn workload mới
cho deployment khác, phải ghi quyết định thay phạm vi; kết quả cũ vẫn chưa PASS.

## 4. Kiến trúc và quy tắc kỹ thuật

```text
Upload / hỏi đáp / xem nguồn
          ↓
Web + API → validation, quota, document registry, job progress
          ↓
PyMuPDF → metadata có bằng chứng → text/table chunks → BM25 + dense index
          ↓
Document/year/program scope → exact-code hoặc hybrid + RRF → evidence budget
          ↓
Grounded answer → kiểm tra claim/citation/số liệu → đáp án hoặc abstention
```

- Parser mặc định PyMuPDF. Scan-only mặc định `review_required/ocr_required`;
  OCR/Docling chỉ ở job opt-in có giới hạn, không dùng LLM để đoán metadata.
- Dedupe theo SHA-256; progress, retry idempotent, cancel, cleanup và restart
  có contract. Chỉ index tài liệu đạt validation; tách ingestion xong với index ready.
- Chunk giữ document, page/page range, heading, table ID và source hash; không
  mất header/boundary hoặc vượt giới hạn cuối sau khi thêm context/overlap.
- Retrieval giữ scope trước ranking, không trộn năm/chương trình/tài liệu;
  encoder load một lần mỗi process. Reranker giữ `RERANKER_ENABLED=false`.
- LLM chỉ diễn giải evidence được chọn. Citation phải tồn tại và có quote/toạ độ
  đúng; bảng/phép tính dùng kiểm chứng deterministic, không đoán số liệu.
- Cache phải gắn với corpus/index/prompt/model/policy/scope; không cache lỗi
  provider thành đáp án thành công. Giữ circuit 503 bền vững và chờ có giới hạn.
- Profile nghiệm thu LLM: [product_llm.yaml](configs/product_llm.yaml).
  Không suy cấu hình mặc định hoặc replay profile thành profile deployment.
- Không thêm framework RAG, vector DB, model, corpus hay graph nếu chưa có vấn
  đề tái hiện và lợi ích cần đo. MVP tiếp tục dùng các component hiện có.

## 5. Chi tiết Phase 0–8: giữ lại phạm vi và nghiệm thu

Phần này giữ đặc tả, contract và tiêu chí của các phase đã làm;
không bỏ nội dung chỉ vì phase đã đóng. Trạng thái ở mục 2 và
điều chỉnh scope ở mục 3 là hiện hành; các lệnh tái hiện bên dưới
không có nghĩa là phải chạy lại acceptance/API đã hoàn tất.

### Phase 0 — Tên dự án, contract và baseline

**IMPLEMENTED.** Đã có tên CampusAI, package `campusai`, README, cấu hình và
`.env.example`. Giữ baseline, public import contract và tài liệu kiến trúc/chính
sách dữ liệu; không suy phần chuẩn hóa này thành nghiệm thu production.

### Phase 1 — Ingestion đại học (10/10 gate)

**DONE; acceptance Phase 1/2 đạt 16/16 tiêu chí. [Bằng chứng](evaluation/results/ingestion_acceptance.json).**

#### Chiến lược đã chọn

Phase 1 dùng pipeline deterministic-first: PyMuPDF cho PDF text-based là đường mặc định,
Docling/OCR chỉ là nhánh review opt-in cho tài liệu khó. Không gọi LLM để parse metadata,
không index tài liệu chưa đạt validation, và không coi fixture sinh tự động là corpus thật.
Mỗi tài liệu được xử lý qua một job idempotent, có registry, version, provenance và trạng
thái rõ ràng. Đây là lựa chọn tối ưu cho free-tier vì giảm cold start, chi phí và bề mặt lỗi,
đồng thời vẫn mở đường cho OCR/layout parser ở worker riêng.

#### Contract đầu vào và corpus nghiệm thu

- Có tối thiểu **5 PDF đại học thật**, ưu tiên UET/VNU; corpus phải đa dạng loại/layout
  và không dùng synthetic fixture để thay thế coverage thật.
- Corpus bao phủ regulation, curriculum, syllabus, handbook, course catalog, tài liệu
  nhiều trang, tài liệu có bảng, tiếng Việt có dấu, tiếng Anh/song ngữ và ít nhất hai
  phiên bản/năm khác nhau.
- Có `supplied_real_corpus`, `generated_test_fixtures` và `holdout_corpus` tách biệt.
- Mỗi PDF có manifest gồm tên, nguồn, năm, số trang, loại tài liệu, ngôn ngữ,
  SHA-256 và trạng thái quyền sử dụng; corpus và manifest được version/hash trong report.
- Holdout không được dùng để tune parser/chunker; acceptance phải chạy được từ workspace
  sạch và không đọc dữ liệu ngoài repository mà không khai báo.

#### Pipeline và lifecycle bắt buộc

Trạng thái canonical:

```text
queued → validating → parsing → detecting_metadata → extracting_tables
       → chunking → persisting → indexing → succeeded
       ↘ review_required / failed / cancelled
```

- Mỗi stage có `started_at`, `finished_at`, progress, duration và error có cấu trúc:
  `error_code`, `message`, `stage`, `retryable`, `action`.
- Tách rõ `ingestion_complete` và `index_ready`; scan-only không được gắn
  `succeeded` hoặc đưa vào index.
- Retry chỉ dành cho lỗi retryable, có backoff/idempotency key và không tạo bản ghi,
  file, chunk hay index trùng.
- Có cancel an toàn, cleanup khi fail/cancel, bounded worker theo CPU/RAM, và phục hồi
  registry sau process restart.
- Concurrent upload cùng SHA-256 được dedupe; hai file khác nhau cùng filename vẫn
  được lưu độc lập.

#### Validation và an toàn file

- Kiểm tra PDF magic bytes/signature, không tin filename/suffix; giới hạn file size,
  page count, tổng text/table size và thời gian parse.
- Upload root được cô lập; filename được normalize; chặn path traversal, symlink và
  đường dẫn ngoài root.
- Từ chối hoặc chuyển review đối với PDF rỗng, hỏng, encrypted, scan-only và
  decompression bomb; có memory guard và timeout.
- Temporary files luôn được dọn sau success/fail/cancel; log không chứa toàn bộ nội
  dung tài liệu nhạy cảm.
- Có test cho file giả, file hỏng, encrypted, file quá lớn, zip/decompression abuse,
  symlink/path traversal và timeout.

#### Metadata học thuật có bằng chứng

Detector phải trả về schema ổn định cho `institution`, `faculty/school`, `program`,
`course`, `course_code`, `document_type`, `academic_year`, `semester`, `version`,
`effective_date`, `issue_date`, `language`. Mỗi field có thể có:

```json
{
  "value": "Kỹ thuật Cơ điện tử",
  "confidence": 0.92,
  "evidence": "Chương trình đào tạo ngành Kỹ thuật Cơ điện tử",
  "source_page": 1
}
```

- Không suy diễn field khi thiếu bằng chứng: trả `null`, confidence thấp và warning.
- Regex/context phân biệt tên chương trình với số tín chỉ; `155 tín chỉ` không được
  nhận là `program`.
- Ưu tiên bìa, quyết định ban hành, header/footer có kiểm soát; hỗ trợ tiếng Việt có
  dấu/không dấu và tiếng Anh.
- Có unit test positive/negative cho từng field và integration test trên toàn corpus;
  không có metadata nghiêm trọng sai trên holdout.

#### Scan/OCR và persistence

- Scan-only trả `review_required` với error code `ocr_required`, không gọi LLM và
  không index text rỗng.
- OCR là background job opt-in, có page/time/cost limit và test cho PDF scan một trang,
  nhiều trang và PDF trộn text/image; Phase 1 không phụ thuộc OCR production để pass.
- Registry dedupe theo SHA-256 nhưng vẫn lưu source metadata, ingestion config,
  parser/chunker/schema version; pipeline version khác không ghi đè artifact cũ.
- Delete document xóa PDF, parsed text, chunks, tables, index, cache và metadata;
  có TTL/cache cleanup và test xác nhận xóa thật.

#### Definition of Done Phase 1

- Corpus thật tối thiểu đạt coverage: ít nhất 5 PDF, tối thiểu 3 loại tài liệu,
  có tài liệu nhiều trang, có bảng, có tiếng Việt/Anh nếu scope hỗ trợ, và có ít nhất
  một PDF scan hoặc layout lỗi; report phân biệt real corpus/fixtures/holdout.
- Mọi chunk hợp lệ có `doc_id`, source, page/page range, `content_type`, source hash,
  parser/chunker version và citation; scan không làm worker treo.
- Job progress/retry/dedupe/cancel/cleanup/restart pass integration/concurrency tests.
- Validation, metadata evidence, registry, delete/TTL và security scan không còn P0/P1.
- Acceptance report được regenerate từ code hiện tại; không được sửa tay để biến fail
  thành pass.
- Sửa `scripts/ingestion/validate_ingestion.py` để acceptance dùng coverage gate thực tế; fixture
  chỉ được báo riêng cho regression, không thay thế corpus thật. Report phải có holdout
  và phải fail closed khi regression test tương ứng fail.

### Phase 2 — Chunking và cấu trúc (10/10 gate)

**DONE; giữ acceptance Phase 1/2, golden fixtures và provenance checks. [Bằng chứng](evaluation/results/ingestion_acceptance.json).**

#### Chiến lược đã chọn

Phase 2 dùng structure-aware chunking với section làm đơn vị ngữ nghĩa, page provenance
làm đơn vị citation, và table là content type độc lập. Heading được nhận diện bằng rule
deterministic có normalization Unicode; không dùng LLM để đoán section. Mọi chunk phải
đạt invariant trước khi persist: kích thước tuyệt đối, section boundary đúng, provenance
đủ và citation mở được đúng trang.

#### P0: golden fixtures và section correctness

- Golden `Điều kiện tốt nghiệp` và `Học phần tiên quyết` pass trên các biến thể: viết
  hoa, đánh số, dấu câu, heading bị tách dòng và heading kéo qua trang.
- Golden test xác nhận đúng heading, section, page, page range, citation và nội dung;
  không ăn sang section kế bên. Bắt buộc pass:
  `test_graduation_golden_fixture_keeps_section_and_citation_page`.
- Heading tiếng Việt có dấu được giữ nguyên bản gốc; normalized form dùng cho search
  (`ĐIỀU KIỆN` → `dieu kien`) nhưng không làm mất numbering.
- Mục lục, header/footer, tên bảng, câu viết hoa dài và mã học phần phải được loại
  khỏi heading bằng context/page-frequency/numbering checks.

#### Heading và section inheritance

- Hỗ trợ Markdown, `1/1.1/1.1.1`, `Điều/Khoản/Mục/Chương`, `Article/Section/Chapter`,
  heading có `: . -`, heading qua dòng và qua trang.
- Heading record có `text`, `normalized`, `level`, `source_page`, `confidence`.
- `heading_path` kế thừa đúng document → page → section → chunk; heading cấp thấp
  không làm mất cấp cao, heading mới chỉ thay level tương ứng.
- Section tiếp tục đúng qua page break; không gán text trước heading vào section sau;
  page range và nested headings phải chính xác.
- Có test section liền kề, nested headings, heading cuối trang, bảng xen giữa section
  và tài liệu layout hỗn hợp.

#### Chunk-size invariant và overlap

- Tính budget sau khi biết context header: `body_budget = MAX_CHARS - header_len -
  safety_margin`; áp dụng cho text và table.
- Final guard chạy sau khi ghép header/content/overlap; nếu vượt thì split lại cho đến
  khi `len(final_chunk.content) <= _MAX_CHARS`.
- Unicode được đo ổn định; overlap không được làm chunk vượt giới hạn; input hợp lệ
  luôn có `diagnostics["chunks_over_limit"] == []`.
- Chỉ ghi overflow khi một đơn vị không thể chia nhỏ hơn, kèm warning và reason rõ ràng;
  không dùng `allowed_margin` để che lỗi splitter.

#### Table chunk contract

- Mỗi table là chunk độc lập, giữ raw values, header đầy đủ, `table_id` ổn định,
  section path, source, page range và `content_type="table"`.
- Table nhiều trang được nối đúng, lặp header khi cần, không trộn với section kế tiếp;
  không tự diễn giải/normalize làm mất dữ liệu.
- Schema tối thiểu: `headers`, `rows`, `units`, `page`, `page_range`, `table_id`,
  `section`, `source`; test cột không đều, ô trống, merged cells, thiếu header và split
  nhiều trang. Bắt buộc pass:
  `test_prerequisite_golden_fixture_preserves_table_header_and_section_boundary`.

#### Provenance, citation và metric

- Mọi chunk có `doc_id`, source name, page, page range, content type, chunk ID,
  heading path, table ID nếu có, parser/chunker version và source hash.
- Citation validator kiểm tra chunk/document tồn tại, page/page range hợp lệ, table ID
  tồn tại và không trỏ vào chunk đã xóa; test end-to-end:
  `query → retrieved chunk → citation → source document/page`.
- Báo cáo corpus thật có chunk count/document, min/mean/p50/p95/max length, overflow,
  overlap, duplicate rate, thiếu heading/citation, sai page range, section boundary failure
  và table mất header.

#### Definition of Done Phase 2

- Hai golden fixture pass; chunk overflow bằng 0 trên corpus hợp lệ.
- Không mất heading, numbering, section path, table header/id hoặc page range; không
  trộn section liền nhau.
- Citation validator pass 100%; mọi chunk có provenance đầy đủ.
- Metric report trên corpus thật và holdout có version/hash; layout thực tế, bảng nhiều
  trang, font lỗi, page rỗng và heading tách dòng đều có test.
- Acceptance JSON, test runtime, tài liệu và code không còn mismatch.

### Phase 1/2 acceptance gate chung

Chỉ đóng Phase 1 và Phase 2 khi tất cả lệnh sau cùng pass trong workspace sạch:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.ingestion.validate_ingestion --input-dir data\corpus\university --holdout data\corpus\university\uet_admission_2025.pdf --output evaluation\results\ingestion_acceptance.json
.\.venv\Scripts\python.exe -m scripts.dev.secret_scan
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
.\.venv\Scripts\python.exe -m scripts.ingestion.benchmark_pdf_pipeline --input-dir data\corpus\university --output evaluation\results\pdf_pipeline_benchmark.json --holdout data\corpus\university\uet_admission_2025.pdf --run-docling --docling-max-pages 30 --run-models --device cpu --batch-size 2 --repeats 1 --model-text-count 8 --memory-budget-mb 8192
.\.venv\Scripts\python.exe -m scripts.ingestion.create_table_review evaluation\results\pdf_pipeline_benchmark.json --output evaluation\results\pdf_table_review.json --complete
.\.venv\Scripts\python.exe -m scripts.ingestion.validate_pdf_benchmark evaluation\results\pdf_pipeline_benchmark.json --acceptance --review evaluation\results\pdf_table_review.json
```

Acceptance report phải được tạo lại từ runtime hiện tại và phải fail closed: nếu regression
test tương ứng fail, report không được ghi nhận `true`. Release note phải ghi commit/version,
Python/OS/package versions, parser/chunker version, corpus hash, holdout hash và thời gian
chạy. Bất kỳ P0/P1 security, reliability, provenance hoặc reproducibility nào còn mở đều
giữ phase ở trạng thái chưa đạt.

### Phase 3 — Embedding và vector search

**IMPLEMENTED; nghiệm thu dense độc lập ban đầu vẫn CONDITIONAL. [Bằng chứng](evaluation/results/retrieval_acceptance.json).**

- dùng fallback hash cho test/dev không tải model;
- production benchmark một embedding model multilingual nhẹ;
- persist index theo corpus/version, không build lại mỗi query;
- thêm FAISS chỉ khi benchmark corpus vượt ngưỡng hiện tại.

Exit criteria: Recall@5 và p95 query được ghi theo từng corpus; restart process không mất index.

### Phase 4 — Basic RAG

**DONE — offline contract; chất lượng model được review riêng ở Phase 7/8. [Bằng chứng](evaluation/results/basic_rag_report.json).**

- lấy top-k context, dựng prompt tiếng Việt/Anh;
- trả lời ngắn và nêu rõ document/page;
- cache câu hỏi giống nhau theo corpus version;
- context budget không vượt giới hạn model/provider.

Exit criteria: câu hỏi fact có answer/evidence; câu ngoài corpus không được bịa.

Phase 4 acceptance: completed with bilingual prompts, provenance-preserving
context/token budgets, versioned query-answer cache, deterministic abstention
tests and offline report in `evaluation/results/basic_rag_report.json`.

### Phase 5 — Citation, grounding và abstention

**DONE — 100%, 10/10 task; nghiệm thu nội bộ ngày 25/10/2026.**
Producer `a21a4cd5` / `grounding-v29`: 400/400 đầu ra pipeline đã được chạy lại
và đối chiếu vật lý độc lập; validator PASS, không có lỗi. Grounding/citation/
abstention P/R 100%, leakage 0, reason accuracy 97,67%; holdout ECE/Brier và
risk 80%/90% đều 0. Ba lượt hồi quy liên tiếp: mỗi lượt 2.663 PASS/2 live SKIP.
Ngưỡng chất lượng, gold và benchmark đã review giữ nguyên. Kết quả tái dùng
426 phản hồi Gemini thật có cùng đầu vào chính xác; không gọi đó là inference mới.
[Hồ sơ đóng Phase 5](evaluation/results/phase5-mixed-absence-20261024/phase5-closure.json).

**Phạm vi đã đóng:** dev120, test130, holdout150 theo contract nội bộ đã được
owner duyệt, có công khai exposure. Source/config/index/raw captures và lịch sử
lỗi được giữ. Public release vẫn cần fresh holdout; không dùng kết quả này để
tự đóng các SLO web/PDF/OCR, cloud hoặc phase khác.

Goal QA toàn ứng dụng là phạm vi riêng và còn ACTIVE. Các mốc thử nghiệm cũ
bên dưới là lịch sử theo source đã ghi; không thay kết luận hiện hành 25/10.

#### Phạm vi và nguyên tắc nghiệm thu

- Bắt buộc `answer`, `citations`, `confidence`, `abstained`; public v2 có
  `claims`, `abstention_reason`, `schema_version`, không lộ internal trace.
- Mọi citation có chunk/document tồn tại trong evidence của request, page/range
  hợp lệ, quote đúng nguồn và mapping đến claim thực sự được hỗ trợ.
- Unsupported/contradicted/ambiguous claims không được hiển thị. Kiểm tra cả
  nội dung `answer`, không chỉ danh sách `claims`; provider không tự quyết định PASS.
- `no_evidence_found` chỉ kết luận về việc tìm kiếm. `document_does_not_mention`
  phải có cơ sở kiểm tra phạm vi tài liệu, không suy từ một top-k không chứa đáp án.
- Giữ benchmark tối thiểu 400 mẫu, dev ≥120/test ≥130/holdout ≥150, đủ positive/
  negative mỗi split, categories và kiểm soát leakage theo release contract.
  Công khai AI/engineering review, exposure và nguồn output; fixture/replay không
  được gắn nhãn live model hoặc human review. Phase 5 dùng independent AI review
  + owner sign-off theo lựa chọn rõ ràng ngày 16/10/2026; human production sign-off, cloud
  acceptance và R-01/R-02 vẫn được báo riêng theo yêu cầu tương ứng.

#### Task chi tiết và thứ tự thực hiện

| ID | Task / phụ thuộc | Đầu ra và điều kiện DONE | Trạng thái |
|---|---|---|---|
| P5-01 | Audit baseline, contract và evidence hiện có | Lập inventory code/schema/policy/calibration/dataset/report với SHA-256; đối chiếu từng yêu cầu, phân biệt legacy/runtime/fixture/replay, giữ thay đổi có sẵn trong workspace. | DONE |
| P5-02 | Siết public/internal schema; sau P5-01 | Validator không crash với JSON sai kiểu, bool giả int, NaN, duplicate/empty ID, thiếu claim/citation, unmapped citations hoặc nested internal fields; HTTP luôn trả public contract hợp lệ. Regression âm và dương đạt. | DONE (offline contract) |
| P5-03 | Citation/provenance integrity; sau P5-01 | Kiểm chunk/doc/page/range/table/quote, request isolation, evidence trùng ID hoặc metadata lỗi; không nhận quote ngoài nguồn hay coordinate giả. Có test adversarial qua generator/API. | DONE (offline provenance) |
| P5-04 | Claim grounding và nội dung hiển thị; sau P5-02/03 | Claim/evidence alignment kiểm số, mã, năm, đơn vị, phủ định, multi-claim và partial; chặn answer chứa fact không nằm trong supported claims, kể cả provider khai báo an toàn. Leakage bằng 0 trên bộ kiểm tra. | DONE -G5-02 validated on400 current-pipeline outcomes; unsupported/contradicted leakage0, precision/recall100%. |
| P5-05 | Abstention taxonomy và phạm vi kiểm tra; sau P5-03/04 | Phân biệt thiếu retrieval với tài liệu đã kiểm tra không đề cập; xử lý unsupported, contradiction, ambiguity, conflict, provider/citation errors bằng reason và thông báo VI/EN phù hợp; không khẳng định vắng mặt toàn tài liệu từ top-k. | DONE -G5-03 abstention P/R100%, reason97.67%; complete-source audit required for document absence. |
| P5-06 | Audit benchmark và phép chấm; sau P5-01 | Kiểm 400 mẫu, split/group/category/source quotes/review metadata; sửa metric đếm nhầm/missing values/fail-open. Citation precision và abstention precision đo tự động trên test và holdout, có denominator; giữ gold và lịch sử exposure. | DONE (reviewed400 frozen; Phase5 owner approval; disclosed exposure; physical validation PASS) |
| P5-07 | Confidence/calibration và cache version; sau P5-04/05/06 | Không tin confidence của provider; fit dev-only, kiểm artifact version/checksum và chống non-finite values; ECE/Brier/risk báo đúng population. Cache không tái dùng kết quả sai schema/policy/source/scope. | DONE -unchanged dev-only fit reverified on current120 dev outcomes and pinned; holdout ECE/Brier/risk0. |
| P5-08 | Current-source runtime qualification and regression; after P5-02..07 | Capture current-source outputs, fit dev-only calibration and qualify held-out; preserve raw failures and source/config/index bindings. | DONE -400 current-pipeline outcomes under exact-input genuine HTTP checkpoint protocol; 3 full regressions each2,663 PASS/2 opt-in SKIP. |
| P5-09 | Release validator and independent report validation; after P5-06..08 | Recompute metrics, physical source/review/config/calibration bindings and population; all5 quality gates required. | DONE -automatic independent physical recomputation matches400/400; all5 internal gates PASS, thresholds unchanged. |
| P5-10 | Handoff, đồng bộ roadmap và cleanup; sau P5-09 | Tài liệu contract/operations/release hiện hành, lệnh tái hiện, completion receipt ràng buộc source/config/dataset/results; chỉ xóa file tạm không còn tham chiếu, giữ baseline và `plan.md` tracked. Chỉ cập nhật DONE/100% sau khi audit đủ 10 task và gates. | DONE -roadmap/handoff/closure synchronized, task-owned test scratch cleaned; raw captures, grants, failures and historical baselines retained. |

#### Historical status as of 23/10/2026

Historical23/10: **7/10 task DONE = 70%; Phase 5 remains incomplete.** Source-bound fact/citation repairs and direct-scope preflight are DONE. Strict diagnostic replay has63/63 supported claims over65 replayable rows, but is not native acceptance. Owner-approved packet9f00be14 bound actual source `ebf1fd3a` correctly:1 successful initial JSON,1 token measurement and1 failed full-PDF generation (HTTP503), then stop;0 evaluable outcomes, test-008 unsubmitted. Shared quota at stop:253/500;2 unused POSTs discarded, no retry/key rotation. Compact PDF follow-up removes duplicated text while preserving all13 original pages and citation verification;819 affected tests PASS, provider validation pending. Full400 current-source outcomes, dev-only calibration and all5 gates remain required. Thresholds unchanged. [Current evidence and remaining work](docs/grounding/phase5_completion.md).

#### Earlier failed attempt - 22/10/2026 (historical)

Phase 5 vẫn 7/10 task DONE; chưa nâng task nào chỉ từ capture dở dang. Pre-repair v14 dev run dùng packet `60fd3232aefa1c4b124eee457efa7ba3f31fcba11bea90954e0e8d47c2fb3d23`, source `86a177edbc458ccd8d9c07cc88f1ecebf156d36bbbc5a0020c4e9496ba5aa564`, runtime `be93b3be2b1bee1c37b98992eadc32aa70f56a51fd226dba45679bf9b12e347f`, index manifest `13523be6ca09e6e54126ae40c596df00f01cd877f02f5692b0d03045aa38111a`. Journal có87 provider POSTs và105 prediction rows; collector mất tiến trình trước `run.json`, nên official predictions vẫn0. Chấm chẩn đoán tạm 105 rows: grounded claim P/R91.07%/89.47%, unsupported leakage5.36%, citation P/R90.20%/89.47%, abstention P/R98.15%/100%, reason accuracy96.23%, Brier0.045637, ECE0.055831; chưa đo holdout calibration/risk và các metric tạm không thay thế gate. Auto-review chặn việc gửi tiếp15 dev rows (tối đa27 POSTs) vì chưa nhận diện được ủy quyền chính xác trong yêu cầu hiện tại; không dùng đường vòng. Giữ nguyên journal gốc; test/holdout chưa gửi.
P5-02…05 đóng ở phạm vi code/contract đã kiểm thử; chất lượng official vẫn phải
qua P5-06…09 và G5-01…05, không suy từ fixture hoặc replay.

#### Historical source remediation and native evidence -23/10/2026

Targeted fixes now handle exact prerequisite-table lookup deterministically, constrain answer scope in the grounding prompt, prune unrelated citations only when a perfect supporting citation is present, and invalidate old grounding cache entries. Current committed source identity is commit 9ba97af0aceb78c93e22a3011abb56f4dc5e539b; source SHA-256 0f975a8879652de73d94a8d5f6205562ede915076a08a6bfb365aa2b174bda36; runtime SHA-256 db454eb10dc74bf3bd6b277fbef8450016f03a4feb50a01bb02560a8e3c3723a. The full offline regression completed with 2352 PASS and 2 opt-in live SKIP; source and runtime fingerprints match before and after the run. Receipt: `evaluation/results/phase5-acceptance-20261021/current-source-full-regression-20261023.json`.

The approved v2 packet and its native captures bind the earlier source SHA 91a68a42c1bac692eb7d34e942da3574a2f30810d2e63699e6587491cf36e5c4 and runtime SHA cd001c4d3d7683c90ef13d21ea21d3ae1b1e3878bdc6e7096bd8ea8fe6fc04a2. Across disjoint runs it touched 103/120 dev rows, with 57 distinct IDs having a successful real model JSON capture and 99 journaled provider POST starts. The 95 evaluable rows show diagnostic grounded claim P/R 97.96%/96.00%, unsupported leakage 2.04%, contradicted leakage 0%, citation P/R/completeness 95.56%/96.00%/96.00%, citation coordinate validity 100%, abstention P/R 98.04%/100%, reason accuracy 100%, ECE 0.039699 and Brier 0.015304. These are partial, pre-fix diagnostics; the residual unsupported claim and incomplete population fail qualification. No prediction was generated by the repaired source, so the old captures are not relabeled or reused as current-source evidence.

The owner-pasted Gemini Chat result is retained as supplementary source review: 33/33 IDs returned, but its local audit found 13 records with issues (5 records with quote corrections, 6 absence claims without enough declared full-source inspection, 5 reason mismatches, and 1 out-of-bounds page; categories overlap). The model/session identity was not verifiable. It contains 0 CampusAI predictions and cannot qualify runtime quality.

For current commit `9ba97af0`, official_predictions=0; no current-source calibration artifact or test/holdout run exists. The prepared packet SHA `49c57804767a8c4ef62763b76732c55defbb9e03777b5c5e1fc4d6b368630345` has matching source/runtime hashes but embeds the earlier commit label; it has 0 posts and remains unapproved. A fresh current-commit capture must preserve the exact prompt and HTTP-body bindings.
Historical r2 only: P5-07 implementation and artifact had120/120 dev outcomes and a dev-only
isotonic fit, payload checksum `1ff16439e70251cdf7e92770c8371547ec3d7807f8dd7edbad13632d862d03ca`.
Giữ1 timeout trong dev; không tuyên bố quality PASS. Test130 hoàn tất; holdout
dừng139/150 ởHTTP429, provider xác nhận500 requests/ngày. Tổng389 outcomes,
402POSTs,400 phản hồi model thành công;11 câu chưa chạy, official0. Grounding
precision53,06%, citation precision55,93%, abstention precision70% trên baseline
chưa đạt ngưỡng. Không quy mọi lỗi chất lượng thành lỗi quota hoặc lỗi grader.
Bản sửa mới chặn chọn nhầm bảng chỉ tiêu và suy hồ sơ cá nhân từ quy định chung;
baseline native cũ không được ghi thành kiểm chứng source mới.

- Đã đóng thêm P5-04 và P5-05: kiểm claim theo quote hiển thị, số/mã/đơn vị/phủ
  định, no-partial requests, reason VI/EN và phạm vi whole-document có giới hạn.
  Quote rỗng không vào cache; locator Điều/Article không được dùng thành quantity.
- [Focused281 PASS](evaluation/results/phase5-remaining56-20261021-v11/contract-closure.xml);
  full regression: **2182 PASS,2 live SKIP**, source đầu-cuối trùng nhau
  ([run](evaluation/results/phase5-remaining56-20261021-v11/full-closure-run.json)).
  Parser/chunker được sửa đồng bộ; các phase khác giữ trạng thái/evidence lịch sử.
- [Replay42/42 đúng hành vi](evaluation/results/phase5-remaining56-20261021-v11/dev66-closure-replay.json):
  unsupported/contradicted leakage0 trên phần có prompt trùng.24 ca không có
  capture khớp prompt mới không được chấm. Đây không phải inference mới.
- Benchmark gốc400/400 được giữ; candidate680 có680 source findings dùng được,
 23/23 temporal legacy có status; cross-split family leakage0. Owner đã review
 nội dung và cho phép nghiệm thu Phase5 với exposure công khai; public release
 vẫn cần fresh holdout. [Frozen400 và physical validation](evaluation/results/phase5-acceptance-20261021/benchmark-validation.json).
- Native dev66 giữ24 outputs từ batch dừng và31 outputs từ45 ID chưa từng gửi;
  không retry ID cũ, không dùng gold làm input. Official predictions=0.
- Đã dọn helper/draft/fixture tạm không cần; source, raw captures, baseline và
  evidence vẫn giữ. [Handoff hiện hành](docs/grounding/phase5_completion.md).

#### Gate đóng Phase 5

Chuẩn review hiện hành: [phase5-ai-owner-v1](docs/grounding/phase5_ai_review.md),
được owner chọn rõ ràng ngày 16/10/2026. Đây là thay đổi yêu cầu người review của
Phase 5; không đổi thresholds hoặc các yêu cầu human ở phase khác. Owner đã
cho phép dùng benchmark đã review có exposure cho Phase5; public release vẫn
bắt buộc fresh holdout.
Ủy quyền policy không tự phê duyệt benchmark chưa hoàn tất.

| Subtask tiếp theo | Đầu ra / phụ thuộc | Trạng thái |
|---|---|---|
| P5-06a — AI/owner review contract | Giữ đường human; AI identity, source findings và artifact hashes, per-row decisions, owner policy authorization tách khỏi approval bản frozen; fail closed và CLI pending template. | DONE — 50 focused PASS |
| P5-06b — Audit tái sử dụng | Giữ 400/400; triage từng annotation; source review đủ 23 temporal gồm 21 warnings; xuất correction proposals riêng và recompute 15 leakage families. | DONE — audit, source reviews và owner content approval |
| P5-05a — Source-scope integration | Physical source/hash/authorized roots/full-text budget; tối đa1 follow-up; giữ page/cache/temporal scope và provider errors; thiếu text/hình fail closed. Implementation contract đóng tại P5-05; official native reason accuracy tiếp tục ở P5-08/G5-03. | DONE —281 focused PASS; full regression PASS; replay/source-scope diagnostics có giới hạn công khai |
| P5-06c — Benchmark revision và families | Hoàn tất sửa/review 400 legacy proposals và5 fresh atomic corrections; giữ ancestry/gold gốc. Giữ lịch sử exposure của test/holdout; fresh study dành cho public release theo lựa chọn owner. | DONE —680/680 findings; leakage0; acceptance400 frozen |
| P5-06d — Review độc lập bản sửa và owner sign-off | Reviewer AI khác annotation author kiểm từng dòng, atomicity, temporal scope và inspected pages; owner content/exposure decision gắn benchmark và review bundle cụ thể. | DONE —9 actual reviewer tasks; owner-approved Phase5 scope; physical validation PASS |
| P5-07a/08a - Native and calibration | Freeze source/config/index; run dev, fit dev-only calibration, pin before test/holdout; preserve failures and exposure, never send gold. | DEV DONE - candidate e6134dc: 120/120 dev outcomes, 78 real JSON model outputs, 90 provider POSTs, 0 failures. Dev quality: grounded/citation/abstention P/R 100%, unsupported/contradicted leakage 0, reason accuracy 96.67%, raw ECE/Brier 0.043524/0.005536; dev-only calibration pinned at SHA-256 `1ad5816bf8985128987fccf3116ab27c14b5905382efd3a770cfcff392817b43`. Held-out calibration remains unmeasured. |
| P5-09a — Validator implementation | Tự tính lại metrics/bindings/population; thiếu review, source, calibration hoặc quality phải fail closed. | DONE —regression PASS; không đồng nghĩa release PASS |
| P5-08b — PDF scope implementation | Opt-in tối đa4 PDF/100 trang/8MiB; đo token trước inference; khóa binary và HTTP body, journal bền, không retry. | DONE —95 kiểm thử native/scope/integrity PASS; provider probe PASS2/2 POSTs,4 trang hình đối chiếu đúng; native quality còn mở |
| P5-08c — Truy hồi đúng PO/PLO | Câu hỏi chỉ rõ namespace phải nhận định nghĩa từ source body đúng loại, giữ scope/filter và candidate-generation của phase khác. | DONE —131 focused PASS cùng nhánh PDF; không tính là model inference mới |
| P5-08d - Current-source regression | Run offline suite after fixes, keep live opt-in tests separate, and verify source identity. | DONE -2,570 PASS/2 opt-in SKIP after the minimal runtime repair. Source/runtime stayed identical before and after the run. Earlier separate live tests both PASS on their recorded source; they are not current-source live results. Evidence: evaluation/results/phase5-mixed-absence-20261024/checkpoint.json and minimal-runtime-full.xml. |
| P5-08e — Tên môn, ngày giờ và giá trị trả lời | Giữ proof cột tín chỉ theo tên chính xác; chuẩn hóa ngày/giờ theo toàn giá trị; chặn heading không có số và giữ phạm vi yêu cầu quote-only. | DONE —265 focused PASS; full2305 PASS/2 live SKIP; cần qualification native mới |
| P5-08f — Giữ liền nhãn và giá trị khi chunking | Sửa nhận diện nhầm dòng đơn vị thành heading, kiểm corpus thật và tạo index mới; giữ nguyên index/captures baseline. | DONE — structure-v5/table-v3; 246 focused PASS; v14 rebuilt 14/14 source PDFs, 528 chunks/79 tables, manifest integrity PASS; MAI Semester 4 “Strength of Materials — 3 credits” retrieved top-1 with explicit header/scope; v13 baseline retained |
| P5-08g - Freeze source for qualification | Keep immutable Git source, physical index/config/benchmark bindings and original shared quota/circuit state. | DONE - historical frozen candidate `cb7220d4b8e10e22114ae11ca353a146d41c1c09`; source/runtime `df723d7b8237e352b09979ffa6d972904554b4c93cce79376f4befacb9bb0e37` / `b740ba08d04a15149958312a078447bb2f735cb796b4d033c685e66c3bae3a1b`, identical to835-test source. Derived preflights f5d7501d/53339a1e contain exactly the same approved API bodies/PDFs as c2540baa/064cd1d6. Caps216/675 include earlier75 dev POSTs. Owner permits one same-key503 recovery and confirms3 separate projects; per-project quota carries conservative prior accounting without resetting the original ledger. |
| P5-08h - Post-test source and grounding repair | Cite the requested exact table row/entity; support natural admission fields and literal discipline identifiers; resolve missing subjects; preserve scope years and original headings; execute and validate the frozen source actually named by the packet. | DONE - final535 affected cross-phase tests PASS; full2410 PASS/2 live SKIP before final follow-up fixes. This closes the code repairs, not native acceptance. |
| P5-08i - Bind factual fields to their own source roles | Resolve admission dates, quota, validity, awards, scale, coefficient, bonus cap and registration obligations from literal source statements. Preserve every conflicting alternative; reject wrong events, subjects, years and extra requests. Check an explicitly selected complete source when retrieval is empty, within the existing one-follow-up budget. | DONE -805 affected tests PASS, including Phase6/7 candidate generation and temporal/product checks. Strict replay:65 replayable rows,63/63 supported claims, citation precision/recall100%, leakage0;0 new POSTs/official predictions. test-007 still has a wrong abstention reason;test-008 requires a fresh inference. |
| P5-09c - Count all spans proved by one citation | A physical citation may prove multiple reviewed evidence spans; retain the original gold denominator and validate every span/coordinate. Incomplete quotes, wrong pages and redundant citations must still lose credit. | DONE - regression PASS; no change to release thresholds or gold annotations. |
| P5-08j - Preflight direct complete-source requests | When retrieval is empty, plan the actual complete-source call directly; do not add a nonexistent initial inference or duplicate follow-up. Preserve exact HTTP body locks and whole-path budgeting for mixed requests. | DONE -807 affected tests PASS; a direct PDF path costs2 POSTs and a mixed initial/follow-up plus direct path costs5. Local transport regression verifies the packet executes within its exact cap. |
| P5-08k - Remove duplicate PDF transcriptions | Keep exact original PDF bytes and every page; send page/citation locators rather than another full transcription. Preserve local physical text-index checks and reject PDF-coverage metadata without actual attachments. | DONE -819 affected tests PASS; identical13-page PDF, textual prompt30,772→7,082 characters. Actual compact probe completed5/5 POSTs and both absence cases correctly; PDF token measurement20,121→10,132 for test-007. This proves the bounded probe, not universal provider reliability. |
| P5-08l - Block mixed positive/absence publication | Positive fragments cannot certify that the rest is absent from a document. Trigger the existing bounded source audit; reject partial completion after full-source review. Keep normal negated facts and quoted examples valid. | DONE implementation - actual captured faulty response now abstains pending complete-source audit;835 cross-phase tests PASS. Cache policyv24. Native validation on the repaired source remains P5-08/09. |
| P5-08m - Frozen cb7220d4 dev120 and calibration | Complete native dev120 on the frozen repaired source, meet existing thresholds, fit dev-only calibration and pin before held-out. | DONE -120/120 native outcomes; grounding/citation/abstention precision and recall100%, reason96.67%>=95%, leakage0.97 POSTs on frozen cb7220d4 source;172/216 across the packet lineage. Fresh dev-only fit/pin SHA1ad5816b…; two reason errors retained. Test130 failed; holdout stopped at59. This dev fit does not certify the subsequent repaired source. |
| P5-08n/09d - Repair observed request, citation and scoring failures | Preserve whole hierarchical locators, resolve only literal same-PDF page proof, retain programme group/quoted rows, normalize complete-source absence and distinguish dated facts from version requests. Count composite claims against atomic reviewed facts without inflating denominators. | DONE code repair -2547 full regression PASS; both separate live opt-in tests PASS. Programme/assessment/deferral facts remain literal source projections. Concurrent10-PDF registry publication passed15 stress iterations. Native release evidence remains open. |
| P5-08o - Separate tokenization and inference quota | Preserve actual endpoint journals and every generation attempt; countTokens uses its documented separate quota. | DONE -218 uniquely proven countTokens reservations reclassified without resetting counters or deleting attempts;107 focused tests and full2547 PASS. Evidence: evaluation/results/phase5-mixed-absence-20261024/count-token-accounting.json. |
| P5-08p - Freeze repaired source and exact request packets | Pin the2547-test source, preserve physical bytes/index/benchmark, prepare bounded new native packets without sending gold. | DONE -commit b1ab8adc pushed; isolated candidate has identical source/runtime d54e1726?/268414bf?. Dev120:204 planned POSTs/cap216; test130+holdout150:617 planned/cap735. New scoped budgets authorized by call_cc8892158aa1465f827759789da01de3; no prior spend refunded. Existing172/216 dev and267/675 held-out spending retained. |
| P5-08q - Complete local dev outcomes on frozen repaired source | Execute the actual52 no-model dev paths with network forbidden and verify capture integrity. | DONE -52 outcomes,0 POSTs, all applicable grounding/citation/abstention metrics100%; no model output claimed. Physical review evidence for all400 records validates with0 errors. Dev collection has since reached118 successful outcomes; held-out waits for complete dev120 and dev-only fit. |
| P5-08r - Qualify native dev on b1ab8adc | Complete dev120 using the approved exact packets and three independently metered projects, then fit/pin calibration. | DONE -120/120 successful native pipeline outcomes; grounded/citation/abstention P/R100%, leakage0, reason96.67%.81 real JSON responses;95 selected-run POSTs,96 campaign POSTs including retained10054 failure. Same-key recovery owner-authorized; fresh dev-only fit34b8e125? pinned before held-out. |
| P5-08s - Correct complete ASCII Vietnamese claim matching | Accept only a full ordered transliteration with identical quantities/roles/conditions and literal physical citations; preserve the inference snapshot and prove scorer-only changes separately. | DONE -20 new tests and full2567 PASS/2 live opt-in SKIP; inference runtime268414bf? unchanged. No gold, thresholds, prompts or captured output edited. Explicit physical source binding rejects changed application, collector, scripts, configs or dependencies. |
| P5-08t - Fix observed bilingual scope and unpublished-citation failures | Preserve section/article/page identity across Vietnamese/English and complete source audit before discarded diagnostic citations. | DONE -minimal3 production-file fix;162 focused and2570 full tests PASS/2 live opt-in SKIP. The4 actual failed captures now produce correct diagnostic outputs with0 new API calls. Cache grounding-v27; no gold, prompt or threshold change. New-runtime native qualification still required. |
| P5-08u - Qualify current v27 dev and pin calibration | Finish120 current-source dev outcomes, pass the existing dev quality thresholds, fit only these captures and lock before held-out. | DONE -producer `3fcd4a46`:120/120 outcomes; grounded/citation/abstention P/R100%, reason96.67%, leakage0.81 real JSON outputs,97 selected-run POSTs/103 campaign POSTs including retained failures. Fresh dev-only fit1ad5816b… pinned before held-out; identical semantic checksum does not mean an old fit was reused. |
| P5-08v - Mixed absence and assessment-recency repair | Block unrelated policy answers to personal realised events, recognise qualified source-absence statements and distinguish assessment recency from document-version requests. | DONE -producer f35f3c37,3 consecutive full suites each2,625 PASS/2 opt-in SKIP;180 focused metric/capture/native-scoring tests PASS. Production bytes fixed for qualification; fresh held-out quality remains P5-09b. |
| P5-08w - Atomic policy facts and actual personal events | Resolve component credits, minimum rank/class size, extension deadline and council level from literal fields; require personal records for actual individual outcomes. | DONE -184 focused tests,3 full suites each2,663 PASS; all9 observed v28 quality errors resolved,400/400 v29 internal acceptance PASS. No benchmark IDs/labels/expected values in runtime. |
| P5-09b - Release quality validation | Validate400 current-pipeline outcomes, dev-only calibration and all5 unchanged quality gates. | DONE -v29-final-score.json PASS, errors[]; dev120/test130/holdout150; grounded/citation/abstention P/R100%, reason97.67%, leakage0, holdout ECE/Brier/risk0. Source a21a4cd5 physically retained; no inference/approval relabeling. |
| P5-09c - Internal closure contract | Remove redundant inference-only closure work without reducing quality; retain public-release requirements. | DONE -owner25/10 authorization recorded in grounding_release_gates.md: exact case/model/config/index/HTTP-body reuse only, gold-free current reprocessing, deterministic selection and fail-closed physical verification. No numeric thresholds or reviewed population changed; actual physical acceptance PASS400/400 at P5-09b. |
| P5-09d - Physical checkpoint validator | Recompute current outputs from real exact-body captures; fail closed on missing/tampered inputs and public-release promotion. | DONE -197 focused tests; actual independent recomputation matches400/400 on v29. |
| P5-10a - Handoff checkpoint and cleanup | Synchronize roadmap/contract/operations and retain reproducible source/raw/baseline evidence. | DONE -phase5-closure.json and completion handoff bind final source,400 outcomes,3 regressions and budget history; temporary test stores removed. |
| P5-10b - Close10/10 Phase5 | All5 internal gates, qualified400, regression/handoff/cleanup. | DONE -100% Phase5 internal acceptance; whole-app QA goal and public fresh-holdout remain separate. |

Gemini Chat returned supplementary source-review results for 33/33 priority cases.
The audit found 20 source-supported answer contents and 33 answer/abstain decisions
matching gold, but 13 records have issues: 5 quote corrections, 6 absence claims without
enough declared full-source inspection, 5 reason mismatches, and 1 out-of-bounds page
(overlapping categories). Model/session identity was not verifiable. These results are
source review only, with 0 CampusAI predictions; they do not replace native qualification.
[Audit](evaluation/results/phase5-acceptance-20261021/gemini-chat-review33-audit.json)

Owner đã cho phép giảm nhẹ chuẩn nếu cần; numeric thresholds chưa đổi.
Owner content/exposure approval và dev calibration đã hoàn tất. Native quality
gates còn phải đạt trước khi Phase5 PASS; public release cần fresh holdout.

| Gate | Điều kiện bắt buộc | Status |
|---|---|---|
| G5-01 — Schema và provenance | Required public fields hợp lệ 100%; citation coordinates/quotes/mapping hợp lệ 100%; internal-field leakage = 0; malformed JSON không làm crash validator/API. | PASS -internal Phase5 |
| G5-02 — Grounding | Unsupported/contradicted public-claim leakage = 0; grounded claim precision ≥99%, recall ≥95%; claim-citation precision/recall/F1 ≥95%; kiểm cả `answer` và claims. | PASS -internal Phase5 |
| G5-03 — Citation và abstention | Citation precision ≥99%, recall/completeness ≥98%; abstention precision ≥99%, recall ≥98%, reason accuracy ≥95%; test/holdout và từng category có số lượng mẫu rõ ràng. | PASS -internal Phase5 |
| G5-04 — Dataset và confidence | ≥400 mẫu đúng split/group contract; calibration count ≥400, dev-only fit, holdout ECE ≤0,05/Brier ≤0,08; risk tại coverage 80%/90% ≤1%/2% trên publishable holdout; checksum/version hợp lệ. | PASS -internal Phase5 |
| G5-05 — Reproducibility và regression | Report được tái tính/kiểm bindings tự động, source fingerprint đúng cả workspace hiện tại; focused/full offline checks đạt, không tính live SKIP là PASS; handoff/cleanup và audit 10/10 task hoàn tất. | PASS -internal Phase5 |

Nguồn chuẩn: [grounding contract](docs/architecture/grounding_contract.md),
[ngưỡng đã khóa](configs/grounding_release.json),
[release gates](docs/grounding/grounding_release_gates.md).
Tiến độ tính theo task có evidence DONE / 10, không suy 100% từ việc code đã tồn tại.

### Phase 6 — BM25 + hybrid + RRF

**DONE trên profile RC3 lịch sử. [Bằng chứng](evaluation/results/hybrid_release_manifest.json). Deployment mới vẫn cần qualification riêng.**

- query routing: exact code/course trước, hybrid sau;
- filter theo document/program/year khi người dùng chọn;
- normalize score, RRF, dedupe chunk và giới hạn candidate;
- đo latency riêng BM25, dense, fusion.

Exit criteria: hybrid thắng từng retriever đơn trên Recall@k mà p95 vẫn phù hợp free CPU.

<a id="phase-7--hoàn-thiện-chất-lượng-sản-phẩm-phạm-vi-tinh-gọn"></a>
### Phase 7 — Hoàn thiện chất lượng sản phẩm, phạm vi tinh gọn

**Trạng thái: DONE — 100% phạm vi Chat-quality owner chốt ngày 13/10/2026.**
Mục tiêu là hoàn thiện retrieval, câu trả lời, citation, scope, abstention và
fallback trên core hiện có. Optional reranker giữ tắt; không bắt làm lại nhánh
20 task / 19 gate để đóng phạm vi này.

#### Hạng mục, điều kiện và kết quả

| ID | Nội dung giữ trong kế hoạch | Điều kiện / kết quả hiện hành |
|---|---|---|
| C7-01 | Snapshot baseline/source/index/calibration, cấu hình, flag và namespace cache; bảo toàn baseline 10 documents và index 15 documents. | DONE: physical files/hash được kiểm tra, runtime và corpus khai báo đúng, reranker tắt. Snapshot cũ không tự nghiệm thu deployment mới. |
| C7-02 | Retrieval/context/scope cho mã môn, tên môn, bảng, số liệu, nhiều hop, selected text và doc/year/program; budget/cache. | DONE trên population đã khóa: Recall@5 test ≥98%, holdout ≥95%; candidate all-gold coverage ≥95%; không hồi quy evidence, không mất provenance/scope/citation. |
| C7-03 | Prompt/evidence/schema/rubric khóa trước output; nhận raw Chat, đối chiếu nguồn và replay baseline/current qua ứng dụng. | DONE: 42/42 đáp án đúng, 26/26 negative đúng; 74/74 grounded claims, 90/90 supported claim-citation pairs; 136 HTTP replay requests. Review đúng role AI, không nhận là fresh hay live latency. |
| C7-04 | Security/grounding regression, cache isolation, malformed evidence, provider/index errors, timeout, restart và fallback. | DONE: 60/60 fault cases, 12 categories, hai process; giữ required regressions và không có provenance/scope/citation leak. Không chạy GPU probes chỉ phục vụ reranker đang tắt. |
| C7-05 | Workload HTTP end-to-end có LLM thật trên một profile, cold/warm/cache on/off, latency/error/RSS/usage. | DEFERRED — NOT PASSED, chuyển R-01 trước release. Giữ workload 100 HTTP/54 provider calls và ngưỡng p95 ≤10 s, timeout ≤0,5%, RSS ≤75% RAM; không dùng Chat/replay để nhận live PASS. |
| C7-06 | Handoff với source/config, raw/checksums, lệnh tái hiện, giới hạn, restart/fallback và cleanup có binding checks. | DONE trong scope điều chỉnh: 1.473 offline tests PASS, coverage 90,60%, secret/diff/bindings đạt; hai live integrations có evidence riêng. Phụ thuộc C7-05 của hợp đồng live cũ còn mở ở R-01, không tự nhận 6/6 live PASS. |

Ngưỡng quality giữ nguyên: citation precision/groundedness ≥98% mỗi primary
split, answer FPR ≤1%, accuracy/citation recall không giảm quá 0,5 điểm % so với
baseline tương thích; hard/multihop phải đủ hop support. Với cùng metric và
population, dùng ngưỡng nghiêm hơn trong
[grounding_release.json](configs/grounding_release.json): citation/grounded
claim precision ≥99%, recall/completeness ≥98%, coordinate validity 100%, zero
unsupported/contradicted claim leakage và schema-invalid outputs. Không bỏ case,
strata hoặc sửa gold để đạt điểm.

#### Phần đã hoãn và phần phải giữ

| Phần | Quyết định |
|---|---|
| Model/input sweep BGE/GTE, learned ranking, router/forest và uplift +3% | DEFERRED cùng optional reranker; không cần cho core đang bàn giao. |
| Fit/freeze routing riêng reranker, cap sweep, F1/F2/F3 và GPU qualification | DEFERRED; giữ code, validators và evidence nếu cần bật tính năng sau này. |
| Nhiều profile/concurrency, reranker canary và rollout exercises | DEFERRED với reranker; deployment thật vẫn cần qualification phù hợp tải thực tế. |
| Source/schema, lifecycle, fault checks và historical baseline đã phù hợp identity | TÁI SỬ DỤNG; không lặp inventory/benchmark/API chỉ để thêm report. |
| Answer/citation/negative, multi-hop support, scope, cache và fallback | GIỮ trong core acceptance; không lược bỏ để làm đẹp trạng thái. |

19 gate qualification vẫn phải đạt trước khi bật reranker production. Kết luận
RELEASE-BLOCKED lịch sử, các failed cycle và activation guard giữ nguyên; chúng
không phải backlog đóng lại scope Chat hiện tại.

#### Cách nghiệm thu và hồ sơ giữ lại

1. Khóa request/prompt/evidence/schema và source/config identity; không xuất gold
   hay arm label cho Chat.
2. Nhận đủ raw output có ID; review từng answer/claim/quote với source và rubric.
   Lỗi format và normalized copy phải ghi riêng, giữ nguyên raw.
3. Replay actual baseline/current applications, chấm paired quality và negative;
   sửa lỗi có source proof, chạy regression bị ảnh hưởng, ghi exposure rõ ràng.
4. Kiểm tra snapshot/retrieval/fault bindings và final suite, rồi lưu handoff.
   Không coi replay timing là API timing.

Bằng chứng: [paired quality review](evaluation/results/phase7-chat-quality-20261013/paired-quality-review.json),
[completion audit](evaluation/results/phase78-chat-quality-completion-20261013.json),
[handoff](docs/phase7_product_handoff.md). Live performance còn mở trong R-01.

### Phase 8 — Evaluation và benchmark

**Trạng thái: DONE — 100% phạm vi Chat-quality owner chốt ngày 13/10/2026.**
Mục tiêu là benchmark university có version/provenance, bộ chấm có định nghĩa
rõ và baseline ứng dụng đã được kiểm tra trước khi mở rộng hoặc ablation.

#### Benchmark và quy định đánh giá

- Frozen v5 có 300 câu: 140 test / 160 holdout, 117 connected groups; kiểm tra
  group/split, schema, source evidence và đủ loại câu hỏi. Bộ này đã exposure,
  chỉ nhận là regression, không phải fresh validation.
- 30 câu bổ sung đã Automated AI Review: 30 Accept / 0 Reject / 0 Pending;
  270 câu lịch sử giữ provenance review cũ. Không giả human signature hoặc
  ghi OFFICIALLY_APPROVED khi chưa có phê duyệt đúng role.
- Câu hỏi/đáp án phải rõ ràng, tự nhiên, có evidence thực sự hỗ trợ, không lộ
  đáp án hoặc sửa câu hỏi chỉ để hợp thức hóa gold sai.
- 43 annotation học kỳ được đối chiếu nguồn trong overlay riêng; benchmark
  frozen giữ nguyên. Validator quote nhiều dòng giữ đúng raw cells/source,
  không ghép hàng hoặc thay số để khớp output.
- Giữ ID riêng cho từng case khi gộp file Chat; payload không kèm gold/rubric
  đáp án. Chỉ gửi câu thiếu hoặc bị ảnh hưởng bởi thay đổi cần kiểm chứng.

#### Các bước và kết quả đã hoàn thành

| Bước | Nội dung | Kết quả |
|---|---|---|
| P8-01 | Chuẩn bị benchmark và metric/collector | DONE: benchmark versioned, schema/group/split/source validation và tests có evidence. |
| P8-02 | Review và freeze | DONE — AUTOMATED_REVIEW_COMPLETE: 30/30 supplemental decisions, giữ historical provenance và frozen v5; không phải chữ ký con người. |
| P8-03 | Thu output và replay baseline ứng dụng | DONE: 145 recorded Chat outputs + 155 nhánh negative local; đủ 300 request, không thiếu/trùng case, không gửi lại qua API. |
| P8-04 | Chấm content, citation, grounding, abstention và schema | DONE trong scope Chat: 145/145 đáp án nguồn đúng, 155/155 negative đúng, 178 supported claims, schema ứng dụng 300/300; false abstention 0. |
| P8-05 | Review baseline, bindings và kết luận | DONE: current runtime/source tương thích, normalized handoff hợp lệ 145/145 và không đổi giá trị; final suite/coverage/cleanup đã kiểm tra. |

#### Metric và giới hạn bắt buộc báo cáo

| Metric / phạm vi | Kết quả và cách hiểu |
|---|---|
| Semantic answer quality | 145/145 đúng theo AI source review; không nhận là nhãn con người hoặc bảo đảm chất lượng trên mọi query mới. |
| Negative / public schema | 155/155 abstention âm đúng; 300/300 phản hồi ứng dụng hợp schema. |
| Source citation / grounded claim | 145/145 có quote/toạ độ nguồn hợp lệ; 178 claim công bố được support. |
| Exact-gold citation identity | 144/145 (99,31%); một nguồn đúng dùng text chunk thay cho gold table chunk. Không sửa gold để nâng điểm. |
| Raw model format | 17 hợp lệ / 128 lỗi escape; normalized handoff 145/145 hợp schema không đổi raw failures thành PASS. |
| Legacy lexical proxies | Giữ nguyên precision 80/178, recall 80/145, unmatched/unsupported proxy 97/178; không diễn giải các proxy này thành semantic error rates. |
| Runtime / resources | Replay chỉ đo xử lý local với recorded output. API latency, availability, native format và workload resource đầy đủ giữ NOT PASSED ở R-01/R-02. |

Mọi report phải ghi denominator, split/strata, source/config/index identity,
grouped CI khi đủ mẫu, raw/normalized provenance, missing measurements và
failures. Không cộng các cohort khác runtime thành SLO hoặc loại failed attempt
khỏi denominator. Token/chi phí provider chưa biết phải ghi unknown, không đoán.

Exit hiện hành: benchmark/review/freeze, source-reviewed output và actual app
replay, content/negative/schema/bindings/final checks/handoff đều hoàn tất trong
scope owner đã điều chỉnh. Exit live nguyên bản vẫn nằm ở R-02 trước release.
Mỗi ablation tương lai phải có hypothesis, protocol khóa trước output và không
làm xấu citation/grounding; không mở sweep chỉ vì đã đóng phase.

Bằng chứng: [freeze v5](evaluation/results/phase8-benchmark-freeze-v5.json),
[completion audit](evaluation/results/phase78-chat-quality-completion-20261013.json),
[evaluation handoff](docs/phase8_evaluation.md). Không còn câu nội dung thiếu
trong hai bộ Phase 7/8 đã chấm, nên không cần gửi lại Chat.


## 6. Kế hoạch các phase tiếp theo

Thứ tự: **Phase 9 → Phase 10 → Phase 12 → Phase 13 → Phase 14**.
Phase 11 được bỏ qua khi không cần Knowledge Graph. R-01/R-02 được xử lý trong
qualification trước public release, không bắt phần phát triển local chờ quota.
Yêu cầu viết lại roadmap này không tự khởi chạy phase hay gọi provider mới.

### Phase 9 — Temporal RAG

**Mục tiêu:** chọn đúng tài liệu theo năm/ngày/phiên bản trước khi sinh đáp án;
không dùng bản cũ, bản chưa hiệu lực hoặc bản khác chương trình để trả lời.
Kế hoạch chi tiết đã cập nhật ngày 13/10/2026; **DONE — 6/6 task, 5/5 gate PASS, 100% scope Phase 9**.
Checkpoint 14/10: đã nhận hai output repair, source review và replay đủ bộ:
**24/24 case PASS** (12/12 dev, 12/12 acceptance; 8 đáp án + 16 negative),
12/12 claim/citation có nguồn, schema 24/24. Không còn output thiếu, false
abstention hoặc scope leak. Raw gốc (21/24 public, 7/8 nội dung Chat) và lỗi
retrieval/version propagation vẫn được giữ; gold/protocol không đổi. Đây là
nghiệm thu lặp đã exposure, không phải fresh validation hay bảo đảm thống kê.
Full suite mới: **1.502 PASS, 2 live SKIP; coverage 91,05%**. Regression 68 case
Phase 7 và 300 case Phase 8 giữ nguyên public output. **T9-01–05 PASS**.
Cleanup hoàn tất: owner đã duyệt riêng ACL trên đúng hai root pytest bị khóa;
helper cùng tài khoản với quyền Administrator kiểm tra 4.779 mục mỗi thư mục,
không có reparse point, xóa cả hai và xác nhận không còn tồn tại. Không đổi
ACL đệ quy hoặc tác động ngoài dự án; helper tạm đã lưu audit rồi xóa.
[Báo cáo nghiệm thu và audit](evaluation/results/phase9-completion-20261014.json),
[review lỗi gốc](evaluation/results/phase9-chat-review-20261014.json).
[Progress và bindings](evaluation/results/phase9-progress-20261014.json),
[handoff Phase 9](docs/phase9_temporal_handoff.md).
Phụ thuộc: Phase 7/8 quality đã đóng. Không phụ thuộc quota/API cho phần phát
triển và kiểm chứng Chat; R-01/R-02 vẫn là điều kiện release riêng.

#### 9.1 Cách làm tối giản và phần tái sử dụng

Tái sử dụng `metadata_detector.py`, metadata của chunk/index,
`HybridRetriever`, `CampusAIQueryService`, `EvidenceRegistry`, grounding và hai
lớp cache hiện có. Chỉ thêm **một resolver temporal deterministic nhỏ** nếu các
component hiện tại chưa đáp ứng; không thêm LLM router, graph, vector DB, service,
framework hay migration toàn corpus. Resolve một lần mỗi request trên phạm vi
tài liệu được phép, rồi mới retrieval, evidence selection và answer generation.

Hai điểm đã thấy khi lập kế hoạch, phải tái hiện trước khi sửa:

- Detector hiện cho phép cụm `ban hành ngày` vào nhánh `effective_date`; cần tách
  ngày ban hành khỏi ngày hiệu lực, chỉ cho bằng nhau khi câu nguồn nói rõ.
- 20 câu temporal Phase 8 tập trung vào bảng đính chính 2021; không coi 20 câu
  đó là 20 family phiên bản độc lập hoặc bằng chứng đủ cho resolver đa phiên bản.

Giới hạn scope: năm/năm học rõ ràng, as-of date, bản mới nhất trong corpus đã
chọn, so sánh hai bản và xử lý thiếu/mâu thuẫn. Không xây engine pháp lý tổng
quát, tự crawl bản mới, suy quan hệ phiên bản bằng embedding hoặc sinh metadata
bằng LLM. Chỉ bổ sung nguồn khi audit chứng minh corpus thiếu cặp phiên bản cần
kiểm chứng; không mở rộng corpus theo phong trào.

#### 9.2 Contract đầu ra temporal phải chốt trước khi code

| Thành phần | Chuẩn đầu ra tối thiểu |
|---|---|
| Metadata | Giữ `issue_date`, `effective_date`, `academic_year`, `version` hiện có; bổ sung block temporal optional khi cần: family, khoảng áp dụng, độ chính xác ngày, quan hệ thay thế/sửa đổi và evidence tham chiếu. Tương thích tài liệu cũ, không bắt re-ingest toàn corpus. |
| Provenance | Mỗi giá trị temporal dùng để quyết định phải có `doc_id`, page/chunk và quote nguồn. Giá trị thiếu bằng chứng để null/unknown; filename, upload time hoặc mọi năm xuất hiện trong nội dung không phải ngày hiệu lực/năm áp dụng. |
| Request context | Intent `none / explicit_period / as_of / latest / compare`; năm hoặc khoảng ngày được chuẩn hóa, `reference_date`, timezone, selected/authorized doc scope và resolver policy version. Xung đột giữa câu hỏi, filter và history phải được giải quyết rõ trước retrieval. |
| Resolution | Status `resolved / needs_clarification / insufficient_evidence / conflict / not_applicable`, các doc/version đủ điều kiện, reason code và nguồn hỗ trợ quyết định. Compare có hai nhóm evidence riêng; status khác `resolved` không được sinh kết luận temporal chắc chắn. Query `none` đi đường cũ khi không có ambiguity về phiên bản. |
| Answer/citation | Giữ public response schema hiện có. Khi trả lời temporal, nêu năm/phiên bản/ngày đúng mức nguồn chứng minh; citation trỏ tới fact và bằng chứng áp dụng thời gian, đủ hai phía nếu so sánh. Diagnostics nội bộ không xuất ra UI; chỉ mở rộng schema khi thực sự cần và có compatibility tests. |
| Cache | Cả retrieval/answer cache phải phân biệt intent, period/as-of/reference day, doc scope, metadata generation và resolver policy. Nếu metadata nằm ngoài index, fingerprint phải bao gồm metadata đó; sửa effective date phải vô hiệu đáp án cũ. |

Quy tắc quyết định bắt buộc:

1. `issue_date` không tự thành `effective_date`; ngày chỉ có tháng/năm giữ độ
   chính xác đó, không tự điền ngày 01. Năm học 2024–2025 không tự đồng nghĩa với
   mọi câu hỏi về năm dương lịch 2024; hỏi rõ khi hai cách hiểu cho kết quả khác.
2. As-of dùng ngày được hỏi; “hiện tại” dùng ngày request theo timezone cấu hình,
   có thể inject clock trong test. Bản tương lai chưa hiệu lực không thắng bản
   đang áp dụng; không chọn theo version string, upload time hay ngày ký lớn nhất.
3. “Mới nhất” và “đang có hiệu lực” là hai intent khác nhau. Chỉ kết luận trong
   corpus/phạm vi đã chọn; không tuyên bố đây là quy định hiện hành toàn trường
   nếu không có bằng chứng đầy đủ. Không âm thầm mở scope để tìm bản khác.
4. Gom cùng family chỉ khi có identity đáng tin: trường/chương trình/loại tài
   liệu và bằng chứng version/replacement. Chưa rõ cùng family thì không tự nối.
   Bản sửa đổi một điều/học phần không tự làm hết hiệu lực cả tài liệu gốc.
5. Khoảng áp dụng có boundary xác định từ nguồn; quy ước nội bộ dùng start
   inclusive/end exclusive và kiểm tra chuyển đổi đúng câu nguồn. Thiếu end date
   không chứng minh hiệu lực vô hạn; overlap hoặc quan hệ hết hiệu lực không rõ
   phải báo conflict/insufficient evidence cho kết luận “hiện hành”.
6. Query không có intent thời gian giữ behavior cũ nếu scope chỉ có một bản phù
   hợp. Nhiều bản cùng fact khác nhau thì hỏi rõ/abstain; không lén chọn latest.
   Compare chỉ cho phép khác biệt giữa hai bản đã xác định, không tắt conflict
   guard cho mâu thuẫn trong cùng bản.

#### 9.3 Task, thứ tự thực hiện và chuẩn đầu ra

| Task | Phạm vi | Phụ thuộc | Trạng thái triển khai |
|---|---|---|---|
| P9-01 | Audit khoảng trống, nguồn và khóa protocol nhỏ | Phase 7/8 evidence | DONE — 100%; [audit](evaluation/phase9/source-audit.json), [protocol](evaluation/phase9/protocol.json), [rubric](evaluation/phase9/source-rubric.json), [24 case](evaluation/phase9/benchmark.jsonl) |
| P9-02 | Metadata thời gian có provenance | P9-01 | DONE — 100%; tách issue/effective, giữ precision/quote, cohort và năm học; metadata/compatibility/persistence controls PASS |
| P9-03 | Intent và resolver deterministic | P9-02 | DONE — 100%; 24/24 nguồn thật chọn đúng, contract tests cho boundary/future/compare/conflict/partial amendment PASS; date-positive mechanics là synthetic, không giả thành real-source quality |
| P9-04 | Tích hợp retrieval, grounding/citation và cache | P9-03 | DONE — 100%; query service, source-scope prompt, filter/auth, hai cache, clock và restart đã kiểm tra; actual model quality thuộc P9-05 |
| P9-05 | Nghiệm thu temporal và regression sản phẩm | P9-04 | DONE — 100%; 24/24 reviewed/replayed, 8 raw đáp án hợp schema, regression 68/300 giữ nguyên; final tests/coverage/local timing PASS; T9-01–04 PASS |
| P9-06 | Handoff, exit review và cleanup | P9-05 | DONE — 100%; audit/bindings, handoff, plan và cleanup đã kiểm tra; artifact catalog giữ raw/source/failure và receipt xóa tệp; T9-05 PASS |

**P9-01 — Audit và khóa protocol; không nghiên cứu lan man.**

1. Lập bảng `đã có / lỗi tái hiện / thiếu / không cần làm` cho metadata, filters,
   resolver, conflict guard, citation và hai cache; chạy chẩn đoán offline tối
   thiểu, không full benchmark/API lặp lại khi chưa có thay đổi.
2. Tìm family phiên bản thật trong corpus hiện có và chứng minh quan hệ bằng
   nguồn. Mục tiêu có ít nhất hai family, mỗi family ít nhất hai phiên bản/cập
   nhật liên quan; tách family dev và acceptance. Cùng một bảng đính chính vẫn
   là cùng nhóm nguồn, dù có nhiều câu hỏi.
3. Tái sử dụng 20 temporal cases Phase 8 làm regression. Thêm **24 case có chủ
   đích: 12 dev + 12 acceptance**, không chia paraphrase/cùng family qua split.
   Hai split đều bao phủ sáu nhóm: năm cụ thể, as-of/boundary, latest/current,
   compare, thiếu/mơ hồ và conflict/scope. Chỉ tăng tối đa 36 case nếu có lỗ hổng
   coverage được ghi trước; không đặt mục tiêu hàng trăm câu.
4. Khóa qid, intent, family/split, expected resolution, eligible/excluded
   versions, answerability, fact claims, evidence/date precision, rubric,
   thresholds và source/index/config hashes trước sửa code/thu output acceptance.

**Chuẩn đầu ra:** một gap list và coverage matrix; benchmark nhỏ đã source
review; protocol/baseline có hash, expected outcomes và danh sách case cần Chat.
Fixture tổng hợp dùng cho boundary/cache/unit tests, luôn ghi là synthetic.
**DONE khi:** mọi case có source proof hoặc lý do negative rõ, không leakage,
baseline ghi đúng lỗi hiện tại; các loại case có coverage. Nếu corpus không có
cặp phiên bản thật, ghi thiếu và chỉ bổ sung đúng cặp còn thiếu; không dùng
fixture để nhận nghiệm thu đa phiên bản thực tế hoặc đợi API vô ích.

**P9-02 — Sửa metadata và quan hệ phiên bản tối thiểu.**

1. Tái hiện và sửa nhầm ngày ký/ngày hiệu lực; phân biệt ngày áp dụng, năm học,
   năm nhắc trong nội dung và version. Giữ raw value/precision khi chưa đủ ngày.
2. Dẫn evidence cho field; nhận diện quan hệ thay thế/sửa đổi chỉ khi nguồn nêu
   rõ, giữ target và phạm vi sửa đổi. Không tự suy toàn bộ lineage từ tên file.
3. Lưu metadata bằng registry/chunk/index contract hiện có; reader hiểu cả record
   cũ và block optional mới, unknown không gây crash hoặc tự thành “latest”.
4. Kiểm tra positive/negative, ngày không hợp lệ, nhiều ngày, hiệu lực “từ ngày
   ký”, tháng/năm thiếu ngày, amendment một phần và read/restart persistence.

**Chuẩn đầu ra:** patch metadata nhỏ; metadata đã chuẩn hóa có evidence trên
các nguồn audit; tests chứng minh lỗi trước/sau và compatibility tài liệu cũ.
**DONE khi:** không còn false date/family assertion trong bộ dev/contract đã
khóa; thiếu evidence luôn unknown; không sửa corpus/gold/baseline cũ để che lỗi.
Không cần metadata hoàn hảo cho mọi PDF ngoài scope để tiếp tục task kế tiếp.

**P9-03 — Resolver thuần deterministic, dễ kiểm tra.**

1. Chuẩn hóa explicit year/academic period/as-of/latest/compare bằng rule gọn;
   năm chỉ được nhắc như dữ kiện không tự thành temporal filter. History chỉ
   dùng theo context contract; user/filter mâu thuẫn không được âm thầm override.
2. Chọn eligible versions trong selected/authorized scope trước global ranking
   và candidate truncation. Nếu applicability nằm ở clause/chunk thì áp đúng
   cấp đó; không loại cả doc gốc vì một amendment.
3. Xuất resolution contract ở 9.2 với reason/evidence; ambiguous/missing/conflict
   kết thúc trước LLM. Compare dựng hai nhóm bounded context cùng subject/fact,
   thiếu một phía thì không tự bù bằng bản năm khác hoặc kiến thức ngoài corpus.
4. Unit tests kiểm tra ngày trước/đúng/sau boundary, chưa hiệu lực, cùng ngày
   nhưng xung đột, missing/partial dates, năm học, filter conflict, cross-program,
   partial amendment và query `none`; permutation input không đổi quyết định.

**Chuẩn đầu ra:** resolver nhỏ, không network/I/O/model riêng, clock inject được;
unit tests có expected eligible/excluded IDs và reason, không chỉ assert status.
**DONE khi:** 100% contract/dev routing cases đúng, không lọt version ngoài scope,
không đoán khi thiếu evidence; không thêm LLM call hoặc retrieval pass để resolve.

**P9-04 — Gắn vào ứng dụng và khóa lỗi cache/citation.**

1. Nối resolver vào query service/filter trước retrieval; giữ API/public schema,
   authorization, exact-code và non-temporal path tương thích. Reuse evidence
   budget; compare chia budget cho hai phía, không tăng context cap tự động.
2. Grounding kiểm tra fact lẫn applicability; câu trả lời phải ghi rõ năm/bản
   và “trong tài liệu đã chọn” khi chỉ chứng minh phạm vi đó. Citation/preview
   lấy metadata hệ thống và quote gốc; không để model tự xác nhận ngày hiệu lực.
3. Đưa resolved temporal context/generation vào cả cache key. Test chuyển ngày,
   thay effective date/replacement metadata, đổi doc scope, filter, index và
   policy; answer lẫn retrieval cache không được trả phiên bản cũ.
4. Chạy actual application tests: query năm cụ thể, hiện tại, compare hai phía,
   ambiguity/unknown, scope trái phép, cache hit/miss/invalidation và lỗi provider.
   Hỏi rõ/abstain dùng schema/reason hiện có, không dựng thêm workflow UI.

**Chuẩn đầu ra:** một đường query temporal hoàn chỉnh, public response hợp schema,
trace quyết định nội bộ, integration tests và cache isolation/invalidation proof.
**DONE khi:** citation/date support và authorization đúng, query không temporal
không hồi quy; temporal safety/negative cases không cần gọi model. Không tăng
round-trip LLM; positive thường tối đa một call, compare một call nếu cần model.

**P9-05 — Nghiệm thu có nguồn, dùng Chat đúng chỗ.**

1. Chạy resolver + ứng dụng trên bộ acceptance đã khóa; lưu quyết định, evidence
   thực gửi model và raw/public output. Chấm cả đáp án đúng lẫn false abstention,
   không nhận abstain toàn bộ là PASS. Lỗi hoặc missing không loại denominator.
2. Case cần model mới xuất **một file gộp** với qid/request/prompt/evidence/schema
   thực của pipeline; không chọn lại evidence thủ công để làm đáp án dễ đúng,
   không kèm gold. Nhận nguyên raw Chat output, AI review từng claim với nguồn,
   rồi replay qua ứng dụng. Chỉ tách file nếu context/output có nguy cơ bị cắt;
   không xuất lại case đã đạt nếu payload/policy không đổi liên quan.
3. Replay 68 case Phase 7 và 300 case Phase 8 trên runtime mới bằng recorded
   output khi prompt/evidence/schema còn tương thích. Case bị thay đổi phải ghi
   rõ và chỉ kiểm chứng lại phần đó; giữ receipt/baseline cũ nguyên byte, không
   giả binding runtime mới là binding cũ. 20 temporal cũ được báo riêng, không
   cộng trùng như mẫu độc lập vào numerator/denominator mới.
4. Chạy focused tests trước, một full offline suite/coverage ở cuối khi code đã
   ổn; đo riêng resolver/local overhead với clock/profile cố định, không tải lại
   encoder hoặc thêm inference pass. Chỉ mở điều tra performance nếu có regression
   rõ; latency replay không phải latency Chat/API thật.

**Chuẩn đầu ra:** per-case review có expected/actual, accept/reject, reason,
source proof, raw/normalization provenance và runtime hashes; bảng metric tổng
và từng nhóm, regression diff và test/coverage receipt. Reviewer ghi rõ
`Codex — Automated AI Review`, không tự nhận human approval/fresh validation.
**DONE khi:** toàn bộ gate ở 9.4 đạt; không có case chưa chấm hoặc missing output.
Nếu acceptance lộ lỗi thì giữ output/failure, sửa bằng dev/generalized regression
và đánh dấu rerun đã exposure; không sửa gold hoặc tăng phiên bản packet vô nghĩa.

**P9-06 — Đóng phase, handoff và dọn đúng phần dư.**

1. Đối soát source/config/index/protocol/benchmark/raw/review/test hashes; xác
   nhận task/gate nào đạt, scope/giới hạn nào chưa có bằng chứng.
2. Viết handoff ngắn: contract/quy tắc, lệnh chạy lại không API, cách cập nhật
   metadata/version, cache invalidation, fallback và những trường hợp phải hỏi rõ.
3. Cập nhật DONE/% thực tế của từng task ngay trong Phase 9 này và kết luận exit;
   không sửa kết quả Phase 7/8 cũ hay nhận R-01/R-02 đã PASS nhờ temporal tests.
4. Xóa draft Chat đã dùng, pytest/cache/materialization không còn reference;
   giữ source/tests/config/frozen benchmark, raw failures và audit nén cần thiết.

**Chuẩn đầu ra:** completion report có gate table và bindings; handoff dùng được;
plan cập nhật; artifact catalog khớp, không có file tạm dư cần giữ vì nhầm binding.
**DONE khi:** P9-01–05 đều DONE, gate table không còn lỗi/missing, handoff và
cleanup được kiểm tra thực tế. Nếu thiếu cặp source thật/acceptance, chỉ ghi
phần đã xong và thiếu cụ thể; không nhận phase hoàn tất bằng unit fixtures.

#### 9.4 Gate nghiệm thu Phase 9

Protocol khóa ở P9-01; ngưỡng dưới đây áp dụng trên bộ acceptance nhỏ đã chốt,
không phải bảo đảm độ chính xác thống kê cho mọi trường hợp tương lai.

| Gate | Chuẩn đầu ra / điều kiện PASS |
|---|---|
| T9-01 — Nguồn và protocol | Case reviewed/frozen, đủ coverage sáu nhóm, family dev/acceptance không giao nhau; có cặp phiên bản thật và provenance, synthetic/exposure ghi riêng. Không thiếu output hoặc đổi gold sau khi xem kết quả. |
| T9-02 — Chọn phiên bản và an toàn | Resolution đúng 100% case acceptance; wrong-version, future-version, cross-program/doc-scope leak = 0. Negative/ambiguous/conflict được xử lý đúng 100%; không có false abstention trên các case đủ evidence đã khóa. |
| T9-03 — Đáp án, citation và format | Nội dung temporal đúng 100% mẫu đã kiểm tra, fact/date/version có source support; coordinate/schema ứng dụng 100%, unsupported/contradicted claims = 0. Với metric/population tương ứng vẫn giữ ngưỡng nghiêm hơn ở `grounding_release.json`; semantic source validity tách khỏi exact-gold chunk matching. Raw Chat parse/schema báo riêng, normalization không được đổi nghĩa hoặc tính là raw PASS. |
| T9-04 — Regression và runtime local | Không hồi quy các case Phase 7/8 không bị thay đổi scope; case thay đổi được review riêng có proof. Cache invalidation/isolation và clock/boundary/restart tests PASS; không thêm LLM call hoặc model load cho resolver. Có số đo local trước/sau, ghi biến động và không suy thành provider SLO. |
| T9-05 — Test, tái hiện và handoff | Required tests không fail, full offline suite/coverage ≥85%, secret/diff/bindings checks PASS; artifacts tái hiện được, handoff và cleanup xong. Hai live opt-in SKIP được công khai, không dùng làm live PASS. |

Kết quả exit 14/10/2026: **P9-01–06 DONE + T9-01–05 PASS trong scope trên**, reranker vẫn tắt,
không phát sinh chi phí. Báo cáo owner rồi mới chuyển work item sang phase khác.

#### 9.5 Giới hạn thời gian, artifact và cách tính tiến độ

- Làm tuần tự P9-01 → P9-06, một target/runtime và một protocol. Nếu task không
  phát hiện gap, ghi proof tái sử dụng rồi chuyển tiếp; không refactor cho đủ task.
- Mỗi task dùng bốn bước đã đánh số ở trên: 0/25/50/75/100% theo bước đã có
  bằng chứng. 100% chỉ khi chuẩn đầu ra/DONE của task cũng đạt. Tiến độ phase
  báo số task và gate đóng được, không gọi tỷ lệ đó là chất lượng model.
- Ưu tiên blocker chọn sai phiên bản, suy nhầm ngày, leak scope và stale cache;
  không tối ưu ranking, thêm source hay thử model khi lỗi nằm ở temporal logic.
- Không tạo ledger/framework mới. Dự kiến chỉ cần benchmark nhỏ + protocol
  dưới `evaluation/phase9/`, một completion summary trong `evaluation/results/`
  và một handoff trong `docs/`; reuse evaluator/validators hiện có, chỉ thêm helper
  mỏng khi thiếu. Đây là output dự kiến, chưa phải artifact đã tạo hoặc PASS.
- Raw/per-case outputs lớn đặt artifact store; report cuối giữ baseline và
  before/after bindings, không nhân bản history hay tạo report/approval cho mỗi
  lần chạy lại. Nếu thiếu một proof nguồn, bổ sung đúng proof đó, không mở sweep.

### Phase 10 — Multi-document và multi-hop

**Mục tiêu:** trả lời đúng câu cần kết hợp nhiều tài liệu hoặc nối hai bước
bằng chứng, giữ riêng đối tượng/chương trình/phiên bản và dẫn đủ nguồn cho kết
luận. Hoàn thiện phần còn thiếu của pipeline hiện tại, không xây hệ agent mới.

Kế hoạch cập nhật **14/10/2026**. Trạng thái: **DONE — 5/5 task DONE (100%),
5/5 gate PASS** trong scope Multi-document/multi-hop đã khóa. **24/24 case PASS**
(12 dev, 12 acceptance; 12 positive, 12 negative), không đổi gold/ngưỡng hoặc
giảm denominator. **P10-01 DONE**: đã source-review trực quan 11 trang PDF, khóa
[24 case](evaluation/phase10/benchmark.jsonl), [rubric](evaluation/phase10/source-rubric.json)
và [protocol](evaluation/phase10/protocol.json) trước thay đổi runtime.
Dev dùng nguồn Cơ điện tử/Robot, acceptance dùng hai chuyên ngành thạc sĩ Điện
tử/Viễn thông; nhóm nguồn và chain không giao nhau, tất cả đã exposure.
[Source audit](evaluation/phase10/source-audit.json) giữ baseline/hashes:
24 request thực, 20 boundary model được capture, 4 local branches; 8 negative
vẫn đi tới model là gap đã sửa. **Baseline ban đầu chưa có output model nên quality chưa đo**,
không tính lỗi capture local là Gemini trả lời sai. Probe false-edge được giữ;
scope audit được tinh chỉnh để không cấm phép cộng liên nguồn hợp lệ.
Đã tích hợp request/source roles, retrieval tối đa hai bước, edge/row proof,
scope-aware arithmetic và cache vào ứng dụng. **Full offline suite cuối: 1.550 PASS,
0 FAIL / 2 live SKIP, coverage 91,09%**. Nghiệm thu bằng raw Chat, source review
và actual replay: **12/12 positive đúng đầy đủ; 4 phép tính local đúng; 12/12
negative xử lý đúng trước model**. 32 claim và 24 citation công khai đã kiểm chứng;
false join/scope leak/unsupported/contradicted leakage/false abstention đều bằng 0.
Tám output Chat thô đều lỗi escape chuỗi quote: **raw parse 0/8 PASS**; chuẩn hóa
16 quote và dòng phân cách thuần cú pháp cho **8/8 schema PASS, 0 sửa nghĩa**.
Không nhận normalized output là raw format PASS. Replay đầu 22/24 phát hiện
guard tên→mã từ chối sai mã có khoảng trắng; đã sửa bằng generalized fixtures,
giữ failure và payload, replay cuối đạt 24/24. Một test quota phụ thuộc giờ reset
đã được cố định clock trong test; guard sản phẩm không đổi, full-suite cuối đạt.
Hồi quy actual payload/public outputs giữ nguyên Phase 7 **68/68**, Phase 8
**300/300**, Phase 9 **24/24**. Các lần hồi quy lỗi được giữ; đã sửa ảnh hưởng
ranking ngoài luồng nối mới và giữ prompt cũ khi native comparison đã đủ nguồn.
Đo local cùng profile đã lưu, gồm chi phí thêm retrieval cho dependent hop;
không coi một lượt đo là API/Chat latency hoặc cam kết hiệu năng thống kê.
[Packet Chat](evaluation/phase10/gemini-chat-packet.md) có đúng 8 case, không gold,
không API/phí; payload giữ nguyên sau kiểm tra tương thích runtime cuối.
[Completion/evidence](evaluation/results/phase10-completion-20261014.json),
[progress](evaluation/results/phase10-progress-20261014.json) và
[handoff](docs/phase10_multi_hop_handoff.md) lưu kết quả, lệnh tái hiện và limitations.
Raw Phase 9 owner gửi trước đây được giữ riêng; raw Phase 10 đã nhận đủ 8 qid.
Runner nhận Chat đã có **8 input/provenance controls PASS**: giữ nguyên raw theo
SHA và từ chối sai/trùng qid, thiếu case hoặc sai schema trước khi load index/model.
Đây là kiểm tra kỹ thuật đầu vào, không cộng vào 24 case quality hoặc full-suite count.
Đã dọn thư mục test tạm sau kiểm tra, archive/restore có SHA, giữ baseline,
raw failures và snapshot roadmap lúc exit. Phụ thuộc:
Phase 7/8 quality và Phase 9 đã DONE trong scope đã chốt; R-01/R-02 về API thật
vẫn NOT PASSED, không phải việc phải chờ để phát triển/nghiệm thu Chat Phase 10.

#### 10.1 Phạm vi gọn và phần tái sử dụng

Tái sử dụng `CampusAIQueryService`, `HybridRetriever`/RRF, metadata và resolver
Phase 9, `EvidenceRegistry`, `align_claims`, `credit_sum.py`, conflict guard,
context/history, citation validator và cache hiện có. Cộng/trừ tín chỉ, claim có
nhiều citation và so sánh phiên bản đã có code/tests; audit trước, chỉ sửa khi
có lỗi tái hiện hoặc thiếu chuẩn đầu ra. Không viết lại để đủ task.

Trong scope:

- **Multi-document:** đối chiếu cùng fact hoặc tổng hợp các fact đã yêu cầu từ
  hai nguồn rõ ràng; khác chương trình/năm được giữ thành hai phía có nhãn.
- **Multi-hop thật:** hop 1 chứng minh khóa nối/quan hệ, hop 2 cung cấp fact của
  đối tượng đã xác định. Ví dụ: tìm mã môn tiên quyết rồi tra tín chỉ đúng môn
  trong tài liệu phù hợp. Hai câu độc lập ghép lại không được nhận là chain.
- **Tính toán nhỏ:** tổng/chênh lệch từ các ô tín chỉ có heading và scope rõ;
  reuse phép tính deterministic, không giao phép tính quyết định cho model.
- **An toàn:** thiếu hop/khóa nối, trùng mã khác chương trình, khác phiên bản,
  mâu thuẫn, tài liệu ngoài quyền, context nhiễu và cache cũ.

Giới hạn sản phẩm cho phase: tối đa **2 hop, 2 nhóm nguồn bắt buộc** mỗi câu.
Mỗi nhóm được có fact chunk và provenance phụ trợ; không đồng nghĩa chỉ được
hai chunk. Tổng tín chỉ trực tiếp đã hỗ trợ nhiều mã vẫn giữ behavior cũ, không
cắt xuống hai mã. Yêu cầu vượt phạm vi nối mới phải hỏi rõ/abstain, không âm thầm
bỏ bớt điều kiện. Không graph, LLM planner, agent loop, vector DB mới, reranker,
fine-tune, crawl rộng, migration corpus hoặc UI mới. Không bật billing/gọi API
để nghiệm thu; dùng Gemini Chat theo workflow đã thống nhất.

#### 10.2 Contract và budget phải khóa trước sửa code

| Thành phần | Chuẩn đầu ra bắt buộc |
|---|---|
| Hiểu yêu cầu | Phân biệt `single / compare / aggregate / join_two_hop`; giữ raw question và điều kiện entity, program, version/period, doc scope, operand order, history/selected text. Nếu không phân giải được thì hỏi rõ; không thêm LLM phân loại. Chỉ thêm cấu trúc nội bộ nhỏ nếu code hiện có thiếu. |
| Identity/khóa nối | Dùng mã/ID và quan hệ có quote nguồn, cùng scope đã chứng minh. Tên gần giống, cùng số, cùng trường hoặc cùng course code ở hai chương trình không đủ để nối. Alias chỉ chuẩn hóa bằng rule/metadata có kiểm chứng; lưu giá trị gốc. |
| Evidence từng hop | Mỗi premise có role/hop, entity key, `doc_id`, chunk, page/range và row/column nếu là bảng; chỉ nhận trong selected/authorized scope. Lưu khóa nối và nguồn chứng minh edge, không chỉ hai endpoint. Diagnostics nội bộ, không đổi public schema. |
| Temporal | Phase 9 chọn đúng phiên bản trước ranking/join. Hai phía compare có nhãn riêng; hop phụ thuộc phải dùng phiên bản tương thích theo nguồn. Không tự nối bản mới với bản cũ hoặc suy ngày hiệu lực từ năm trên bìa. |
| Retrieval | Mặc định một pass trên scope hợp lệ, chia bounded candidates/context cho các premise. Chỉ cho phép pass thứ hai khi khóa nối lấy được từ hop 1 và còn thiếu hop 2; không loop/retry retrieval tự động. Trần hai lượt search, mỗi lượt tối đa 20 candidates, tổng tối đa 40 và không vượt cap đang cấu hình; encoder tối đa tương ứng hai query, không model load mới cho planner. |
| Context/token | Reuse giới hạn context đang cấu hình; không tăng `max_context_chars`, token hoặc output cap để che lỗi thiếu evidence. Ưu tiên đủ fact/edge/provenance cho hai phía trước chunk phụ; bị cắt mất premise bắt buộc thì abstain. Một model generation tối đa/câu; deterministic arithmetic và negatives tối đa 0 call khi đủ phân loại local. |
| Claim/kết luận | Claim nguyên tử gắn đúng nguồn; kết luận nối phải có đủ premise và edge. Không dùng lexical overlap hoặc numeric overlap chung để hợp thức hóa phép nối. Tất cả điều kiện bắt buộc của câu hỏi phải được trả lời; không coi phần trả lời một phía là thành công toàn câu. |
| Phép tính | Operand = entity + chương trình/phiên bản + ô giá trị + đơn vị + citation. Giữ thứ tự A−B, dấu âm và 0; không nhầm giờ học thành tín chỉ, không cộng trùng một môn do nhiều chunk/alias/bản sao. Cùng mã ở hai nguồn chỉ là hai operand khi câu hỏi xác định rõ hai scope. |
| Conflict | Khác số liệu giữa hai phía compare có scope rõ được trình bày như khác biệt. Mâu thuẫn trong cùng phía, khóa nối không duy nhất hoặc thiếu một premise phải hỏi rõ/abstain; không tắt conflict guard cho mọi câu nhiều tài liệu. |
| Cache/context | Reuse key hiện có, thêm dependency còn thiếu nếu audit chứng minh cần: intent, hop/role/operand order, selected/authorized scope, temporal fingerprint và generation của mọi nguồn liên quan. History/assistant output/selected text không thành bằng chứng hoặc quyền truy cập. Đổi một nguồn phải vô hiệu kết quả ghép cũ. |

#### 10.3 Benchmark nhỏ, nguồn thật và chuẩn nghiệm thu

P10-01 khóa **24 case: 12 dev + 12 acceptance**, chia theo family/nhóm nguồn,
không chia paraphrase/cùng chain qua hai split. Mỗi split gồm 6 positive và
6 negative. Reuse nguồn/case cũ khi phù hợp và ghi exposure; không gọi là fresh.

| Nhóm | Dev | Acceptance | Bằng chứng cần kiểm tra |
|---|---|---|---|
| Compare/tổng hợp hai nguồn | 2 positive | 2 positive | Đủ hai phía, nhãn scope và citation riêng; có giá trị bằng nhau và khác nhau nếu nguồn thật cho phép. |
| Tổng/chênh lệch từ hai nguồn | 2 positive | 2 positive | Đúng ô, đơn vị, toán hạng và phép tính; không dùng model làm calculator. |
| Nối hai hop có quan hệ thật | 2 positive | 2 positive | Hop 1 chứng minh edge/khóa nối, hop 2 đúng entity và scope; không chỉ hai fact đặt cạnh nhau. |
| Khóa nối sai/không duy nhất | 2 negative | 2 negative | Trùng mã khác scope hoặc hai endpoint không có quan hệ được chứng minh; không false join. |
| Thiếu hop/mâu thuẫn | 2 negative | 2 negative | Chỉ có một phía, thiếu ô/đơn vị, hoặc mâu thuẫn cùng phía; phải chặn kết luận đầy đủ. |
| Scope/time/context | 2 negative | 2 negative | Nguồn ngoài selected/authorized scope, phiên bản không phù hợp hoặc history gây nhầm đối tượng. |

Sáu nhóm trên là denominator quality. Cache/budget/permutation/truncation và
fault/restart được kiểm tra bằng contract/integration tests riêng, không cộng
fixture tổng hợp vào numerator nguồn thật. Có ít nhất hai family dev/acceptance
không giao nhau, mỗi family đủ nguồn cho chain hai hop thật; nếu audit chưa có,
ghi gap và chỉ bổ sung nguồn công khai chính thức tối thiểu. Không tạo đáp án,
edge hoặc nhãn nguồn giả để lấp ma trận. Chỉ tăng tối đa 32 case khi có lỗ hổng
coverage được ghi trước khi xem output acceptance; không mở sweep lớn.

Khóa qid/question/request, split, required hops/edge/entity keys, eligible và
excluded docs/versions, answerability, phép tính/claim, source quotes/coordinates,
rubric, thresholds và source/index/config/runtime hashes trước triển khai.
Nếu case đã exposure, lưu cả output/failure cũ; không sửa gold, bớt denominator
hoặc nới ngưỡng sau khi xem kết quả. Reviewer là **Codex — Automated AI Review**,
không giả chữ ký/phê duyệt con người.

#### 10.4 Task, thứ tự và chuẩn đầu ra

| Task | Phạm vi | Phụ thuộc | Trạng thái |
|---|---|---|---|
| P10-01 | Audit, baseline và khóa protocol/benchmark | Phase 7–9 evidence | DONE — 100%; source/PDF review, 24-case freeze và actual baseline/snapshot đã kiểm tra; baseline model quality chưa đo, không giả thành baseline accuracy |
| P10-02 | Evidence từng hop, scope và retrieval/cache có budget | P10-01 | DONE — 100%; actual 24-case source/budget audit và cache/scope/edge controls PASS |
| P10-03 | Ghép đáp án, phép tính và kiểm chứng đủ chain | P10-02 | DONE — 100%; 12/12 positive, 12/12 negative, 32 claim/24 citation đã source-review; phép tính và chain đúng |
| P10-04 | Nghiệm thu nguồn thật và regression sản phẩm | P10-03 | DONE — 100%; actual replay 24/24, regression 68/300/24 exact-compatible, counters/local before-after và final tests có proof |
| P10-05 | Exit review, handoff và cleanup | P10-04 | DONE — 100%; requirement audit, completion/handoff/snapshot, secret/diff/bindings/restore và cleanup verified |

**P10-01 — Audit trước, chỉ sửa gap có bằng chứng.**

1. Kiểm kê `đã có / lỗi tái hiện / thiếu / ngoài scope` cho retrieval đa nguồn,
   tổng/chênh lệch, composition, citation, scope/time, history và cache. Reuse
   tests/baseline hiện có; không bắt đầu bằng refactor hoặc gọi model.
2. Chọn nguồn thật và chứng minh edge/identity cho mỗi chain; kiểm tra độ đủ của
   cả hop và các nguồn gần giống dễ nhầm. Tách family dev/acceptance theo 10.3.
3. Source-review và khóa 24 case/rubric/coverage/hashes/budget; đánh dấu exposure,
   synthetic controls và các case cần Chat. Không đưa gold vào request runtime.
4. Chạy baseline bằng ứng dụng hiện tại: lưu retrieval/hop/edge/claim/public
   schema và lỗi thực tế. Chỗ chưa có raw model output chỉ ghi chưa đo, không
   dùng synthetic model response để nhận quality.

**Chuẩn đầu ra:** gap list có case tái hiện, source/edge map, benchmark/rubric và
protocol frozen, baseline có hashes và danh sách kiểm chứng còn thiếu.
**DONE khi:** mọi case có proof hoặc negative rationale, split không leakage,
đủ chain thật và budget chốt; biết chính xác component nào cần sửa. Component
đã đạt được reuse có proof; không triển khai lại.

**P10-02 — Giữ đủ evidence cho từng hop trong scope.**

1. Reuse request/context và resolver Phase 9 để phân giải điều kiện/entity/time;
   dựng hop requirements nội bộ nhỏ, chỉ hỗ trợ các dạng đã chốt ở 10.1–10.2.
2. Lọc selected/authorized docs trước retrieval. Một pass và phân bổ context cho
   từng role là mặc định; dependent hop được tối đa một pass bổ sung bằng khóa
   nối đã chứng minh. Không mở scope để tìm bản đối chiếu còn thiếu.
3. Giữ mapping fact/edge/row/column/provenance, dedup đúng entity và ô nguồn;
   bảo đảm không mất hop vì top-k, program-title ranking hoặc context truncation.
   Khóa budget toàn câu, không nhân đôi context/token cap cho mỗi subquery.
4. Bind dependency của hai phía vào cache; test đổi nguồn/metadata/period,
   hoán đổi operand order, doc/filter/quyền, history/selected text, restart và
   các tình huống thiếu một hop. Trace số search/encoder/model call thực tế.

**Chuẩn đầu ra:** evidence plan/set nội bộ có roles và source proof, trace scope
và budget; tests cho source isolation, cache invalidation và đủ hai phía.
**DONE khi:** routing/evidence requirements đúng 100% dev/contract cases, leak=0,
không vượt hai search và cap context hiện có; thiếu hop không tới generation.
Chưa nhận chất lượng đáp án model chỉ từ retrieval recall.

**P10-03 — Kiểm chứng chain và phép tính trước khi xuất đáp án.**

1. Reuse claim/citation registry; kiểm tra premise riêng và edge nối entity.
   Giới hạn suy luận ở quan hệ/lookup/compare đã định nghĩa; không suy quan hệ
   chỉ từ hai đoạn cùng nhắc mã/tên, không nối qua assistant history.
2. Reuse deterministic sum/difference và headed credit rows; sửa đúng gap về
   scope/operand nếu baseline tìm thấy. Kiểm tra âm/0, mã cách nhau, alias/bản sao,
   cùng mã khác chương trình, ô giờ học và unit thiếu. Giữ behavior cũ ngoài gap.
3. Với câu cần diễn đạt, một LLM call trên context thật của ứng dụng; câu trả lời
   nêu rõ từng phía và conclusion có đủ premise/citation. Giữ public schema,
   không thêm prompt planner hoặc tự tăng output cap.
4. Tests chặn false join, sai toán hạng/thứ tự, citation thiếu phía, premise bị
   cắt, contradiction cùng phía và instruction injection trong evidence/context;
   positive đủ nguồn phải trả lời, không nhận abstain mọi câu là PASS.

**Chuẩn đầu ra:** claim-to-premise/edge support, phép tính tái hiện từ ô nguồn,
public response hợp schema, focused before/after tests và trace một call/0 call.
**DONE khi:** dev/contract đúng 100%, unsupported/contradicted output=0, không
false abstention trên positive đã chốt; một nguồn đúng không che hop sai/thiếu.

**P10-04 — Nghiệm thu nhỏ, không đợi API.**

1. Chạy toàn bộ 24 case bằng pipeline thật; lưu requests, evidence/hops/edge,
   raw/public outputs, schemas và counters. Local negatives/calculation chấm
   trực tiếp; các case cần model được capture ở boundary generation.
2. Xuất một packet Chat gộp chỉ những case chưa có output tương thích, gồm
   prompt/evidence/schema thực, không có gold/expected hops. Chỉ chia packet
   khi có nguy cơ vượt context/output, không hỏi từng câu. Nhận nguyên raw;
   source-review từng claim/edge/operand rồi replay qua ứng dụng hiện tại.
3. Đối chiếu before/after trên bộ đã khóa; báo dev/acceptance và sáu nhóm riêng.
   Replay regression Phase 7 (68), Phase 8 (300), Phase 9 (24), không cộng các
   bộ cũ vào denominator mới. Chỉ carry review cũ khi payload/source còn tương
   thích; phần thay đổi cần review riêng và Chat lại đúng phần đó.
4. Chạy focused tests, rồi full offline suite/coverage cuối khi runtime ổn;
   đo local trước/sau cùng profile, ghi counters và biến động. Chỉ điều tra khi
   có hồi quy rõ; replay không phải latency Chat/API. Sau lỗi acceptance, giữ
   failure, sửa bằng dev/generalized fixture và rerun phần bị ảnh hưởng có exposure.

**Chuẩn đầu ra:** review từng case gồm expected/actual, accept/reject/reason,
source proof, raw/normalization provenance, request/runtime/index bindings;
metric đủ mẫu, regression diff và test/coverage/local timing receipt.
**DONE khi:** T10-01–04 PASS, không thiếu output, không case chưa chấm; mọi case
đạt cả semantic support và actual public replay. Không chỉnh nhãn để làm xanh.

**P10-05 — Đóng phase với hồ sơ gọn, dùng lại được.**

1. Audit từng chuẩn đầu ra/gate với source/config/index/raw/review/test hashes;
   phân biệt real-source quality, synthetic mechanics và giới hạn mẫu đã exposure.
2. Viết handoff ngắn: supported requests, hop/edge/scope rules, budgets, cách
   cập nhật nguồn/cache, fallback và lệnh replay zero-network không ghi đè receipt.
3. Cập nhật task/% và gate trong `plan.md` theo evidence; giữ Phase 0–14 và
   kết quả Phase 7–9. Không đổi R-01/R-02 thành PASS hoặc tự chuyển phase khác.
4. Sau kiểm tra references/bindings, archive raw cần audit và dọn temp/draft/cache
   không còn dùng. Giữ source/config/tests/frozen inputs, baseline và raw failures;
   bản roadmap ở thời điểm nghiệm thu phải có snapshot, tránh bind vĩnh viễn
   báo cáo lịch sử vào một `plan.md` còn được cập nhật.

**Chuẩn đầu ra:** một completion summary có task/gate table và artifact bindings,
handoff, roadmap cập nhật và cleanup receipt. Không tạo report cho mỗi retry.
**DONE khi:** P10-01–04 DONE, T10-01–05 PASS, handoff/cleanup verified; chỉ lúc đó
đóng Phase 10/goal và báo owner. Thiếu proof/Chat output phải ghi đúng phần thiếu.

#### 10.5 Gate nghiệm thu và cách tính tiến độ

Các ngưỡng khóa ở P10-01 trên bộ nhỏ 24 case; 100% ở đây là kết quả bộ đã chốt,
không phải cam kết độ chính xác thống kê trên mọi câu hỏi tương lai. Với metric
và population tương ứng, giữ ngưỡng nghiêm hơn của `grounding_release.json`.

| Gate | Điều kiện PASS / chuẩn đầu ra |
|---|---|
| T10-01 — Protocol và nguồn | Đủ 24 case/6 nhóm, hai split tách family, có chain hai hop thật với edge proof; nguồn/hashes/rubric/ngưỡng frozen, exposure rõ. Không thiếu output hoặc sửa gold sau acceptance. |
| T10-02 — Scope, hop và budget | 100% required premise/edge chọn đúng trên bộ đã chốt; wrong entity/version, false join và unauthorized/doc-scope leak=0. Thiếu/mơ hồ/conflict xử lý đúng; không vượt hai search, context cap và một generation/câu; kiểm tra cache/historical context PASS. |
| T10-03 — Đáp án, phép tính, citation | 12/12 positive đúng đầy đủ, 12/12 negative xử lý đúng; supported claims, required-edge/operand coverage và source-coordinate validity 100%; unsupported/contradicted leakage=0, false abstention=0, public schema 100%. Raw Chat parse/schema và mọi normalization báo riêng; normalization không được đổi nghĩa hoặc được tính là raw PASS. |
| T10-04 — Regression/local runtime | Phase 7/8/9 không hồi quy ngoài behavior thay đổi có source review rõ; actual prompt/schema compatibility có proof. Counter/fault/cache/restart controls PASS, không model planner/load mới; có local before/after cùng profile, không nhận là live provider SLO. |
| T10-05 — Tests, tái hiện và exit | Required tests không fail; full offline coverage ≥85%; live opt-in SKIP công khai. Secret/diff/bindings/artifact restore checks PASS, handoff đủ dùng, cleanup xong, task/gate và limitations phản ánh đúng bằng chứng. |

Exit: **P10-01–05 DONE + T10-01–05 PASS**, reranker OFF, không phí API và
không mở rộng framework/corpus ngoài gap nguồn tối thiểu đã chứng minh.

Trạng thái gate hiện tại: **T10-01, T10-02, T10-03, T10-04, T10-05 PASS**.
Protocol/source/output đủ; source review và actual replay 24/24; contract/cache/
history/budget controls và hồi quy exact-compatible đạt; full offline suite,
coverage, exit/handoff/cleanup có bằng chứng trong completion report.
Đây là nghiệm thu nhỏ đã exposure qua owner-mediated Chat, không phải fresh
validation, chữ ký con người hay qualification API thật. **R-01/R-02 NOT PASSED**.

Thứ tự thực hiện: **P10-01 → P10-02 → P10-03 → P10-04 → P10-05**.
Mỗi task có bốn bước: 0/25/50/75/100% theo bước hoàn tất có proof; 100% chỉ khi
đạt chuẩn đầu ra/DONE. Báo tiến độ phase bằng task/gate đã đóng, tách khỏi quality.
Audit và sửa dev trước khi xin output Chat; giữ một protocol và một target runtime,
chỉ xuất lại payload thay đổi. Không full-suite/benchmark sweep lặp lại vô ích.
Không đặt hạn hoàn thành giả trước audit; sau P10-01 báo remaining work theo gap
thực và phần cần owner gửi Chat, không dùng thời gian chờ làm lý do nới gate.

Hồ sơ dự kiến: frozen benchmark/protocol/rubric nhỏ tại `evaluation/phase10/`,
một completion summary tại `evaluation/results/`, một handoff tại `docs/`;
reuse evaluator/artifact store. Raw lớn để artifact store có catalog/hashes,
không commit model weights, index hay nhật ký prompt/output dài vào Git.

### Phase 11 — Knowledge Graph

**Mục tiêu:** truy xuất quan hệ học phần nhanh, đúng scope và có thể lần ngược
đến bằng chứng gốc. Tái sử dụng core Phase 9/10, giữ một sidecar SQLite nhỏ.

Trạng thái **DONE — 5/5 task (100%), 5/5 gate PASS** ngày 14/10/2026.
[Frozen protocol](evaluation/phase11/protocol.json) giữ 16 case (8 dev/8 acceptance),
nguồn/rubric/ngưỡng trước prototype. Nhánh **QUALITY** đã chứng minh sửa hai lỗi
local dev khác chain (`p11-dev-02`, `p11-dev-04`); baseline thiếu model output
ở bốn câu khác vẫn UNMEASURED, không được tính là model trả sai.

Candidate qua WSGI/service thật đạt **16/16: 8 positive/8 negative**, 18 claim và
15 citation có nguồn; 15 answer schemas và 1 authorization HTTP400 error contract
hợp lệ. Cả bộ dùng **0 generation/search/encoder/provider call**. Index audit
249 node/72 cạnh đủ điều kiện, extraction precision/recall100%; unsupported/
conflicting/missing-endpoint relations được báo riêng. SQLite610.304 byte,
manifest1.611 byte, dưới cap2.380.584 byte; không có dependency/service graph mới.

Hồi quy thực Phase7/8/9/10 đạt **68/300/24/24**, exact actual prompt/schema/source
và public outputs khớp các bản đã source-review. Full offline suite **1.582 PASS,
2 live SKIP, coverage90,99%**. Feature opt-in qua `relation_index`, mặc định OFF;
profile web/MVP hiện có không phụ thuộc sidecar. Không gọi API hoặc phát sinh phí.
Local timing/RSS không phải API SLO; R-01/R-02 vẫn NOT PASSED.

[Completion/evidence](evaluation/results/phase11-completion-20261014.json) giữ
20 bước audit, gates, các raw/failure/hash binding và roadmap snapshot tại exit.
[Handoff/rollback/replay](docs/phase11_relation_index_handoff.md) mô tả bật/tắt,
build/rebuild, scope, budgets và giới hạn. Bằng chứng lớn được nén đúng byte vào
artifact store; đã kiểm tra restore, secret/diff và xóa 12 thư mục test tạm.
Phase0–10 và12–14, các kết quả lịch sử và gold giữ nguyên.

#### 11.1 Phương án tối ưu và giới hạn

Chọn **relation index deterministic**, không dựng một hệ GraphRAG riêng.
Ưu tiên một sidecar SQLite qua `sqlite3` sẵn có, kèm manifest nhỏ; chỉ chọn
format khác nếu P11-01 chứng minh SQLite không đáp ứng. Không duy trì đồng thời
nhiều backend. Chỉ mục là dữ liệu dẫn đường tới chunk/row gốc, không phải nguồn
sự thật độc lập hoặc gold benchmark.

Tái sử dụng `course_code_key`, headed table rows, `Premise`/edge proof trong
`multi_hop_evidence.py`, `plan_request`, resolver temporal, `CampusAIQueryService`,
`HybridRetriever`, `EvidenceRegistry`, `align_claims`, arithmetic và cache.
Không viết lại parser, embedding, bộ sinh đáp án hay citation validator.

Trong scope nếu có quyết định GO:

- Học phần trong đúng tài liệu/chương trình/phiên bản; tên và mã có bằng chứng.
- Quan hệ **tiên quyết trực tiếp** từ cột hoặc phát biểu nguồn rõ ràng. Chọn một
  hướng lưu canonical, ví dụ `môn phụ thuộc → môn tiên quyết`; truy vấn chiều
  ngược chỉ dùng index đảo, không đảo nghĩa quan hệ trong đáp án.
- Tra quan hệ trực tiếp/chiều ngược và chain tối đa hai bước. Hai cạnh trực tiếp
  tạo một đường đi hai bước, không biến thành một cạnh tiên quyết trực tiếp mới.
- Tín chỉ là fact có ô nguồn; cộng/trừ tiếp tục chạy deterministic. Tên→mã là
  lookup đã chứng minh, không phải xác nhận hai chương trình tương đương.

Ngoài scope: Neo4j/network service, graph framework, LLM extraction/planner,
entity embedding mới, community detection, graph visualization/UI, recommendation
lộ trình học, crawl/migration corpus, hơn hai hop, nhận diện tương đương tự động,
diễn giải prerequisite nhiều mã/AND/OR hoặc điều kiện văn bản chưa có contract.
Reranker OFF; không tự gọi API, đổi key/model, bật billing hoặc phát sinh phí.

| Contract | Chuẩn đầu ra bắt buộc |
|---|---|
| Entity identity | Khóa theo `doc_id/source_hash + program/version scope + canonical course_code`; giữ giá trị gốc. Nếu program/version chưa xác lập, giữ identity riêng theo tài liệu, không đoán hoặc gộp theo tên/mã giống nhau. |
| Edge/fact proof | Mỗi cạnh/fact có relation type/direction, entity endpoints, source hash, chunk, physical page/range, heading và row/column/cell nếu là bảng. Thiếu heading/provenance hoặc endpoint chưa xác minh thì không publish cạnh sử dụng được. |
| Alias/conflict | Chỉ chuẩn hóa khoảng trắng mã, đoạn song ngữ/footnote đã có rule. Không fuzzy merge. Duplicate cùng proof được dedup; khác giá trị hoặc quan hệ cùng scope giữ conflict và chặn kết luận, không lấy cạnh đầu tiên. |
| Scope/time | Lọc selected/authorized docs và resolver thời gian trước lookup/traversal. Không đi qua nguồn ngoài quyền rồi mới lọc kết quả; không dùng năm tên file làm ngày hiệu lực. |
| Query budget | Tối đa 2 hop, 2 nhóm nguồn, 2 adjacency lookup; tối đa 40 node/40 edge xét cho một request. Kiểm tra fan-out/count trước khi đọc danh sách vượt cap; vượt giới hạn phải báo không đủ phạm vi, không trả danh sách cắt như kết quả đầy đủ. |
| Shared retrieval budget | Graph candidates và fallback chia chung cap tối đa 40 evidence candidates, mỗi search tối đa 20; tối đa 2 search và 2 encoder query toàn câu. Truy vấn chunk theo ID phải được trace; không ẩn full-index scan, retry hoặc tăng cap sau fallback. |
| Grounding/context | Fetch và kiểm chứng lại chunk/row thật trước trả lời; không tạo quote từ bản tóm tắt cạnh. Giữ context cap 12.000 ký tự của profile nghiệm thu và token/output cap hiện có; tối đa 1 generation/câu, local relation/arithmetic/negative dùng 0 khi đủ xử lý deterministic. |
| Lifecycle/cache | Graph là derived artifact, có source/index/extractor/schema/policy fingerprint và trạng thái ready. Build idempotent/atomic, không phục vụ bản ghi một phần. Update/delete nguồn làm mất hiệu lực cạnh và answer cache; manifest cũ/corrupt không được dùng âm thầm. |
| Fallback | Chỉ dùng đường Phase 10 khi intent được hỗ trợ và còn budget; graph off/missing không làm hỏng đường hiện có. Nếu nguồn thật thiếu/mâu thuẫn hoặc hết budget thì clarify/abstain; fallback không được bỏ điều kiện để trả lời một phần. |

#### 11.2 Bộ nghiệm thu nhỏ và quyết định giá trị

P11-01 khóa **16 case nguồn thật: 8 dev + 8 acceptance**, mỗi split 4 positive
và 4 negative; tách family/nhóm nguồn/chain, không chia paraphrase qua hai split.
Reuse corpus đã có, giới hạn pilot tối đa bốn tài liệu thuộc hai family. Không
đọc đáp án benchmark để build index. Mỗi case phải có source review, đáp án/
answerability, direction/path/edge, eligible/excluded scope và coordinates.

| Nhóm | Dev | Acceptance | Chuẩn đầu ra |
|---|---|---|---|
| Quan hệ trực tiếp và truy vấn chiều ngược | 2 positive | 2 positive | Đúng hướng, đủ kết quả được hỏi trong cap, mỗi cạnh có proof riêng; không suy cạnh từ hai endpoint cùng xuất hiện. |
| Chain hai bước và fact cuối chain | 2 positive | 2 positive | Đủ hai cạnh/premise, đúng entity cuối; không gọi quan hệ gián tiếp là tiên quyết trực tiếp. |
| Identity/scope/phiên bản sai | 2 negative | 2 negative | Không gộp trùng mã khác chương trình, leak nguồn ngoài quyền hoặc trộn phiên bản. |
| Thiếu cạnh/mơ hồ/mâu thuẫn | 2 negative | 2 negative | Chặn kết luận thiếu proof; không coi ô trống/OR/nhiều mã hoặc cạnh không duy nhất là cạnh hợp lệ. |

Fault/cycle/fan-out, reordered input, budget, cache, update/delete, corrupt index,
build failure và restart là controls riêng, không cộng fixture synthetic vào
16 case quality. Nếu nguồn thật không đủ matrix thì ghi gap, không bịa cạnh;
chỉ bổ sung nguồn chính thức tối thiểu khi chứng minh cần. Chỉ tăng tối đa 24
case nếu coverage gap được ghi trước freeze, không mở sweep lớn.

Khóa một protocol, qid/request, rubric/gold, hashes và ngưỡng **trước prototype**.
Baseline có graph OFF, candidate có graph ON, cùng source/config/profile; raw
output chưa có phải ghi UNMEASURED. Lịch sử exposure và lỗi phải giữ nguyên;
không sửa gold/denominator/ngưỡng sau khi nhìn acceptance.

**GO sơ bộ sau audit:** có ít nhất hai lỗi dev khác chain tái hiện thuộc quan hệ
trong scope, hoặc có ít nhất bốn câu positive cần lookup quan hệ để kiểm tra giả
thuyết giảm chi phí. Giả thuyết không được tính là lợi ích đã đạt.

**Chỉ giữ implementation sau P11-04 nếu quality không giảm và đạt ít nhất một
nhánh lợi ích đã chọn trước:**

- **Nhánh chất lượng:** sửa được ít nhất hai case dev khác chain mà baseline
  sai/không trả lời dù đủ nguồn; candidate đạt đủ acceptance và regression.
- **Nhánh chi phí:** trên cohort quan hệ đã khóa, giảm ít nhất 25% tổng
  search/encoder calls so với baseline và giảm ít nhất 20% p95 local retrieval
  + proof. Đo xen kẽ OFF/ON, cùng device/thread/cache profile, ít nhất năm lượt
  cho tám positive (40 quan sát mỗi arm); tách build/cold load và lỗi khỏi
  warm timing nhưng vẫn báo đầy đủ lỗi. Đây là phép đo local, không phải API SLO.

Sidecar pilot không vượt `max(1 MiB, 10% dung lượng BM25+dense của cùng nguồn)`;
báo build time, disk, cold/warm/RSS và fallback rate. Không đạt chất lượng/lợi
ích hoặc tăng độ phức tạp không tương xứng thì kết luận **NO-GO/DEFERRED**,
giữ core hiện có, gỡ prototype và chuyển ưu tiên sang MVP. Đây là quyết định
dừng hợp lệ, **không được ghi graph đã DONE/PASS 100%**. Chỉ một prototype và
một vòng chỉnh theo dev trước acceptance; không đổi stack hay thử vô hạn.

#### 11.3 Task tuần tự và chuẩn đầu ra

| Task | Công việc | Phụ thuộc | Trạng thái |
|---|---|---|---|
| P11-01 | Audit nhu cầu, source proof, baseline và khóa protocol | Phase 9/10 evidence | DONE — 100%; source review/freeze16, actual baseline và GO nhánh chất lượng có proof; model baseline chưa đo được báo riêng |
| P11-02 | Build relation index nhỏ, có provenance và lifecycle | P11-01, GO sơ bộ | DONE — 100%; source audit 249 node/72 cạnh, cap storage và 16 mechanics/lifecycle tests PASS |
| P11-03 | Tích hợp query/grounding/cache/fallback có budget | P11-02 | DONE — 100%; actual16/source review, caps/cache/fallback và 131 focused controls PASS |
| P11-04 | Nghiệm thu quality, lợi ích và regression | P11-03 | DONE — 100%; quality benefit, hồi quy68/300/24/24 và offline tests/coverage PASS |
| P11-05 | Exit audit, handoff và cleanup | P11-04 | DONE — 100%; 20 bước audit, handoff/bindings/restore/secret/diff và cleanup PASS |

**P11-01 — Chứng minh cần làm trước khi thêm code.**

1. Đọc kết quả Phase 9/10; kiểm kê phần đã có, lỗi tái hiện, phần thiếu và ngoài
   scope. Chọn user queries cụ thể, ưu tiên direct/inverse relation lookup;
   không coi tên “Knowledge Graph” là yêu cầu phải thêm database.
2. Source-review identity/edge/direction của hai family; khóa 16 case, negative
   rationale và controls. Ghi exposure, không gọi tập đã xem là fresh holdout.
3. Chạy graph-OFF baseline bằng service thật, lưu đúng/sai/chưa đo, counters,
   local costs và source/runtime/index hashes. Reuse output cũ chỉ khi actual
   prompt/schema/source tương thích; không dùng synthetic answer thay chất lượng.
4. Chốt một hướng lưu cạnh, schema nhỏ, nhánh lợi ích và budgets; quyết định
   GO sơ bộ/NO-GO có lý do. Chỉ GO mới mở P11-02; NO-GO không chặn Phase 12.

**Đầu ra:** gap/decision record, source-edge map, frozen benchmark/rubric/protocol
và baseline có hashes. **DONE khi:** đủ nguồn và baseline để quyết định, mọi
case có proof hoặc negative rationale, không có phần quality chưa đo bị ghi PASS.

**P11-02 — Tạo chỉ mục cạnh từ evidence đã xác minh.**

1. Dùng extractor/table rules hiện có tạo entity occurrence, direct edge và
   fact references. Không parse bằng LLM, không lấy edge từ gold hoặc history.
2. Lưu forward/reverse lookup và provenance trong một sidecar; giữ direction,
   scope, source version, original cells và conflict status. Không tạo cạnh
   transitive, tương đương hoặc alias không có nguồn.
3. Build theo nguồn, idempotent và atomic; manifest bind source/index/extractor/
   schema hashes. Source update/delete/reindex vô hiệu bản derived cũ; lỗi giữa
   chừng không làm ready index nửa vời, restart không nhân đôi entity/edge.
4. Kiểm tra source→index và index→source: không sót cạnh thuộc contract, không
   phát sinh cạnh giả; test code spacing, duplicate/conflict, blank/OR cells,
   direction, deletion, corrupt manifest và build interruption.

**Đầu ra:** builder/reader tối thiểu, sidecar/manifest có hashes và edge audit.
**DONE khi:** extraction precision/recall đều 100% trên tập cạnh hỗ trợ đã source-
review (case không hỗ trợ báo riêng), provenance/direction 100%, lifecycle controls
PASS và sidecar nằm trong cap; chưa tính index đúng là answer quality đã PASS.

**P11-03 — Dùng index để lấy nguồn, giữ nguyên guard trả lời.**

1. Route deterministic chỉ intent quan hệ đã chốt; resolver và authorization
   chạy trước lookup. Feature flag mặc định OFF trong khi nghiệm thu, các intent
   khác giữ đường cũ. Không planner/model load hoặc public API/schema mới.
2. Lookup/traverse tối đa hai hop, kiểm tra fan-out/cycle và budget trước khi
   mở rộng. Fetch source chunk/row theo pointer, kiểm chứng lại cạnh và fact;
   graph stale hoặc dangling pointer không trở thành evidence.
3. Đưa evidence thật qua context/claim/citation/conflict/completeness guards
   hiện có. Arithmetic/local negatives không cần model; thiếu edge/citation,
   wrong direction hoặc trả lời thiếu danh sách phải bị chặn.
4. Bind graph/source generation và policy vào cache hiện có. Test graph on/off,
   update/delete một nguồn, scope/filter/time/history, operand order, restart,
   corrupt sidecar và fallback còn/hết budget; trace cả graph lookup/proof fetch,
   search, encoder, generation và candidate counts.

**Đầu ra:** tích hợp nhỏ trong service, source-backed traces, cache/fallback
controls. **DONE khi:** dev/control cases đúng đầy đủ; false edge/leak=0, không
vượt cap, graph OFF giữ behavior cũ và lỗi index không làm request treo/crash.

**P11-04 — Đo chất lượng và lợi ích trước khi quyết định giữ graph.**

1. Chạy đủ 16 case qua service thật ở OFF/ON; review từng endpoint/edge/path/
   fact/citation và completeness. Không nhận abstain tất cả là thành công.
2. Nếu cần model output mới, xuất một packet gộp prompt/evidence/schema thật,
   không gold, tối đa tám positive cần generation. Owner dùng Gemini Chat;
   nhận raw, báo parse/schema và syntax-only normalization riêng, source-review
   rồi actual replay. Không chờ API/quota và không gửi lại payload đã tương thích.
3. Chạy phép đo lợi ích đã khóa ở 11.2; báo quality dev/acceptance, chi phí
   build/storage/cold/warm/RSS/counters, cả lỗi và trường hợp không cải thiện.
   So cả end-to-end local processing để không che chi phí proof/fallback.
4. Chạy focused controls; nếu sửa shared retrieval/service/claim/cache thì replay
   regression Phase 7/8/9/10 (68/300/24/24) khi payload tương thích, review phần
   thay đổi. Chạy full offline suite một lần khi runtime ổn, coverage ≥85%;
   lưu failure, sửa bằng dev/generalized fixture, không tune gold acceptance.

**Đầu ra:** per-case source review/replay, OFF/ON comparison, regression và
tests/coverage receipt. **DONE khi:** 8/8 positive và 8/8 negative đúng, không
case thiếu/chưa chấm, citations/edges/schema đạt 100%, regression không giảm và
lợi ích đã khóa đạt. Không đạt lợi ích thì ghi NO-GO, không gán PASS kỹ thuật
thành “graph hữu ích”; native API reliability/latency vẫn không được suy từ Chat.

**P11-05 — Chốt hồ sơ và giữ dự án gọn.**

1. Audit từng bước/task/gate với source/config/index/raw/review/test bindings;
   phân biệt real-source quality, synthetic controls, exposure và local timing.
2. Viết handoff: scope/edge direction/budget, build/rebuild/update/delete,
   cache/fallback, feature flag, rollback và lệnh replay offline. Chỉ bật cho
   profile/intent đã đạt nghiệm thu; MVP không phụ thuộc graph để khởi động.
3. Cập nhật task/%/gate trong root `plan.md`, lưu snapshot roadmap tại exit;
   giữ Phase 0–14, kết quả Phase 7–10 và R-01/R-02 NOT PASSED.
4. Kiểm tra references/bindings/secret/diff và artifact restore; nén raw cần
   audit, xóa temp/draft/build/cache dư. Nếu NO-GO, rollback/gỡ code prototype
   không dùng, giữ baseline/failure/decision proof, không để backend nửa làm.

**Đầu ra:** một completion hoặc decision summary, handoff, immutable roadmap
snapshot và cleanup receipt. **DONE khi:** exit GO thực sự đạt đủ gate; nếu
NO-GO chỉ đóng audit/decision với trạng thái DEFERRED, không khai graph hoàn tất.

#### 11.4 Gates, tiến độ và exit

| Gate | Điều kiện PASS / chuẩn đầu ra | Trạng thái hiện tại |
|---|---|---|
| T11-01 — Nhu cầu/protocol | Baseline/source proof đủ; GO sơ bộ có căn cứ; 16 case/hashes/rubric/nhánh lợi ích/ngưỡng frozen, split tách family, không sửa gold sau acceptance. | PASS — source audit/protocol và actual baseline |
| T11-02 — Entity/edge/index | Identity/direction/provenance và extraction precision/recall 100% trên quan hệ hỗ trợ; không false edge/merge; build/update/delete/corrupt/restart controls PASS, storage trong cap. | PASS — index audit và 16 mechanics tests |
| T11-03 — Query safety/quality | 8/8 positive đầy đủ, 8/8 negative đúng; edge/path/claim/citation/source-coordinate/public schema 100%; leak/unsupported/contradicted/false abstention=0; caps/context/cache/fallback PASS. | PASS — actual16 và focused controls |
| T11-04 — Giá trị/regression | Ít nhất một nhánh lợi ích đã khóa đạt; chi phí và faults công khai; regression liên quan không giảm, required tests 0 FAIL, full offline coverage ≥85%, live SKIP báo riêng. | PASS — quality benefit, regression416/416 và offline suite |
| T11-05 — Exit | Task chuẩn đầu ra đủ; bindings/restore/secret/diff/rollback/handoff/cleanup PASS, roadmap và limitations đúng thực tế, không phí/API qualification giả. | PASS — exit audit/restore/secret/diff/cleanup |

Thứ tự: **P11-01 → quyết định GO → P11-02 → P11-03 → P11-04 → P11-05**.
Mỗi task có bốn bước: PLANNED 0%, IN PROGRESS 25/50/75%, DONE 100% khi đủ
chuẩn đầu ra và proof. Báo task count/gate count riêng, không dùng thời gian chờ
Chat làm % tiến độ. **Chỉ nhận Phase 11 graph DONE 100% khi 5/5 task DONE và
5/5 gate PASS**. NO-GO/DEFERRED giữ trạng thái/việc chưa làm rõ, không đổi mẫu số
hoặc đánh dấu các task chưa triển khai thành DONE để đạt 100%.

Hồ sơ tối thiểu khi triển khai: một bộ nhỏ tại `evaluation/phase11/` (protocol,
benchmark, rubric), một completion/decision summary tại `evaluation/results/`
và một handoff tại `docs/`. Raw/index/snapshot lớn dùng artifact store có hashes;
không tạo report cho từng retry hoặc commit sidecar/corpus/model weights vào Git.

### Phase 12 — Web app MVP

Trạng thái: **DONE — 100% (5/5 task, 8/8 UI work item; 15/10/2026)**.
Phạm vi hoàn tất: Web app MVP chạy local, nghiệm thu bằng kiểm thử offline.
Tái sử dụng application/query/registry/job, giữ public answer schema. UI riêng
trong `src/campusai/ui/`, chia pages/styles/scripts/features, không thêm build
system hoặc frontend dependency vào runtime.

1. DONE — upload PDF thật, signature/size/encryption validation, tiến độ worker,
   ready khác ingestion complete; failed/review/cancel và retry có kiểm thử.
2. DONE — chọn nguồn chính xác, hỏi đáp, citation doc/page/quote, PDF đúng trang;
   source bytes phải khớp document hash, không dùng highlight giả.
3. DONE — phân biệt thiếu bằng chứng/quá tải/lỗi, một request mỗi lần gửi,
   timeout client 45 giây có giải thích không hủy server work; không retry tự động.
4. DONE — feedback lưu thật, scope tại server, delete source/store/index/cache,
   eviction retriever và bindings job; không còn stale source/citation.
5. DONE — E2E PDF upload thật với provider local chỉ trong test; cả bốn tab,
   keyboard/drawer/dialog, XSS/scope/junction và sáu viewport đã kiểm tra.

Evidence: [UI architecture/API/acceptance](docs/ui/phase12-ui.md),
[source/artifact receipt](docs/ui/evidence/acceptance.json),
[browser checks](docs/ui/evidence/browser-results.json).
Kết quả hiện hành: **1.604 offline PASS, 2 opt-in live SKIP; 38 focused PASS**;
**29 browser checks PASS**, axe không có lỗi A/AA trong các trạng thái đã audit.
Reviewer: **Codex — Automated AI Review**, không thay chữ ký con người.

23/10/2026 — tối ưu throughput sau nghiệm thu MVP, không đổi grounding/citation/
abstention thresholds: mặc định chạy **3 PDF ingestion workers + 8 queued jobs**
và tối đa **4 query workers**. Năm PDF có thể được chọn/tải đồng thời; mỗi file
có tiến độ riêng, file lỗi được giữ để thử lại. Upload body, kiểm tra PDF và ghi
file không còn bị tuần tự hóa bởi UI lock; job capacity, registry và publish index
vẫn có đồng bộ riêng. Các câu hỏi đọc corpus dùng shared access; thao tác thay/xóa
tài liệu vẫn được bảo vệ. Danh sách nhiều tài liệu lấy một snapshot job thay vì
quét lại lịch sử cho từng PDF. Hai PDF thật (34 và 13 trang) hoàn tất upload/index
trong 4,515 ms song song so với 4,980 ms tuần tự (~9,3% nhanh hơn) là baseline
trước khi tăng worker count, trên profile local hash-model.

Kiểm thử browser E2E mới nhất đạt **39/39 checks**, gồm sáu PDF bị từ chối đúng
giới hạn, năm PDF upload đồng thời và chuyển sang ready, các luồng chat/source/
delete, sáu viewport và axe A/AA. Full regression hiện hành: **2.368 PASS, 2
opt-in live SKIP**. HTTP workload cục bộ, offline với BGE-M3 trên năm PDF fixture
1 trang (4,749 bytes): cả năm được nhận trong 0,113 giây và ready trong 9,619 giây
kể cả nạp model lạnh. Tiếp đó 100 câu EN/VI tự nhiên chạy qua bốn query workers:
100/100 HTTP/API success trong 4,853 giây, p95 0,324 giây; deterministic test
provider trả citation đúng cho 72 câu và fail-closed abstention cho 28 câu (13
unsupported claim, 15 ambiguous). Đây là kiểm tra pipeline/retrieval/concurrency,
không phải đánh giá chất lượng model thật; không có Gemini/provider call và không
hạ threshold. Live quota/latency/answer quality chưa được đo. Source/runtime SHA
hiện hành: `d531563c32cfca89d081d81d16b82461246a96299568285846eef0729b91894d` /
`2554b054a90db099335aea0d384a9e137f124692f78ba788cf9bac3063de010a`.

Exit local MVP đạt: upload → ready → chat → source → feedback/delete.

Full-app QA goal remains ACTIVE. MVP acceptance does not close the broader
optimization/AI-quality goal. Evidence: [QA audit](QA_AUDIT.md),
[scenarios](TEST_SCENARIOS.md), [performance](PERFORMANCE_REPORT.md), and
[improvement log](IMPROVEMENT_LOG.md).

| QA item | Required behavior | Current state |
|---|---|---|
| QA-01 | App works from clean Git source | DONE - clean exported tree has 114 app tests PASS. |
| QA-02 | Current-source native answer quality | DONE for the accepted Phase5 snapshot:400/400 outputs and all5 gates PASS. See phase5-closure.json; subsequent app changes require their own regression checks. |
| QA-03 | Realistic full upload/OCR/index load and fidelity | IN PROGRESS - five real PDFs / 104 pages measured before and after; 3/5 ready in both runs. Two large scans still exhaust the OCR budget. Raw benchmark retained in docs/ui/evidence/pdf-runtime-load.json. |
| QA-04 | Preserve mixed native/scan pages and legacy readiness | DONE - selective OCR, fail closed on unread pages; audit legacy sources/cache/job identity. |
| QA-05 | Explicit bounded local OCR from document details | DONE - no reupload, manual retry retains history, source/scope checks, server cap 50 scan pages/120 seconds. |
| QA-06 | Existing job journal survives upgrade | DONE - exact legacy/current identity validation; corrupt rows fail closed; 2 local PDFs and 5 jobs retained. |
| QA-07 | Expanded AI/PDF quality | OPEN - at least100 verified AI cases,30 distinct representative PDF fixtures; extraction98%, OCR90%, retrieval95%, context95%, accuracy90%, hallucination<=2%, no document/page loss. Reuse reviewed evidence where applicable; do not count fixture-provider answers as live AI. |
| QA-08 | Fixed-environment performance and concurrency | OPEN -20 simultaneous users; ordinary API p95<=500ms, real AI TTFT p95<=5s,100-page/10MB text PDF p95<=15s; LCP<=2.5s, INP<=200ms, CLS<=0.1. Baseline and measured after-state required. |
| QA-09 | Final stability and recovery | IN PROGRESS -three consecutive full regressions DONE on identical source/runtime bytes:2,570 PASS/2 opt-in SKIP each. Browser43/43 PASS on desktop/mobile. Broader recovery/security and fixed-environment performance acceptance remain open; secret scan PASS. |
| QA-10 | Cancel OCR promptly and show monotonic progress | DONE -page-boundary cancellation stops remaining OCR pages; physical-page progress is reported and later stages cannot lower it. Two failures reproduced before repair;30 focused tests and2,665 full-suite tests PASS,2 opt-in live SKIP. Evidence:docs/ui/evidence/ocr-evaluation-20261025.json. |

2026-10-25 app repair regression also reran all400 Phase5 requests against
their exact native HTTP captures:400/400 complete,0 pending, all output/evidence
rows identical to the accepted snapshot,0 fresh provider calls. This verifies
answer behavior after the OCR callback changes; it does not relabel cached
responses as fresh inference or replace the bound Phase5 release report.

Latest full-worktree regression:2,665 PASS /2 opt-in live SKIP (282.89 s),
`docs/ui/evidence/ocr-regression-20261025.xml`. The earlier local-OCR UI
cycle had2,384 PASS /2 opt-in live SKIP (258.03 s).
Focused OCR/web/PDF/jobs: 37 PASS. Clean Git tree
`d4fa931f219a8b47423474e9a10003fb55089917`: 114 app tests PASS (11.95 s).
Browser E2E: 41/41 PASS with actual local OCR, recovery after admission error,
axe OCR dialog and six baseline viewports. Current receipts:
`docs/ui/evidence/ocr-ui-tests.xml`, `docs/ui/evidence/ocr-browser-results.json`;
parser baseline/after hashes remain in `docs/ui/evidence/pdf-parser-batch.json`.
No provider calls, journal reset, user-document deletion or threshold changes.

Local startup đã hoàn thiện bằng `start-campusai.cmd`: tự đọc cấu hình/credential
local đã có, không in key/đổi key/model/bật billing. PDF owner đã index xong;
đáp án thật bằng VI/EN trên nguồn tiếng Anh và mở đúng trang quote đã kiểm tra.
Năm lần query ứng dụng được giữ đủ: hai đáp án có căn cứ, một claim bị từ chối
trước sửa prompt và hai phản hồi lỗi provider/kết nối; xem evidence UI. Không
suy lượt smoke nhỏ thành nghiệm thu quota provider, SLO hay public deployment;
**R-01/R-02 vẫn DEFERRED — NOT PASSED**. Single-user loopback, chưa có account
authentication/multi-user ownership. Job history hiện theo vòng đời process;
thiết bị mobile thật và public vận hành thuộc Phase 13/14.

### Phase 13 — Deployment

Trạng thái: **IN PROGRESS — 6/64 tiêu chí (9,4%), 0/16 task DONE**.
Mỗi task có bốn tiêu chí bắt buộc bên dưới; tỷ lệ phase = số tiêu chí có evidence
đã kiểm tra / 64. Không tính thời gian chờ tài khoản hoặc code chưa chạy thành DONE.
Phụ thuộc MVP Phase 12; lỗi vận hành local được sửa trước khi mang lên cloud.

#### Phạm vi và quyết định hạ tầng ngày 15/10/2026

Owner yêu cầu **cloud miễn phí hoàn toàn, không phụ thuộc máy cá nhân**, và xác nhận
chưa có Oracle account nhưng có thể tự đăng ký/xác thực thẻ. Owner xác nhận lại
ngày 15/10: chưa đăng ký, sẽ cung cấp thông tin sau. Tiếp tục code/test/docs độc lập;
không hỏi lại cho đến khi owner cập nhật và không coi đây là yêu cầu pause goal.
Không đưa self-host
laptop vào phương án nghiệm thu. Target ưu tiên: **một OCI Ampere A1 Always Free VM,
2 OCPU / 12 GB RAM**, Linux ARM64; tổng boot + data volume tối đa 200 GB trong home
region, cấu hình ban đầu 50 GB boot + 50 GB data nếu quota thực tế cho phép.
Đây là target cần preflight tài khoản/capacity, chưa phải VM đã cấp thành công.

Một process ứng dụng dùng chung BGE-M3 CPU; một worker ingestion; giới hạn query
đồng thời bằng 1, từ chối nhanh request vượt tải. Giữ UI tĩnh cùng origin với API,
JSON indexes + SQLite metadata/job/budget cần thiết; không thêm Kubernetes, Redis,
vector DB, GPU thuê, frontend hosting hoặc managed database khi chưa cần.
Ưu tiên virtualenv + systemd trực tiếp trên VM để giảm RAM/build/storage overhead.
Container chỉ thêm khi chứng minh lợi ích, không phải chuẩn đầu ra bắt buộc.
Reranker/KG giữ OFF; không thay model/quality contract để vừa hạ tầng.

Chi phí thuê compute, storage, ingress/DNS và provider trong profile phải là
**0 USD/tháng trong quota đã kiểm chứng**. Không dùng trial credit làm điều kiện
chạy app, không nâng PAYG/bật billing, không tự chuyển paid hardware/service/key/model.
Budget alert không thay hard limit. Khi hết quota/capacity: báo rõ và dừng phần
phụ thuộc, vẫn làm code/test/docs độc lập. Không tạo tải giả để chống thu hồi VM.

Ingress mặc định cho Phase 13: HTTPS riêng cho owner trên VM qua Tailscale Personal
và Serve; không cần tên miền trả phí, app chỉ bind loopback và ACL giới hạn owner.
Máy cá nhân chỉ là client, không chạy backend. Public URL cho mọi người thuộc Phase 14,
sau authentication/ownership/abuse/privacy/release gates. Nếu owner cần public staging,
phải khóa phương án DNS/TLS miễn phí và xác thực trước khi mở ingress.

Các hạn mức được kiểm tra từ nguồn chính thức ngày 15/10/2026:

| Phương án | Đánh giá cho backend hiện tại | Quyết định |
|---|---|---|
| [OCI Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) | A1 Free tenancy hiện là 2 OCPU/12 GB, 200 GB block volume; có thể thiếu capacity/thu hồi VM idle. [Đăng ký yêu cầu thẻ xác thực](https://www.oracle.com/cloud/free/faq/). | Target có điều kiện; xác nhận Console/account trước provision. Không dùng số 4 OCPU/24 GB cũ. |
| [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces-overview) | Tạo Docker/Gradio compute Space mới yêu cầu paid plan, ngoại lệ ZeroGPU có điều kiện riêng. | Không dùng Docker CPU Basic làm mặc định miễn phí; quyết định GPU Phase 7 là lịch sử. |
| [Render Free](https://render.com/docs/free), [compute](https://render.com/docs/compute-plans) | 512 MB RAM, disk ephemeral, không có persistent disk miễn phí; không phù hợp model hiện tại. | Loại khỏi profile chính. |
| [Tailscale Personal](https://tailscale.com/pricing), [Serve](https://tailscale.com/docs/features/tailscale-serve) | Personal 0 USD, tối đa 6 users; HTTPS trong tailnet, cần account/client và ACL. | Ingress riêng cho owner; không suy thành public hosting hay SLA. |

Snapshot local chỉ dùng capacity estimate, không thay số đo ARM64/cloud:
[infrastructure audit](docs/deployment/phase13/evidence/infrastructure-audit.json).

#### Danh sách task và chuẩn đầu ra

**C13-01 — Khóa profile và điều kiện miễn phí. IN PROGRESS — 2/4 (50%).**
Phụ thuộc: Phase 12. Đầu ra: `docs/deployment/phase13/profile-decision.md` và
`evidence/infrastructure-audit.json`, sau đó bổ sung receipt quota Console đã che dữ liệu riêng.

- [x] Kiểm kê runtime/model/storage và gap thật: server local, queue/job, restart/rollback checker.
- [x] Đối chiếu nguồn chính thức; ghi yêu cầu cloud-only, zero-cost, target và phương án bị loại.
- [ ] Owner hoàn tất account; kiểm tra home region, Always Free entitlement, usage hiện có và khả năng cấp A1; lưu kết quả thật.
- [ ] Khóa một profile triển khai với quota/cost hard stops, RAM/disk/worker budget và giới hạn sleep/reclaim; không còn prerequisite không rõ.

**C13-02 — Runtime và cấu hình triển khai. IN PROGRESS — 1/4 (25%).**
Phụ thuộc: C13-01 cho target thật; thiết kế có thể chuẩn bị trước account.
Đầu ra: `configs/deployment/`, `src/campusai/deployment/` chia module theo trách nhiệm.

- [ ] Validate env/schema: absolute data paths, allowed hosts/origins, timeout, concurrency, quota; sai cấu hình phải fail startup rõ.
- [ ] Tách state `/var/lib/campusai`, model cache, config/secrets và immutable release; không ghi dữ liệu người dùng vào source checkout.
- [ ] Khóa CPU/model revision, runtime/Python/dependency identity và flags OFF; startup không nạp corpus evaluation hay gọi provider.
- [x] Tests cấu hình hợp lệ/sai/missing secret/path và contract local hiện có PASS; có lệnh preflight không lộ secret.

[Configuration/preflight guide](docs/deployment/phase13/runtime-configuration.md),
[109 focused PASS](docs/deployment/phase13/evidence/cloud-runtime-focused.xml) và
[source/artifact receipt](docs/deployment/phase13/evidence/cloud-config-receipt.json)
ghi **1.676 regression PASS / 2 opt-in live SKIP**. Template chưa điền owner/identity
phải bị từ chối exit 2. Cấu hình tách state/cache/config/release, validate env roots,
loopback host/origin, timeout/worker caps, flags OFF và quota receipt; không đọc key
local, tạo data root, load model hoặc gọi provider trong preflight.

Đã thêm opt-in pinned BGE cho cả ingestion/index/query: manifest đủ 11 file và
commit `5617a9f61b028005a4858fdac845db406aefb181`; index lưu revision thật và từ chối
legacy/missing dense khi chạy profile pin. [Native offline check](docs/deployment/phase13/evidence/dense-model/offline-windows.json)
dùng BGE thật trên **Windows AMD64**, CPU, một encoder, vector 1.024 chiều,
12,48 giây cho fixture nhỏ, zero socket/API attempts. Đây không phải ARM64/cloud
hoặc SLO; chưa rewrite index của owner. Production entrypoint, supervisor,
resource controls, durable jobs/budgets và volume thật chưa nối đủ, nên ba tiêu
chí runtime/startup còn mở; không lấy preflight làm deployment acceptance.

**C13-03 — Gói cài đặt tái lập trên ARM64. TODO — 0/4.**
Phụ thuộc: C13-02. Đầu ra: lock/constraints ARM64, wheel + manifest, script install/preflight.

- [ ] Cài đúng Python/PyTorch CPU/BGE-M3 trên ARM64 thật; xác minh wheel availability, không giả PASS bằng máy AMD64.
- [ ] Pin dependency/model revision và hashes; gói chỉ có runtime/UI assets cần thiết, không chứa key, PDF riêng, venv hoặc benchmark nặng.
- [ ] Clean checkout + artifact manifest dựng được runtime trên VM; BGE tải/cache một lần, offline warm restart không tải lại.
- [ ] Artifact manifest ràng buộc source/config/lock/model/package; giữ bản trước để rollback, kiểm tra license và install verification.

**C13-04 — HTTP server và service supervisor. TODO — 0/4.**
Phụ thuộc: C13-02/03. Đầu ra: production WSGI entrypoint + systemd unit/runbook.

- [ ] Thay wsgiref ở deployment bằng WSGI server phù hợp, một process/model, HTTP threads có giới hạn, bind loopback.
- [ ] systemd chạy user riêng, restart có backoff/start limit, graceful shutdown và startup timeout; không tạo restart loop do provider 503.
- [ ] Health/UI/document polling vẫn phản hồi khi một query đang chờ API; thêm request phải nhận busy response có hạn thay vì xếp hàng vô hạn.
- [ ] Test hai HTTP request đồng thời, process exit/restart thật, model singleton và shutdown không mất job/state PASS.

Local follow-up ngày 15/10: query không giữ khóa metadata khi chờ provider.
Health/UI/document polling/readiness và POST quote lookup vẫn phản hồi;
corpus writes giữ lease đến khi query kết thúc. [40 focused tests](docs/deployment/phase13/evidence/ui-polling-focused-final.xml)
kiểm request đồng thời qua HTTP thật; xóa hai method shadowed giống hệt trong
WebDocuments. Chưa thay production WSGI/systemd hoặc đo ARM64/VM, nên chưa
đánh dấu tiêu chí production đạt chỉ bằng server loopback.

**C13-05 — Secrets và ingress HTTPS riêng. TODO — 0/4.**
Phụ thuộc: C13-01/04. Đầu ra: env template, ingress/ACL config và access evidence.

- [ ] Secrets chỉ từ env/file quyền hạn chế ngoài release; thiếu/sai credential báo mã an toàn; không đọc key local hoặc lộ qua UI/log/package.
- [ ] Tailscale Personal trên VM, Serve HTTPS và ACL chỉ owner hoạt động; xác minh đúng gói miễn phí, không dùng trial/business paid plan.
- [ ] Backend không mở Internet/LAN trực tiếp; chặn giả identity/proxy headers, cross-origin writes; health/metrics và PDF không rò ra ngoài quyền.
- [ ] Client được phép truy cập đủ luồng; client không được phép bị chặn; TLS và secret redaction được kiểm tra thực tế.

**C13-06 — Persistence và giới hạn dung lượng. TODO — 0/4.**
Phụ thuộc: C13-02/03. Đầu ra: data layout/volume mount + consistency checks.

- [ ] PDF, registry, chunks, BM25/dense indexes, job ledger và provider cooldown/budget nằm trên persistent volume đã xác nhận miễn phí.
- [ ] Mount thiếu/read-only/thiếu disk thì fail closed, không âm thầm ghi vào ephemeral root; atomic writes và checksum được giữ.
- [ ] Cap storage app ban đầu 10 GiB và tối đa 80% data volume; upload kiểm tra chỗ trống gồm staging/index overhead, trả lỗi trước khi ghi thiếu.
- [ ] Upload/index/delete qua HTTP rồi restart process và reboot VM: doc_id/hash/page/ready giữ đúng, không hồi sinh tài liệu đã xóa.

**C13-07 — Job bền vững và hàng đợi hữu hạn. TODO — 0/4.**
Phụ thuộc: C13-06. Đầu ra: SQLite/job journal gọn, recovery contract + fault tests.

- [ ] Một ingestion worker, tối đa 2 job chờ; kiểm tra admission trước tạo file/job; queue đầy trả 429/busy có hướng dẫn.
- [ ] Persist job/source/options/progress/terminal state và dedupe identity; API/UI đọc được history sau restart.
- [ ] Khi process chết giữa job: đánh dấu interrupted/retryable hoặc resume idempotent theo checkpoint; không báo ready khi index chưa commit.
- [ ] Kill/restart ở upload/parse/index, retry/cancel/delete và duplicate concurrent upload PASS; không có orphan/corpus lẫn hoặc job treo vĩnh viễn.

**C13-08 — Provider failure, quota và UX chờ. IN PROGRESS — 3/4 (75%).**
Phụ thuộc: C13-02 cho profile; sửa regression local độc lập được làm ngay.
Đầu ra: bounded query admission, provider fault/cache fix và quota receipt; tham khảo repo owner yêu cầu.

- [x] Không cache provider lỗi tạm thời; phân biệt 503/cooldown, 429/quota, timeout, credential/format với thiếu bằng chứng; retry sau hồi phục dùng lại câu hỏi được.
- [x] UI nhận error code/Retry-After, báo thời gian chờ và retry thủ công; history không đưa lỗi hệ thống vào hội thoại; không tự gửi retry/key/model fallback.
- [ ] Persistent call/token budget dùng giới hạn nhỏ hơn quota account và cap cấu hình; restart/cache/concurrency không vượt budget; provider không billing, max_retries=0.
- [x] Fault tests success→503→cooldown→recovery, 429/timeout, cached success, hai request đồng thời và no-extra-call PASS; giữ nguyên grounding/citation validator.

Evidence C13-08: [repo review](docs/deployment/phase13/repository-review.md),
[81 focused tests](docs/deployment/phase13/evidence/provider-recovery-tests.xml),
[32 browser checks](docs/deployment/phase13/evidence/provider-recovery-browser/browser-results.json).
Historical source-bound [recovery receipt](docs/deployment/phase13/evidence/provider-recovery-receipt.json)
có 1.613 regression PASS / 2 opt-in live SKIP và kiểm wheel UI 10/10 assets.
Đây là fault injection/offline + loopback, **0 live provider calls**; không phải
cloud smoke hoặc availability/SLO. Cache đã loại lỗi API từ trước; thay đổi mới
là HTTP error classification, cooldown UX/history và local HTTP/query admission.

Owner yêu cầu thử chuyển Gemini 2.5 Flash nếu tiết kiệm token (15/10/2026).
Candidate dùng `thinkingBudget=0`; GET metadata 2.5/3.8 đều 200 nhưng một lần
inference 2.5 qua credential hiện có trả **404**, protocol dừng, không retry/key
rotation/paid OpenRouter fallback. [Candidate evidence](docs/deployment/phase13/evidence/model25/candidate-smoke.json)
giữ nguyên failure; chưa so sánh được token giữa hai model, chưa đổi active profile.
Google hiện hạn chế dòng 2.5 cho người đã dùng trước; không suy metadata PASS
thành quyền inference hay kết luận 404 chắc chắn do entitlement.

Owner tiếp tục yêu cầu hỏi được nhiều câu liên tiếp. Thử Gemini 3.5 Flash-Lite
`thinkingLevel=minimal`: hai native calls ban đầu trả về nhưng một đáp án VI bị
validator từ chối; giữ [candidate failure](docs/deployment/phase13/evidence/flash-lite-candidate/candidate-smoke.json).
Một sequence HTTP riêng qua app đầy đủ đạt 2 câu có nguồn (~6,4/6,5 giây),
câu thứ ba trả **503**; dừng ở 3/10, không resume/retry/rotate key và **không đổi
model mặc định**. [Live report](docs/deployment/phase13/evidence/flash-lite-candidate/http-sequence-initial/report.json).
Đổi model nhẹ hơn chưa đủ chứng minh hết overload hoặc tiết kiệm token.

Bổ sung fallback local opt-in tại product entrypoint: đáp án AI vẫn abstained,
trả riêng tối đa 3 trích đoạn nguyên văn đã kiểm quote/page theo request scope;
UI ghi rõ chế độ đọc nguồn, cho tra cứu tiếp và mở PDF. Không sinh nội dung mới,
không cache excerpt/fault hoặc đưa degraded turns vào history. Trong cooldown,
lookup không gọi Gemini; không dùng paid provider/model fallback.
[Review](docs/deployment/phase13/provider-continuity.md) và
[receipt hiện tại](docs/deployment/phase13/evidence/source-excerpts-receipt.json):
**1.621 regression PASS / 2 live SKIP, 40 focused PASS, 36 browser checks,
wheel UI 11/11 assets**. Fault test kiểm 20 HTTP lookup → một injected 503 →
19 lookup local → hồi phục và cache thành công; đây không phải 20 Gemini answers.
Hai receipt Phase 12/provider recovery trước đó giữ nguyên identity lịch sử.
Không tăng % Phase 13 hoặc đánh dấu C13-08 DONE: persistent budget/quota thật và
độ sẵn sàng provider vẫn chưa được nghiệm thu.

**C13-09 — Startup, health, readiness và cold start. TODO — 0/4.**
Phụ thuộc: C13-04/06/08. Đầu ra: lifecycle probes + source-bound measurements.

- [ ] `/live` chỉ process; `/ready` 503 đến khi model/index/storage sẵn sàng; provider outage hiển thị degraded mà không restart toàn app.
- [ ] Không tải model mỗi request; kiểm checksum/model identity khi start, cache warm load và missing/corrupt index fail closed.
- [ ] Đo ít nhất 3 cold starts + 3 warm restarts trên cùng VM/profile; ghi download/startup/ready time, RSS, CPU, disk và mọi lần thất bại.
- [ ] Warm restart từ model cache ≤120 giây, readonly health/UI p95 ≤1 giây khi query chờ; không PASS dựa vào probe gọi provider.

**C13-10 — Provision và deploy cloud thật. TODO — 0/4.**
Phụ thuộc: C13-01/03–09. Đầu ra: idempotent bootstrap/deploy script và VM receipt đã redaction.

- [ ] Provision đúng A1/region/quota và network/volume miễn phí; estimate + thực trạng 0 USD, không dùng trial/PAYG/paid resource.
- [ ] Deploy release có identity, model cache và env template bằng lệnh tài liệu hóa; tắt app nếu preflight thiếu điều kiện.
- [ ] Service chạy sau logout SSH và reboot VM; URL HTTPS owner dùng được từ client khác khi máy phát triển không chạy backend.
- [ ] Redeploy cùng release idempotent, không ghi đè state/key, không nhân bản model/worker; ghi cấu hình thật và lệnh tái lập.

**C13-11 — Smoke đầu-cuối trên URL cloud. TODO — 0/4.**
Phụ thuộc: C13-10. Đầu ra: `evidence/cloud-smoke.json` + browser evidence.

- [ ] Empty state → upload PDF được phép dùng → job progress → ready → chọn scope → chat hoạt động trên HTTPS thật.
- [ ] Ít nhất một câu VI và một câu EN có đáp án qua provider thật, claim/quote/trang đối chiếu PDF; negative phải abstain đúng.
- [ ] Preview/locate, feedback, retry/cancel, dedupe, delete và thay scope/cache được kiểm tra; không dùng tài liệu riêng đang có để upload công khai.
- [ ] Browser desktop/mobile viewport không lỗi JS/overflow; provider lỗi được báo rõ và UI còn thao tác được; fake/replay ghi riêng, không tính là live.

**C13-12 — Backup và restore sạch. TODO — 0/4.**
Phụ thuộc: C13-06/07/10. Đầu ra: backup/restore CLI, manifest và actual recovery receipt.

- [ ] Backup nhất quán khi quiesce writes: PDF/registry/index/jobs/schema/version/checksum; secret không nằm trong backup công khai.
- [ ] Bản sao độc lập khỏi VM/volume đang chạy trên storage miễn phí trong quota; retention tối đa 3 bản theo disk budget, có restore command.
- [ ] Restore vào data root sạch rồi chạy process mới: list/ready/query/source/quote/delete-state đúng; dữ liệu hỏng/path traversal bị từ chối.
- [ ] Mục tiêu RPO ≤24 giờ, RTO ≤30 phút trên dataset acceptance ≤100 MiB; đo thực tế, không suy thành SLA. VM reclaim không mất mọi bản sao.

**C13-13 — Rollback release và dữ liệu. TODO — 0/4.**
Phụ thuộc: C13-03/10/12. Đầu ra: release manifest, rollback command + real HTTP receipt.

- [ ] Giữ current + previous release immutable, checksum/config/schema compatibility và snapshot trước migration; không rollback mù vào schema mới.
- [ ] Tạo lỗi release thử trong staging, chuyển về previous bằng quy trình có maintenance/quiesce; không đụng app local của owner.
- [ ] Process cũ chạy lại thật, health/ready/upload/query/source/citation và cache invalidation đúng sau rollback; không chỉ kiểm dense.json load được.
- [ ] Rollback hoàn tất ≤10 phút trên dataset acceptance; kiểm doc_id/delete state, báo downtime/mất dữ liệu nếu có và lưu mọi failure.

**C13-14 — Đo runtime và sức chứa profile. TODO — 0/4.**
Phụ thuộc: C13-10/11. Đầu ra: workload manifest khóa trước run và `evidence/runtime-report.json`.

- [ ] Khóa dataset, câu hỏi, seed, request groups, concurrency 1/2/4, cold/warm/cache on-off, deadline và API-call cap trước đo; benchmark test không dùng để tune.
- [ ] Tối thiểu 100 HTTP gồm read-only/query/cache/busy/error cases; tối đa 10 provider attempts miễn phí cho smoke deployment, ≥6 giây spacing; dừng khi 503/429/cap, không tự resume run để làm đẹp report.
- [ ] Báo denominator đầy đủ: success/expected rejection/unexpected error/timeout, p50/p95/p99 theo nhóm, peak RSS/CPU/disk, queue/model count và token/call budget; cached/replay tách live.
- [ ] Peak app RSS ≤75% RAM VM, không OOM; query concurrency cap giữ health/UI p95 ≤1 giây, query deadline ≤30 giây. Live nhỏ chỉ là staging measurement; workload bị dừng chưa đủ mẫu không PASS.

**C13-15 — Đối soát R-01/R-02 và phạm vi release. TODO — 0/4.**
Phụ thuộc: C13-14. Đầu ra: `release-conditions.md`, decision record có tác giả/role.

- [ ] Đối chiếu nguyên workload/ngưỡng/bindings R-01/R-02; giữ historical failures và trạng thái NOT PASSED nếu chưa đủ phép đo.
- [ ] Chọn và ghi rõ: qualification theo protocol cũ, hoặc staging deployment scope riêng. Thay điều kiện public release cần owner chấp thuận cụ thể, không tự giảm SLO.
- [ ] Run mới/cũ khác profile hoặc workload không gộp denominator; proxy recovery/rollback cũ không thay kiểm process thật.
- [ ] Mọi điều kiện bắt buộc của scope Phase 13 đã xử lý; phần public còn mở chuyển rõ sang Phase 14/R-03, không gọi app là production/SLA đã đạt.

**C13-16 — Acceptance, bàn giao và cleanup. TODO — 0/4.**
Phụ thuộc: C13-01–15. Đầu ra: `acceptance.json`, vận hành/triển khai/runbook và cập nhật README/plan.

- [ ] 15 task trước đủ evidence; manifest ràng buộc source/config/model/runtime/artifact identity, xác minh hashes và link tái lập.
- [ ] Focused tests + regression phù hợp PASS, cloud smoke/restart/restore/rollback PASS; ghi chính xác skip, failed run và giới hạn chưa đo.
- [ ] Hướng dẫn owner mở URL, start/stop/redeploy, xem lỗi/quota, backup/restore/rollback; xác minh profile 0 USD và không phụ thuộc laptop backend.
- [ ] Xóa temp/build/draft không còn binding; giữ code/tests/evidence/baseline, `plan.md` ở root tracked Git; chỉ sau đó ghi Phase 13 DONE 64/64 = 100%.

#### Thứ tự thực hiện và gate đóng phase

Ưu tiên: sửa provider error UX/HTTP blocking đang ảnh hưởng local trong C13-08/04;
chuẩn bị C13-02/03/06/07/09 trong lúc owner đăng ký account; sau preflight cloud
thực hiện C13-10 → 11/12 → 13/14 → 15 → 16. Phụ thuộc account/capacity không ngăn
việc làm code/test độc lập, nhưng không được thay bằng local để đóng deployment.

| Gate | Chuẩn PASS | Task |
|---|---|---|
| G13-01 | Cloud-only profile và entitlement/0 USD được xác minh thực tế | 01/02/10 |
| G13-02 | Runtime ARM64 tái lập, một model/process, HTTP không đứng khi query chờ | 03/04/09 |
| G13-03 | HTTPS chỉ owner, secrets riêng, kiểm unauthorized không rò dữ liệu | 05 |
| G13-04 | Data và jobs đúng sau restart/reboot, queue/disk hữu hạn | 06/07 |
| G13-05 | Không cache fault, lỗi/Retry-After rõ, không vượt quota/call budget | 08 |
| G13-06 | Upload/chat VI/EN/source/feedback/delete PASS trên cloud thật | 11 |
| G13-07 | Backup độc lập, restore sạch và rollback process thật PASS | 12/13 |
| G13-08 | Runtime workload đủ mẫu, tài nguyên đạt, R-01/R-02/scope được đối soát | 14/15 |
| G13-09 | 64/64 tiêu chí, acceptance source-bound, runbook/cleanup hoàn tất | 16 |

Exit: **16/16 task, 64/64 tiêu chí, 9/9 gate PASS** trên cùng profile cloud miễn phí.
Chưa public release khi Phase 14/điều kiện public bắt buộc còn mở. Reviewer tự động
ghi đúng **Codex — Automated AI Review**, không thay chữ ký hay quyết định owner.

### Phase 14 — Production hardening

Trạng thái: **PLANNED — chưa nghiệm thu phase**. Phụ thuộc deployment đã khóa.

1. Structured logs/request ID và đo từng stage; không log secret hoặc toàn bộ
   tài liệu nhạy cảm. Theo dõi lỗi, timeout, RAM, token và quota.
2. Kiểm tra abuse/rate limit, timeout/circuit, cache isolation và giới hạn worker.
3. Chốt privacy/retention/TTL, quyền dữ liệu, delete và backup/restore manifest.
4. Hoàn thiện incident runbook, dependency policy, rollback và tài liệu public.
5. Đối soát evidence còn tương thích với release candidate; công bố giới hạn
   Free Tier và chỉ số đã đo, không tự nhận SLA hoặc production reliability 100%.

Exit: checklist vận hành/security/data đạt, điều kiện release không còn thiếu,
owner duyệt bản release cụ thể. Human approval bắt buộc phải được ghi đúng role;
AI review không được thay chữ ký con người.

## 7. Cách làm và cập nhật tiến độ

1. Mỗi lần chỉ chọn một work item có lỗi/phạm vi và exit cụ thể. Kiểm tra phần
   đã có trước khi xây mới; sửa tới khi case tái hiện và regression liên quan đạt.
2. Với task đang làm, ghi **IN PROGRESS + %**, dựa trên checklist đóng được
   (ví dụ 3/5 bước = 60%). Không gán % cho thử nghiệm chưa đủ mẫu hoặc tự tăng theo thời gian.
3. Chỉ ghi **DONE** sau khi lưu và kiểm tra evidence cùng source/config identity.
   Báo riêng scope, denominator, lỗi, phần chưa đo và dependency bên ngoài.
4. Chat verification: gộp nhiều câu còn thiếu trong một file, giữ qid/prompt/
   evidence/schema riêng, không kèm gold; nhận raw output, kiểm tra nguồn và
   replay qua ứng dụng. Không gửi lại case đã đạt nếu không có thay đổi liên quan.
5. Không tune trên test/holdout. Bộ đã exposure chỉ là regression; sửa annotation
   phải có source proof và version/overlay, không ghi đè benchmark đã freeze.
6. Không gọi API/bật billing/đổi key hoặc model chỉ để tạo report mới. Khi có
   live run, giữ ngân sách đã duyệt, spacing, deadline, failure policy và checkpoint.
7. Sau mỗi task, xóa draft/cache/temp/output dư sau khi kiểm tra references và
   bindings. Giữ source, config, tests, baseline, raw failures và audit cần tái hiện.
8. Git giữ code, roadmap, benchmark/gold, summary và hash manifest. PDF/index/
   weights/raw lớn nằm trong artifact store; không commit key hoặc môi trường ảo.

## 8. Tiêu chí hoàn thành dự án

Dự án hoàn tất khi có MVP public chạy trong giới hạn miễn phí đã thống nhất,
đủ upload/job/chat/source/feedback/delete, core answer và temporal/multihop theo
scope đạt nghiệm thu, deployment có rollback và vận hành an toàn. Reranker và
Knowledge Graph không bắt buộc khi chưa chứng minh cần thiết.

Public release phải có chỉ số chất lượng, citation/grounding/abstention,
latency/error/resource và token/quota đo đúng môi trường; thiếu số đo phải được
ghi nhận và xử lý trước khi nhận là đạt điều kiện tương ứng. Phase 7/8 quality
DONE không đồng nghĩa toàn dự án hoặc deployment đã hoàn thành.

## 9. Bằng chứng, tái hiện và lịch sử

| Nội dung | Hồ sơ chính |
|---|---|
| Phase 1/2 | [Acceptance](evaluation/results/ingestion_acceptance.json), [hướng dẫn](docs/ingestion/ingestion_acceptance.md) |
| Phase 3 | [Report dense độc lập — conditional](evaluation/results/retrieval_acceptance.json) |
| Phase 4 | [Basic RAG report](evaluation/results/basic_rag_report.json), [contract](docs/grounding/basic_rag_release.md) |
| Phase 5 | [Grounding contract](docs/architecture/grounding_contract.md), [release thresholds](configs/grounding_release.json), [audit/handoff](docs/grounding/phase5_completion.md), [manifest hiện hành](evaluation/results/phase5-acceptance-20261021/manifest.json) |
| Phase 6 | [Release manifest](evaluation/results/hybrid_release_manifest.json), [release contract](docs/retrieval/hybrid_release.md) |
| Phase 7/8 hiện hành | [Completion audit](evaluation/results/phase78-chat-quality-completion-20261013.json), [Phase 7 handoff](docs/phase7_product_handoff.md), [Phase 8 evaluation](docs/phase8_evaluation.md) |
| Phase 7 quality | [Paired review](evaluation/results/phase7-chat-quality-20261013/paired-quality-review.json) |
| Phase 8 benchmark | [Frozen v5](evaluation/results/phase8-benchmark-freeze-v5.json) |
| Release conditions chưa đạt | [Phase 7 performance review](evaluation/results/phase7-free-tier-performance-20261013/progress-review.json), [Phase 8 live exit](evaluation/results/phase8-live-remaining-20261013/exit-review.json) |
| Task và lịch sử phạm vi | [Ledger](evaluation/results/phase7-completion-20261004/completion_task_ledger.json); đọc `owner_phase78_chat_completion_amendment` cho scope mới, `active_tasks` giữ hợp đồng live cũ |
| Artifact và cleanup | [Storage/restore](docs/operations/artifact_storage.md), [cleanup receipt](evaluation/results/storage-cleanup-20261013.json) |
| Thiết kế và hardening cũ | [Architecture](docs/architecture/system_hardening.md), [Phase 3–6 hardening specification](docs/planning/release_hardening_plan.md); không mặc định mọi checklist cũ đã DONE |

Kiểm tra audit Phase 7/8 không cần mạng:

```powershell
.venv\Scripts\python.exe evaluation/results/review-phase78-chat-completion-20261013.py.txt
```

Lệnh audit tạo lại report; nếu dùng kết quả mới cho handoff, phải cập nhật binding
tương ứng. Không chạy lại phép đo/API chỉ để đọc kết quả đã lưu.

<a id="phase-7--reranker"></a>
<a id="phase-7--reranker-release-qualification"></a>
<a id="phase-7-joint-dev-feasibility--2026-10-04"></a>
### Lịch sử Phase 7 và roadmap trước khi viết lại

Các anchor cũ được giữ để liên kết từ tài liệu lịch sử không bị hỏng. Kết luận
reranker **RELEASE-BLOCKED**, các cycle thất bại và 20-task/19-gate contract vẫn
được giữ trong [đặc tả qualification](docs/reranker/phase7_task_spec.md),
[kế hoạch lịch sử](docs/reranker/phase7_completion_plan_20261004.md) và
[runbook](docs/reranker/reranker_release_runbook.md). Chỉ mở lại qualification
nếu cần bật reranker; không dùng lịch sử đó làm backlog của scope Chat đã đóng.

Toàn bộ plan trước lần viết lại này được giữ nguyên byte trong artifact store,
identity `.local_artifacts/experiment_runs/roadmap-rewrite-20261013/plan-before-rewrite.md`,
SHA-256 `fd510baec8d77d916abf852098afe8cf5a028222c4a79ad4ce27ffc7208d7f76`.
[Artifact manifest](evaluation/artifacts/manifest.json) chứa địa chỉ object nén
và checksum; xem hướng dẫn storage để restore. Không cần mang nhật ký dài vào
roadmap hiện hành hoặc xóa bằng chứng để làm trạng thái trông đẹp hơn.
