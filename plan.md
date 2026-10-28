# Cách đọc và nguyên tắc bảo toàn plan

**Theo yêu cầu chủ dự án: giữ đầy đủ bản plan trước lần viết lại ngày
28/10/2026, vì các công việc trong đó chưa hoàn thành.** Phần A bên dưới giữ
nguyên nội dung từ commit `104888d1`, không rút gọn task, bỏ lịch sử, số liệu,
bằng chứng hoặc tự chuyển việc đang làm thành DONE.

**Phần B bổ sung kế hoạch chi tiết các phase 0–14.** Quyết định phát hành hiện
hành là **local single-user**; phần cloud trong bản gốc được giữ để tra cứu,
không còn là yêu cầu triển khai. Phase 13–14 local ở Phần B thay thế phạm vi
cloud cũ, không thay thế các việc QA còn dở. Các cập nhật QA mới hơn được giữ
ở Phần B với phạm vi/bằng chứng tương ứng; số liệu ở Phần A là mốc trước sửa.

- [Phần A — toàn bộ plan gốc](#plan-goc-truoc-khi-viet-lai).
- [Phần B — tổng quan và chi tiết bổ sung](#plan-bo-sung).
- [Phase 13 local](#bo-sung-phase-13) · [Phase 14 local](#bo-sung-phase-14).
- [QA hiện hành và các việc còn mở](#bo-sung-viec-con-lai).

Các lần cập nhật sau chỉ bổ sung hoặc sửa đúng trạng thái có bằng chứng;
**không viết đè bằng bản tóm tắt, xóa phần chưa xong hoặc dọn mất nội dung cũ.**

<a id="plan-goc-truoc-khi-viet-lai"></a>
## Phần A — Plan gốc trước lần viết lại, giữ đầy đủ

# CampusAI — Kế hoạch và tiến độ

Cập nhật: **28/10/2026 · Asia/Bangkok**

Repository: [trbk07/campusai-university-rag](https://github.com/trbk07/campusai-university-rag)

## 1. Đọc nhanh

**Phase 5 đã DONE 100% trong phạm vi nghiệm thu nội bộ.** Goal đang làm là
kiểm thử và tối ưu **toàn bộ ứng dụng**, có phạm vi rộng hơn Phase 5.

| Nội dung | Trạng thái |
|---|---|
| Phase 5 — citation, grounding, abstention | **DONE · 10/10 task, 5/5 gate** |
| Web app MVP | **DONE** trong phạm vi local |
| Goal QA và tối ưu toàn ứng dụng | **ĐANG LÀM** · còn 3 nhóm việc bên dưới |
| Triển khai cloud miễn phí | **ĐANG LÀM** · 6/64 tiêu chí, 0/16 task hoàn tất |
| Public release | **CHƯA NGHIỆM THU** · còn chất lượng, vận hành và fresh holdout |

**QA-07b đã DONE:** bộ 100 câu đạt accuracy tối thiểu **95%** theo cách tính bảo thủ,
**0/100** câu bị phát hiện thông tin không có căn cứ, ngữ cảnh **15/15**.
Kết quả áp dụng cho benchmark nội bộ đã công khai exposure; không phải fresh holdout.
**Làm tiếp:** [chất lượng PDF trên bộ đại diện](#viec-con-lai).
Không review lại gold đã đạt hoặc làm lại task DONE.

Đi đến: [Việc còn lại](#viec-con-lai) · [Đã DONE](#da-done) ·
[Phase 5](#phase-5) · [Toàn bộ phase](#cac-phase) · [Cloud](#phase-13--deployment) ·
[Quy tắc cập nhật](#quy-tac-cap-nhat).

## 2. Goal hiện tại — QA và tối ưu toàn ứng dụng

Mục tiêu: tải nhiều PDF thuận tiện, hỏi đáp chính xác, xử lý nhanh, không mất
dữ liệu và có bằng chứng kiểm thử. Upload tối đa **5 PDF mỗi lượt**; người dùng
có thể thêm các lượt tiếp theo, không giới hạn cả cuộc chat chỉ có 5 PDF.

Nguồn yêu cầu: `goal.txt`. Kết quả chi tiết nằm trong
[QA audit](QA_AUDIT.md), [kịch bản kiểm thử](TEST_SCENARIOS.md),
[báo cáo hiệu năng](PERFORMANCE_REPORT.md) và [nhật ký cải tiến](IMPROVEMENT_LOG.md).

`[x]` = DONE trong phạm vi đã ghi. `[ ]` = còn phải làm hoặc còn thiếu bằng chứng.
Không tính phần trăm toàn goal bằng cách cộng các task có khối lượng khác nhau.

<a id="qa-goal-progress"></a>
<a id="viec-con-lai"></a>
### 2.1. Việc còn lại — làm theo thứ tự

1. [ ] **QA-03b / QA-07c — Chất lượng PDF trên bộ đại diện.**
   Dùng lại inventory 34 PDF. Đo **extraction ≥98%, OCR ≥90%, evidence/retrieval
   ≥95%**, không mất trang, nhầm tài liệu hoặc mất dữ liệu.
   Kết quả OCR trên fixture đã đạt chỉ áp dụng cho các fixture đó.
   **Đã xong QA-03b1:** loại lớp chữ ẩn/transparent khỏi native text, bảng và
   nguồn trích dẫn; cache v2 được kiểm tra trước khi nâng lên coverage-v3.
   PDF lỗi đã OCR lại đủ 18/18 trang; 33 PDF khác giữ nguyên extraction,
   toàn bộ 34 PDF / 268 trang giữ nguyên nguồn. CER/OCR và retrieval đại diện vẫn mở.
   **Phương án đã loại:** TableFormer + OCR từng ô quá chậm (49 giây/trang,
   cả tài liệu vượt 120 giây) và vẫn sai ký tự. Đã gỡ bản thử khỏi runtime,
   giữ bằng chứng để không thử lại cùng cách; không đổi OCR mặc định hoặc ngưỡng.
   **QA-03b2 engineering DONE:** thêm nhánh VietOCR local riêng, không cài training stack.
   Đủ 18/18 trang PDF lỗi; trang bảng khôi phục đúng **20/20 lần xuất hiện mã**
   so với 10/20 trước sửa. Bộ scan giả lập 6 dạng đạt **97,2% ký tự**;
   chưa thay cho CER và retrieval trên toàn bộ PDF thật. Mặc định vẫn giữ nguyên.
   **Làm tiếp:** kiểm liên kết mã, tín chỉ, tiên quyết theo ô/bảng và đối chiếu
   đầy đủ với nguồn trước khi chấm retrieval đại diện.
   [Bằng chứng](docs/ui/evidence/vietnamese-ocr-20261028.json).
2. [ ] **QA-08c — Tốc độ streaming AI thật.**
   Đo **p95 thời gian đến token đầu tiên ≤5 giây** trong môi trường cố định.
   Không tính heartbeat, cache hoặc trích đoạn local thành token model mới.
   **Engineering QA-08c1 đã DONE:** transport Gemini SSE, đo token thật và tiến độ
   UI; chỉ hiển thị câu trả lời sau grounding. Nhánh này **tắt mặc định**.
   Đợt đo thật 20 câu: 17 câu đúng nguồn, 3 timeout; p95 tính cả lỗi chưa đạt.
   Không bỏ mẫu lỗi hoặc chạy lại câu đã thành công để làm đẹp kết quả.
   [Bằng chứng và phạm vi](docs/ui/evidence/query-streaming-20261028.json).
3. [ ] **QA-09d — Nghiệm thu cuối goal.**
   Khi runtime cuối ổn định: chạy **3 full regressions liên tiếp** trên cùng source,
   kiểm 100% luồng/tests bắt buộc, critical E2E 100%, tổng E2E ≥98% và không có
   crash/exception chưa xử lý. Đối chiếu toàn bộ yêu cầu rồi mới đóng goal.
   Full regression mới nhất ngày 28/10: **3.149 PASS / 0 FAIL / 2 live SKIP**;
   **282 tests liên quan OCR PASS**. Lượt streaming trước đó:
   **346 tests liên quan PASS**, thêm **64 tests launcher/streaming PASS**,
   giao diện mặc định **43/43**, nhánh streaming **44/44**, JS transport **9/9**.
   Đây chưa phải chuỗi 3 full trên runtime cuối vì chất lượng PDF vẫn còn mở.
   Điều kiện toàn goal vẫn gồm không còn lỗi P0/P1 hoặc High/Critical được xác nhận;
   recovery local đã DONE không thay thế kiểm chứng chất lượng PDF/AI còn mở.

<a id="da-done"></a>
### 2.2. Task đã DONE — giữ đóng

- [x] **QA-03b2 — OCR tiếng Việt local và sửa trường mã trên scan.** Backend
  VietOCR chạy riêng, kiểm checksum/kích thước model và hủy/timeout được bằng
  process boundary hiện có. Không thay OCR mặc định hoặc training dependencies.
  Đủ 18/18 trang PDF lỗi, 70 chunks; trang 14 khôi phục đúng 20/20 lần xuất hiện
  mã so với 10/20 trước sửa. Fixture scan 6 dạng đạt 97,2% ký tự. **282 tests liên
  quan và full 3.149 tests PASS**; gate chất lượng PDF đại diện vẫn mở.
  [Bằng chứng và cách bật](docs/ui/evidence/vietnamese-ocr-20261028.json).

- [x] **QA-08c1 — Transport và đo streaming thật.** SSE được giới hạn kích thước,
  bỏ thought parts; cache/local không tạo token giả. Hủy kết nối giải phóng lượt
  xử lý, lỗi giữ nguyên quota/cooldown, không tự retry. UI chỉ nhận tiến độ cố định
  và kết quả đã kiểm grounding. Bật riêng bằng `CAMPUSAI_QUERY_STREAMING=1`;
  mặc định giữ đường trả lời đã nghiệm thu. **346 tests liên quan, 9 JS tests,
  43 kiểm tra UI mặc định và 44 kiểm tra UI streaming PASS.** Gate độ trễ QA-08c
  vẫn mở. [Bằng chứng](docs/ui/evidence/query-streaming-20261028.json).

- [x] **QA-09c2 — Recovery và bảo mật ứng dụng local.** 229 tests liên quan PASS;
  gồm quyền nguồn, upload lỗi, symlink, source bị sửa, provider lỗi/cooldown,
  hủy/xóa/retry và 10 checkpoint kill/restart thật. Giữ đủ 11 biên bản process;
  secret scan PASS. Phạm vi là các luồng local đã kiểm, không phải nghiệm thu
  public deployment hoặc chất lượng OCR. [Bằng chứng](docs/ui/evidence/request-safety-recovery-20261027.json).
- [x] **QA-09c2b — Không crash vì JSON lồng quá sâu.** Bốn API trả 400
  `invalid_json`; 20 request lỗi qua HTTP thật không làm mất lượt xử lý của câu sau.
- [x] **QA-09c2c — Chặn Host ngoài localhost.** Từ chối đủ 8 trường hợp Host
  ngoài phạm vi, sai port, thiếu hoặc lặp trước khi vào ứng dụng; 4 địa chỉ local
  hợp lệ vẫn truy cập được. Không thay đổi prompt, grounding hoặc gates Phase 5.

- [x] **QA-03c / QA-08d — PDF text 100 trang / 10 MB.** Đủ **20/20 lượt** upload
  mới trên pipeline coverage-v3, model BGE-M3 thật trên CUDA: **p95 12,25 giây**
  (ngưỡng 15 giây), tối đa 14,16 giây. Fixture **10.243.313 byte**, không chèn padding;
  giữ nguyên text 100 trang và đủ 372 chunks trong BM25/dense sau mỗi lượt.
  Đọc hình học bảng bằng tối đa 4 process/PDF; ghép theo thứ tự để giữ scope nối trang.
  **625 tests liên quan PASS**; bảng của **35 PDF / 368 trang** giống hệt trước sửa.
  Phạm vi: app local, model/OS cache đã warm, upload tuần tự; startup model đo riêng
  42,51 giây. Không suy rộng sang scan hoặc 5 PDF lớn đồng thời.
  [Bằng chứng và cách chạy lại](docs/ui/evidence/native100-performance-20261027.json).

- [x] **QA-03b1 — Không tin lớp OCR ẩn lỗi của PDF.** Giữ chữ vẽ thật (kể cả nét
  stroke), bỏ chữ vô hình khỏi text/bảng/source scope và truy vấn trang cụ thể.
  Không tái dùng cache OCR cũ của PDF lỗi; PDF không bị ảnh hưởng nâng metadata
  mà không rebuild chunks. OCR local lại đủ 18 trang; 100 kết quả AI giữ nguyên
  byte, không gọi model mới; **344 tests liên quan PASS**.
  [Bằng chứng và giới hạn](docs/ui/evidence/pdf-visibility-20261027.json).

- [x] **QA-07b / QA-07b8 — Chất lượng AI tự nhiên và nhiều lượt.** Đủ 100 câu
  (80 có đáp án, 20 thiếu dữ liệu/mơ hồ, có không dấu/lỗi gõ/hội thoại).
  Accuracy tối thiểu **95/100**; riêng câu có đáp án tối thiểu **75/80 = 93,75%**.
  Hallucination phát hiện **0/100**; ngữ cảnh **15/15**, đủ 17 trường.
  Kết hợp đối chiếu gold tự động, nguồn/trang/quote và review AI riêng cho 100 câu;
  5 câu chưa được bộ kiểm tự động chứng nhận vẫn tính vào phần chưa chắc chắn.
  793 tests liên quan PASS. Chỉ dùng **5 POSTs review**, không sinh lại predictions.
  [Bằng chứng và giới hạn](evaluation/results/full-app-natural-20261026/quality-qualification.json).
- [x] **QA-07b8b3 — Giữ đủ điều kiện trong định nghĩa danh hiệu.** Không bỏ vế
  đóng góp tích cực khi tóm tắt điều kiện; dùng trọn nguyên văn đã trích và kiểm
  lại qua grounding. Chỉ 0064 thay đổi, 99 phản hồi khác giữ nguyên; cache v37.

- [x] **QA-07b8b1 — Metric ngữ cảnh trên bộ natural100.** 15/15 hội thoại đúng,
  đủ 17 trường được yêu cầu; kiểm tự động với gold đã review, lịch sử đầu vào
  và nguồn/trang trích dẫn. Phạm vi là bộ dev đã công khai exposure.
- [x] **QA-07b8b2 — Không bỏ vế ở câu hỏi học kỳ của nhiều học phần.** Mỗi môn
  phải có mã/tên và học kỳ nhất quán trong toàn tài liệu đã chọn; thiếu hoặc
  mâu thuẫn một môn thì không tự suy ra đáp án. Cache cũ bị vô hiệu hóa qua v36.
  [Bằng chứng hai task](evaluation/results/full-app-natural-20261026/context-quality.json).
- [x] **QA-09c2a — Sửa catalog làm validator Phase 7 lỗi.** Khóa đường dẫn đã khớp
  identity tương đối trong repo; xác minh lại đủ 8.868.567 byte của artifact gốc.
  Thêm kiểm tra toàn catalog để ngăn lỗi lặp; 54 tests liên quan PASS.

- [x] **QA-07b8a — Sửa 5 ca từ chối sai cuối của natural100.** Ngày/hạn từ thông báo
  đúng đợt/năm; điều kiện điểm từ đúng danh hiệu; tên và tín chỉ từ cột bảng nguồn.
  Đã kiểm lại đủ 100 ca trên cùng index; 90 phản hồi công khai giữ nguyên, 5 ca sửa
  đúng và 5 ca vốn đúng chuyển sang local. 721 tests PASS. Tra cứu mới không khớp
  ca nào trong 400 ca Phase 5 đã nghiệm thu; giữ đóng Phase 5 nội bộ.
  [Bằng chứng](evaluation/results/full-app-natural-20261026/remaining-five.json).

- [x] **QA-01 — Đóng gói và khởi động từ Git.** Đã sửa lỗi thiếu module;
  bản export có 114 app tests PASS.
- [x] **QA-02 — Phase 5 nội bộ.** 400/400 kết quả, 5/5 gates PASS;
  kết quả hồi quy trên code mới giữ nguyên.
- [x] **QA-04 — PDF trộn text và scan.** Nhận diện phần ảnh chứa chữ ngay
  dưới tiêu đề native; readiness và cache dùng coverage-v2.
- [x] **QA-05 — OCR từ chi tiết tài liệu.** Không cần upload lại;
  retry, cancel, quyền nguồn và giới hạn 50 trang / 120 giây đã kiểm chứng.
- [x] **QA-06 — Tương thích job cũ.** Đọc identity cũ/mới, giữ lịch sử;
  từ chối dữ liệu identity giả mạo.
- [x] **QA-10 — Hủy OCR và tiến độ.** Dừng worker, không chạy tiếp trang sau;
  tiến độ không lùi hoặc báo 100% trước khi index xong.
- [x] **QA-11 — OCR Việt/Anh trong process riêng.** Có deadline/cancel,
  không đổi OpenMP của app; 6 layout fixture đạt 97,54% ký tự.
- [x] **QA-12 — Tối ưu đọc thư viện và metadata.** Cache có invalidation,
  chỉ đọc scope đã chọn; quyền và thao tác xóa/retry vẫn kiểm tra mới.
- [x] **QA-13 — Nội dung ảnh trên cùng trang text.** Giữ chữ/style native,
  thứ tự cột, không lặp facts hay lấy chữ bị che; đã kiểm cả hai backend OCR.
  Fixture Việt đạt 98,44%. Reindex 5 tài liệu / 268 trang trong 40,65 giây,
  giữ nguyên 7 PDF gốc và lịch sử job.

### 2.3. Chi tiết các mốc đã DONE — lịch sử

Các số liệu bên dưới mô tả từng mốc cũ, không thay thế trạng thái hiện tại ở mục 1–2.2.
Giữ đóng các task này; chỉ làm phần còn thiếu ở mục 2.1.

- [x] **QA-07b6a — Giữ phạm vi học kỳ khi đọc bảng tiếp trang.** Sửa mất 17 dòng
  và gán nhầm dòng tổng thành “Semester 29”. Giữ đủ 111/111 dòng bảng của PDF
  3 trang, kiểm hình học cột trước khi kế thừa tiêu đề, giữ marker khi chia chunk.
  Full regression trước guard đóng phạm vi cuối: 2.836 PASS / 2 live SKIP;
  sau guard cuối: 119 tests liên quan PASS. Không tính thành full run cuối goal.
  [Bằng chứng](evaluation/results/full-app-natural-20261026/source-scope.json).
- [x] **QA-07b6b — Nghiệm thu 19 ca trên nguồn đã sửa.** Index thử chỉ thay
  tài liệu bị ảnh hưởng; 14 tài liệu khác và baseline giữ nguyên byte. Đã chọn
  19 đầu vào cùng tài liệu; cả 19 truy hồi được cột tín chỉ có tiêu đề rõ ràng.
  Hiện 19/19 ca khớp các trường học kỳ/tín chỉ/đơn vị/tên học phần trong gold và
  document/page đã review; quote hợp lệ, 0 ca từ chối sai. Chỉ đóng nhóm 19 ca;
  tại mốc đó QA-07b còn mở. Hiện QA-07b đã DONE theo nghiệm thu 100 ca ở mục 2.2.
- [x] **QA-07b6b1 — Citation và nhãn học kỳ.** Ràng đúng hàng/môn/học kỳ,
  giữ phạm vi so sánh, kiểm đủ nhóm đơn vị giảng dạy; phân biệt `Semester8`
  với số tín chỉ và nhãn dòng tổng. Cache `grounding-v32` qua restart đã kiểm.
  399 tests liên quan và 244 tests chéo phase PASS. Thêm đúng 11 calls thật;
  reprocess 19/19 ca dùng captures khớp HTTP, 0 pending, 5 ca từ chối sai được
  sửa, 0 ca vốn trả lời được bị từ chối mới. Năm ca Phase 5 có thể bị ảnh hưởng
  được reprocess và giữ nguyên public/internal; 395 ca còn lại không vào nhánh
  mới. [Bằng chứng](evaluation/results/full-app-natural-20261026/semester-citations.json).
- [x] **QA-07b6b2a — Tham chiếu tài liệu đang chọn.** Khi đã chọn đúng một PDF,
  “bản chương trình này/liên kết” không tự biến thành yêu cầu chọn phiên bản.
  Giữ các kiểm tra năm, khóa, phiên bản, so sánh và hiệu lực. Citation “học bên…”
  phải kiểm đủ nhóm môn; cache `grounding-v33`. 456 tests PASS, thêm 2 calls thật;
  reprocess 19/19 ca, sửa `0088`, giữ nguyên 15 kết quả đã trả lời được.
  Lỗi citation thừa của `0092` tại mốc này đã được đóng ở QA-07b6b2.
  [Bằng chứng](evaluation/results/full-app-natural-20261026/selected-reference.json).
- [x] **QA-07b6b2 — Tra cứu đơn vị và học phần từ bảng nguồn.** Sửa đủ
  `0085/0090/0092`. Đọc bảng của toàn PDF đã chọn, suy viết tắt từ tên nguồn và
  chỉ dùng định danh duy nhất; kiểm nhóm đơn vị đầy đủ, ô tín chỉ và marker học kỳ.
  Thiếu/mâu thuẫn/điều kiện hoặc nhiều chủ thể thì không tự trả lời. Cache
  `grounding-v34` qua restart đã kiểm; đổi index giữa lúc tra cứu không phát/cache
  kết quả cũ. 607 tests PASS; 19 ca hoàn tất gồm 14 local
  và 5 captures khớp HTTP, 0 calls mới, 0 ca đã trả lời được bị từ chối mới.
  Cả 400 ca Phase 5 không vào nhánh tra cứu mới, không mở lại nghiệm thu nội bộ.
  [Bằng chứng](evaluation/results/full-app-natural-20261026/curriculum-lookup.json).
- [x] **QA-07b7a — Kiểm chứng capture khi phần corpus khác thay đổi.** Adapter
  offline chỉ dùng lại khi model/config/user input/HTTP body khớp, toàn bộ BM25
  và dense của các tài liệu được chọn giữ nguyên byte, manifest còn nguyên.
  Corpus/model/scope thiếu bằng chứng thì từ chối; cơ chế mặc định vẫn giữ
  strict whole-manifest. 107 tests PASS, không sửa runtime hoặc gates Phase 5.
- [x] **QA-07b7b — Đủ 100 ca trên index hiện hành.** 100/100 hoàn tất,
  64 captures được kiểm chứng (56 qua proof của scope), 36 local; giữ nguyên 97
  ca đã xong, chỉ bổ sung 3 ca thiếu. Thêm 4 POSTs thật: 3 phản hồi thành công,
  1 timeout được giữ nguyên; project/key thứ hai hoàn tất hai ca còn lại.
  100 schema và 79 quote-source bindings hợp lệ; chưa phải điểm semantic quality.
  [Bằng chứng](evaluation/results/full-app-natural-20261026/current100.json).
- [x] **QA-07b8 — Năm ca từ chối sai và chấm chất lượng đầy đủ — DONE.**
  `0111/0112/0128`: ngày/giờ tuyển sinh thạc sĩ; `0121`: điều kiện học phần dưới
  C+ của danh hiệu Xuất sắc; `0160`: tên/tín chỉ EMA3143. Đối chiếu raw prediction
  với nguồn trước khi sửa. Đã sửa đủ và nghiệm thu accuracy/hallucination/context
  trên 100 ca; xem bằng chứng mới nhất ở mục 2.2, không mở lại task này.
- [x] **QA-07b5 — Tổng tín chỉ theo học kỳ.** Tra cứu dòng tổng gắn với
  nhãn học kỳ trong cùng bảng nguồn; không cộng các môn tự chọn. 369 tests liên
  quan PASS, có kiểm tra dòng tổng mâu thuẫn, đổi cột, đổi phạm vi và cache qua
  restart (`grounding-v31`). Đủ 100/100 ca, 0 pending; 5 ca từng từ chối sai nay
  trả lời đúng, 1 ca vốn đúng chuyển sang local; 94 đầu ra public còn lại giữ nguyên.
  Còn 15 ca từ chối sai thuộc QA-07b. Không gọi model mới; 69 captures khớp HTTP,
  31 ca local. Cả 400 câu Phase 5 không khớp intent mới; không mở lại nghiệm thu.
  [Bằng chứng](evaluation/results/full-app-natural-20261026/semester-totals.json).
- [x] **QA-07b4a — Tra cứu một môn từ bảng nguồn.** Xác định duy nhất tên/mã môn,
  đọc đúng cột tín chỉ và đủ mã tiên quyết; không suy từ giờ học, dữ liệu thiếu,
  điều kiện OR hoặc hàng mâu thuẫn. Ba ca nhiều lượt lỗi đã trả đúng bằng chứng;
  thêm một ca vốn đúng chuyển sang xử lý local, không gọi model.
- [x] **QA-07b4b — Xử lý cache từ chối cũ.** Version `grounding-v30` bỏ qua kết quả
  cũ; kiểm thử SQLite xác nhận trả đáp án đúng ở lượt đầu và cache đúng sau restart.
- [x] **QA-07b4c — Hồi quy phần tra cứu và các phase liên quan.** 740 tests PASS;
  lượt tương thích đã ghi nhận 400/400 ca Phase 5, 0 pending, đầu ra public,
  đáp án/claims nội bộ giữ nguyên. Chỉ số cosine/chấm điểm truy hồi có sai khác
  số học nhỏ; không gọi đó là dữ liệu raw giống từng byte. Không mở lại nghiệm thu Phase 5.
- [x] **QA-07b4d — Nghiệm thu bộ chọn đoạn nguồn mới.** Chặn khớp nhầm một
  phần tiêu đề, giữ thứ tự từ Việt/không dấu; 217 focused PASS. Chỉ gọi thêm đúng
  3 đầu vào đổi: 3/3 phản hồi thật thành công và có nguồn. Pipeline hiện hành đủ
  100/100 ca, 0 pending, dùng 75 captures thật khớp HTTP và 25 ca local. Còn 20
  ca từ chối sai thuộc việc QA-07b đang mở; không coi đây là PASS chất lượng toàn bộ.
  [Bằng chứng và test](evaluation/results/full-app-natural-20261026/course-lookup.json).

| Đã DONE | Kết quả và phạm vi |
|---|---|
| QA-03a — Đo/sửa OCR và index, bật GPU | Đối sánh CPU/CUDA trên 5 PDF / 104 trang; có số đo reindex thực tế. Chưa thay phép đo fresh upload 100 trang / 10 MB. |
| QA-07a — Kiểm kê PDF | 34 SHA khác nhau; đã kiểm số trang và thứ tự trang vật lý. Chưa đồng nghĩa đạt mọi ngưỡng chất lượng PDF. |
| QA-07b1 — Giữ chủ đề của câu hỏi lược chủ thể | DONE · 15/15 ca đã review, trước sửa 7/15. Hybrid truy hồi đủ các trang gold ở top 8: 14/15 → 15/15; chưa phải accuracy đáp án AI. [Bằng chứng](docs/ui/evidence/natural-context-20261026.json). |
| QA-07b2 — Chạy bộ 100 câu tự nhiên thật | DONE · 80 câu có đáp án, 20 negative, gồm 15 nhiều lượt và 10 lỗi gõ. Baseline có 79 phản hồi JSON model thật, 21 ca local, không lỗi provider; chất lượng còn FAIL. [Baseline](evaluation/results/full-app-natural-20261026/diagnostic-score.json). |
| QA-07b3 — Giữ đủ điều kiện sau tiêu đề nguồn | DONE · 531 tests liên quan PASS; gọi mới đúng 3 ca đổi payload, dùng lại 76 captures khớp HTTP. Cả 3 ca trả đáp án có nguồn; 100/100 ca pipeline đầy đủ, tổng 82 POSTs thật. Không hạ gate. [Kết quả](evaluation/results/full-app-natural-20261026/repair.json). |
| QA-08a — API thường, 20 người đồng thời | 400/400 HTTP 200; p95 tổng 0,478 giây, thư viện 0,429 giây, fact PDF 0,497 giây trên workload local 7 tài liệu / 17 jobs. |
| QA-08b — Web Vitals trong lab | 9/9 sessions đạt trên desktop/tablet/mobile; max LCP 308 ms, INP 104 ms, CLS 0,0109. |
| QA-09a — Unit/integration đã chốt | Bản 25/10: 2.718 full PASS / 2 opt-in live SKIP. Các lượt focused sau đó: 429, 531, 740 PASS; bộ chọn đoạn nguồn mới: 217 PASS. Không cộng các lượt chồng lấn thành số test riêng biệt. Chuỗi full cuối thực hiện tại QA-09d. |
| QA-09b — Luồng browser cốt lõi | 43/43 PASS; gồm hai lượt thêm 5 PDF, chat, nguồn, xóa, OCR, responsive và accessibility. |
| QA-09c1 — Recovery đã có | Busy/quota/503/timeout, hủy/retry OCR, đọc nguồn khi provider lỗi và worker không đọc stdin lớn. |

Bằng chứng: [hybrid coverage](docs/ui/evidence/hybrid-coverage-20261025.json),
[full regression](docs/ui/evidence/hybrid-final-full-20261025.xml),
[browser](docs/ui/evidence/hybrid-final-ui-20261025/browser-results.json),
[OCR isolation](docs/ui/evidence/ocr-isolation-20261025.json),
[OCR progress](docs/ui/evidence/ocr-evaluation-20261025.json),
[inventory PDF](docs/ui/evidence/phase5-v27-20261024/pdf-parser.json).
Số đo mới nhất ở trên được tạo ngày **25/10/2026**, trong phạm vi môi trường đã ghi.

<a id="phase-5"></a>
## 3. Phase 5 — Đã hoàn tất

**DONE 100% · 10/10 task · 5/5 gate · nghiệm thu nội bộ ngày 25/10/2026.**

| Task | Nội dung | Trạng thái |
|---|---|---|
| P5-01 | Audit baseline, contract và bằng chứng | DONE |
| P5-02 | Schema đầu ra public/internal | DONE |
| P5-03 | Citation, trang, quote và provenance | DONE |
| P5-04 | Grounding từng claim và nội dung hiển thị | DONE |
| P5-05 | Abstention và phạm vi kiểm tra nguồn | DONE |
| P5-06 | Benchmark, review và phép chấm | DONE |
| P5-07 | Confidence, calibration và cache version | DONE |
| P5-08 | Qualification runtime và regression | DONE |
| P5-09 | Kiểm tra lại report và 5 quality gates | DONE |
| P5-10 | Bàn giao, đồng bộ tài liệu và cleanup | DONE |

Kết quả chốt trên producer `a21a4cd5` / `grounding-v29`:

- **400/400** ca: dev 120, test 130, holdout 150; kiểm tra vật lý độc lập PASS.
- Grounding, citation và abstention precision/recall **100%**; leakage **0**;
  reason accuracy **97,67%**; holdout ECE/Brier/risk **0**.
- **3 full regressions liên tiếp**, mỗi lượt **2.663 PASS / 2 live SKIP**.
- Tái sử dụng 426 phản hồi Gemini thật khi đầu vào HTTP khớp chính xác,
  rồi chạy lại pipeline hiện hành; không gắn nhãn inference mới.

Phạm vi này dùng benchmark đã review, công khai lịch sử exposure và được owner
duyệt. **Fresh holdout cho public release vẫn còn mở.** Goal QA toàn ứng dụng,
SLO web/PDF/OCR và cloud có điều kiện riêng.

Hồ sơ: [closure](evaluation/results/phase5-mixed-absence-20261024/phase5-closure.json),
[bàn giao](docs/grounding/phase5_completion.md),
[release gates](docs/grounding/grounding_release_gates.md),
[ngưỡng chất lượng](configs/grounding_release.json),
[đặc tả và lịch sử task](docs/planning/phase_details.md#phase-5).

<a id="cac-phase"></a>
## 4. Roadmap toàn dự án

Trạng thái chỉ áp dụng cho phạm vi đã nghiệm thu. `IMPLEMENTED` nghĩa là đã có
code nhưng chưa đủ bằng chứng đóng toàn bộ nghiệm thu độc lập.

| Phase | Nội dung | Trạng thái | Hồ sơ |
|---|---|---|---|
| 0 | Tên dự án, package, cấu hình nền | IMPLEMENTED | [Chi tiết](docs/planning/phase_details.md#phase-0) |
| 1 | Ingestion và lifecycle PDF | DONE | [Acceptance Phase 1/2](evaluation/results/ingestion_acceptance.json) |
| 2 | Chunking, bảng, provenance | DONE | [Acceptance Phase 1/2](docs/ingestion/ingestion_acceptance.md) |
| 3 | Embedding và dense index | IMPLEMENTED · report độc lập còn CONDITIONAL | [Dense report](evaluation/results/retrieval_acceptance.json) |
| 4 | Basic RAG, context, cache | DONE · offline contract | [Report](evaluation/results/basic_rag_report.json) |
| 5 | Citation, grounding, abstention | **DONE · 100% nội bộ** | [Kết quả](#phase-5) |
| 6 | BM25 + dense + RRF | DONE · release lịch sử | [Manifest](evaluation/results/hybrid_release_manifest.json) |
| 7 | Core product quality | DONE · scope Chat, 68/68 ca | [Handoff](docs/phase7_product_handoff.md) |
| 8 | Benchmark và evaluation | DONE · scope Chat, 300/300 ca | [Evaluation](docs/phase8_evaluation.md) |
| 9 | Temporal RAG | DONE · 6/6 task, 5/5 gate | [Handoff](docs/phase9_temporal_handoff.md) |
| 10 | Multi-document / multi-hop | DONE · 5/5 task, 5/5 gate | [Handoff](docs/phase10_multi_hop_handoff.md) |
| 11 | Knowledge Graph có nguồn | DONE · 5/5 task, 5/5 gate; mặc định OFF | [Chi tiết](docs/planning/phase_details.md#phase-11) |
| 12 | Web app MVP | DONE · local MVP; goal QA mở riêng | [UI](docs/ui/phase12-ui.md) |
| 13 | Deployment cloud miễn phí | ĐANG LÀM · 6/64 tiêu chí (9,4%) | [Kế hoạch cloud](#phase-13--deployment) |
| 14 | Production hardening | CHƯA NGHIỆM THU | [Phạm vi](docs/planning/phase_details.md#phase-14) |

<a id="phase-13--deployment"></a>
## 5. Cloud và điều kiện public release

**Phase 13: 6/64 tiêu chí đạt, 0/16 task DONE.** Ưu tiên hiện tại vẫn là hoàn tất
goal QA local. Cloud cần xác minh tài khoản, entitlement, quota và capacity thật;
kết quả local không thay cho nghiệm thu cloud.

| Nhóm task | Công việc | Trạng thái |
|---|---|---|
| C13-01 | Khóa profile và xác minh miễn phí | 2/4 tiêu chí |
| C13-02 | Runtime và cấu hình triển khai | 1/4 tiêu chí |
| C13-08 | Provider recovery và persistent budget | 3/4 tiêu chí |
| C13-03–07, 09 | Build/runtime, workers, HTTPS/quyền, dữ liệu/jobs, health | Còn phải nghiệm thu theo từng task |
| C13-10–16 | Deploy thật, cloud smoke, backup/restore, rollback, capacity, release, bàn giao | Còn phải nghiệm thu |

Thứ tự: chuẩn bị runtime/state/health → xác minh account/profile → deploy thật →
smoke và restore/rollback → đo capacity → đối soát release → bàn giao.
Đích đóng Phase 13: **16/16 task, 64/64 tiêu chí, 9/9 gate** trên profile cloud miễn phí.
[Checklist đầy đủ](docs/planning/phase_details.md#phase-13) ·
[quyết định profile](docs/deployment/phase13/profile-decision.md).

| Điều kiện release còn mở | Trạng thái / yêu cầu |
|---|---|
| R-01 — Performance workload thật của Phase 7 | DEFERRED · NOT PASSED; giữ protocol và ngưỡng gốc |
| R-02 — Latency, availability và native format của Phase 8 | DEFERRED · NOT PASSED; Chat/replay không thay số đo API thật |
| R-03 — Public deployment và vận hành | Phase 13/14; cần quyền dữ liệu, bảo mật, quota, recovery và số đo trên môi trường triển khai |
| Fresh holdout Phase 5 | Cần bộ chưa exposure trước public release; không thay trạng thái DONE nội bộ |

Giữ Free Tier, không tự bật billing hoặc dịch vụ trả phí. Không gộp số đo từ
nhiều môi trường/source để tuyên bố SLO; công bố đúng giới hạn và lỗi đã quan sát.

<a id="quy-tac-cap-nhat"></a>
## 6. Cách làm và cập nhật plan

1. Chỉ chọn **một task còn mở**; ghi rõ lỗi/khoảng trống, việc cần làm và điều kiện đóng.
2. Khi đủ bằng chứng, tick `[x]` hoặc ghi DONE ngay, kèm kết quả và đường dẫn bằng chứng.
3. **Giữ task DONE đóng.** Chỉ kiểm tra lại khi code/phụ thuộc liên quan thay đổi,
   có lỗi mới, dữ liệu/môi trường vượt phạm vi đã đo, hoặc đến nghiệm thu cuối bắt buộc.
   Ghi lý do trước khi mở lại.
4. Sửa tài liệu/plan không kích hoạt full regression, 400 ca hay benchmark PDF.
   Sửa code chạy focused tests liên quan; giữ kết quả của phần không bị ảnh hưởng.
5. Dùng lại dữ liệu, review và captures hợp lệ. Không tạo lại benchmark đã đạt,
   tune trên test/holdout hoặc gọi lại ca thành công khi không có lý do liên quan.
6. Ba full regressions cuối chạy khi runtime ổn định; không bắt đầu lại sau mỗi
   cập nhật tiến độ. Không tính replay/cache/SKIP thành inference hoặc live PASS.
7. Dọn file tạm không còn dùng sau khi kiểm tra references/bindings; giữ source,
   cấu hình, tests, baseline, lỗi lịch sử và bằng chứng tái hiện.
8. Giữ `plan.md` ở root và tracked Git. Commit/push qua `origin` tới repo CampusAI
   ở đầu tài liệu; không push sang repo financial cũ.
9. Chủ dự án cho phép tự chọn phương án và tiếp tục các thao tác đã ủy quyền;
   không chờ xác nhận lại cho quyết định thông thường. Giữ giới hạn dữ liệu,
   chi phí và bằng chứng nghiệm thu đã thống nhất.

## 7. Tra cứu đặc tả và lịch sử

Plan này là nguồn **trạng thái hiện hành và thứ tự công việc**.
[Đặc tả phase và lịch sử nghiệm thu](docs/planning/phase_details.md) giữ nguyên
ID task, contract, ngưỡng, phụ thuộc và bằng chứng cũ để tra cứu. Các mốc
IN PROGRESS/BLOCKED trong lịch sử không thay trạng thái DONE đã chốt ở đây.

<a id="ưu-tiên-hiện-tại--hỏi-liên-tục-không-quá-tải-chi-phí-dịch-vụ-0"></a>
Goal continuity local ngày 16/10 đã đóng trong phạm vi đã đo:
[hồ sơ](docs/deployment/phase13/free-continuity-goal.md).
Không đồng nghĩa provider miễn phí vô hạn hoặc đã đạt cloud SLO.

<a id="phase-7--hoàn-thiện-chất-lượng-sản-phẩm-phạm-vi-tinh-gọn"></a>
<a id="phase-7--reranker"></a>
<a id="phase-7--reranker-release-qualification"></a>
<a id="phase-7-joint-dev-feasibility--2026-10-04"></a>
Phase 7 hiện hành là scope chất lượng Chat đã đóng. Optional reranker giữ OFF;
qualification cũ vẫn có trạng thái RELEASE-BLOCKED, chỉ mở nếu cần bật reranker.
[Đặc tả lịch sử](docs/reranker/phase7_task_spec.md) ·
[artifact storage/restore](docs/operations/artifact_storage.md).


---

<a id="plan-bo-sung"></a>
## Phần B — Bổ sung chi tiết và quyết định local release

Phần A được giữ nguyên để tiếp tục các việc chưa hoàn thành. Phần này
bổ sung nội dung từng phase và ghi quyết định mới; không xóa hay tự đóng
công việc còn mở trong bản gốc.

# CampusAI — Roadmap toàn dự án và local release

Cập nhật: **28/10/2026 · Asia/Bangkok**
Repository: [trbk07/campusai-university-rag](https://github.com/trbk07/campusai-university-rag)

## 1. Quyết định hiện hành và cách đọc

**Đích phát hành: bản local, chạy trên máy người dùng, một người dùng trên mỗi
instance.** Quyết định của chủ dự án ngày 28/10/2026 thay thế mục tiêu triển khai
cloud trước đây. Phase 13 chuẩn bị bản local có thể cài đặt/tái tạo; Phase 14
nghiệm thu và phát hành bản đó. Oracle, VM, ARM64, domain, HTTPS công khai,
Tailscale và hạ tầng đa người dùng không còn là điều kiện hoàn thành dự án.

**Local không có nghĩa là AI hoàn toàn offline.** UI, PDF, index, OCR và state
chạy/lưu trên máy. Profile Gemini hiện có vẫn cần Internet và credential của
người dùng; câu hỏi, lịch sử và đoạn nguồn theo payload thực tế có thể được gửi
đến provider. Không có credential/provider khả dụng thì chỉ công bố đúng các
chức năng local đã kiểm chứng, không hứa vẫn sinh được đáp án AI.

Các phase 0–12 được khôi phục dưới đây để thấy đủ quá trình đã làm. **DONE theo
phạm vi từng phase không đồng nghĩa đã nghiệm thu bản release cuối.** Không mở
lại phase đã đóng chỉ để tạo báo cáo mới. Riêng Phase 0/3 đã có implementation;
hồ sơ cũ chưa xác nhận mọi điều kiện nghiệm thu độc lập, nên giữ rõ giới hạn đó.

- `[x]` / **DONE**: đã hoàn tất trong phạm vi ghi kèm.
- `[ ]`: còn thiếu công việc hoặc bằng chứng; có code không tự trở thành DONE.
- Số đo lịch sử chỉ áp dụng source/config/data/máy đã ghi, không tự chứng nhận RC mới.

Đi đến: [Tổng quan](#bo-sung-cac-phase) · [Phase 0–12](#bo-sung-phase-da-lam) ·
[Việc QA còn lại](#bo-sung-viec-con-lai) · [Phase 13](#bo-sung-phase-13) ·
[Phase 14](#bo-sung-phase-14) · [Quy tắc cập nhật](#bo-sung-quy-tac-cap-nhat).

<a id="bo-sung-cac-phase"></a>
## 2. Tổng quan đủ 15 phase

| Phase | Mục tiêu | Trạng thái / phạm vi |
|---|---|---|
| 0 | Nền tảng, tên dự án, package, contract | Đã triển khai; không có nghiệm thu production riêng |
| 1 | Ingestion và lifecycle tài liệu | DONE · acceptance Phase 1/2 |
| 2 | Chunking, bảng, provenance | DONE · acceptance Phase 1/2 |
| 3 | Embedding và dense index | Đã triển khai; dense report độc lập lịch sử còn CONDITIONAL |
| 4 | Basic RAG, context và cache | DONE · offline contract |
| 5 | Citation, grounding, abstention | DONE · 10/10 task, 5/5 gate, nghiệm thu nội bộ |
| 6 | BM25 + dense + RRF | DONE · release lịch sử |
| 7 | Chất lượng sản phẩm cốt lõi | DONE · scope Chat-quality, 68/68 ca |
| 8 | Benchmark và evaluation | DONE · scope Chat-quality, 300/300 ca |
| 9 | Temporal RAG | DONE · 6/6 task, 5/5 gate |
| 10 | Multi-document / multi-hop | DONE · 5/5 task, 5/5 gate |
| 11 | Chỉ mục quan hệ học phần có nguồn | DONE · 5/5 task, 5/5 gate; mặc định OFF |
| 12 | Web app MVP | DONE · local single-user; QA mở rộng theo dõi riêng |
| 13 | Đóng gói và khả năng chạy local | ĐANG CHUẨN BỊ · kế hoạch mới, chưa nghiệm thu toàn phase |
| 14 | Hardening, nghiệm thu và local release | CHƯA NGHIỆM THU · phụ thuộc RC Phase 13 |

Luồng chính: **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 12 → 13 → 14**.
Phase 11 là nhánh tùy chọn đã hoàn thành; không bắt bật graph/reranker để release.
QA mở rộng của ứng dụng là đầu vào cho Phase 13/14, không phải một phase mới.

<a id="bo-sung-phase-da-lam"></a>
## 3. Các phase đã làm — mục tiêu, kết quả và giới hạn

<a id="bo-sung-phase-0"></a>
### Phase 0 — Nền tảng dự án

Đã triển khai tên CampusAI, package `campusai`, cấu hình, README, biến môi trường,
public import contract và baseline. Mục tiêu là thống nhất cấu trúc và cách chạy,
không tự nhận đây là nghiệm thu release. Repository chính dùng `origin` CampusAI;
remote financial lịch sử chỉ fetch. [Đặc tả](docs/planning/phase_details.md#phase-0).

#### Kế hoạch chi tiết Phase 0

Phụ thuộc: không có; cung cấp nền cho mọi phase sau.

| Hạng mục | Nội dung và đầu ra | Trạng thái / điều kiện |
|---|---|---|
| P0-A | Tên sản phẩm, namespace `campusai`, cấu trúc source/tests/config/docs | Đã triển khai; bảo toàn import contract |
| P0-B | Cấu hình mẫu, biến môi trường, lock và cách khởi động | Đã triển khai; cài sạch được kiểm ở L13-04 |
| P0-C | Repository chính, baseline và quy tắc quản lý artifact/secret | Đã triển khai; không push repo financial, không commit credential |
| P0-D | Roadmap, contract và hướng dẫn đóng góp | Giữ `plan.md` tracked; mọi phần cũ phải còn tra cứu được |

Đầu ra: nền dự án nhất quán và tài liệu chạy/tái hiện. Không mở một đợt
nghiệm thu production riêng cho Phase 0; khoảng trống release xử lý ở 13/14.

<a id="bo-sung-phase-1"></a>
### Phase 1 — Ingestion và lifecycle PDF · DONE

Tiếp nhận/kiểm tra PDF, nhận diện tài liệu, metadata, xử lý nền, lưu trữ và quản
lý vòng đời upload/retry/delete. Kiểm soát file lỗi, đường dẫn và nguồn; scan cần
OCR có giới hạn thay vì âm thầm coi trang rỗng là thành công. Phase 1/2 đã đạt
**16/16 tiêu chí acceptance chung**.
[Acceptance](evaluation/results/ingestion_acceptance.json) ·
[Contract](docs/planning/phase_details.md#phase-1).

#### Kế hoạch chi tiết Phase 1

Phụ thuộc: Phase 0. Giữ DONE cho acceptance gốc; QA mở rộng không xóa kết quả cũ.

| Hạng mục | Công việc / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| P1-A | Nhận file, kiểm loại/kích thước/đường dẫn, tính identity/hash | File không hợp lệ bị từ chối rõ, không thoát thư mục cho phép |
| P1-B | Trích text/metadata theo trang, phân loại native/scan/mixed | Không tự báo scan rỗng là tài liệu có evidence sẵn sàng |
| P1-C | Job xử lý, trạng thái, retry/cancel và persistence | Job/data nhất quán qua restart; retry không nhân bản source |
| P1-D | Registry, xóa tài liệu và thu hồi derived data | Không còn nguồn/index/cache trái quyền sau xóa |
| P1-E | Acceptance source-bound và hướng dẫn tái hiện | Giữ report Phase 1/2; chỉ kiểm lại phần liên quan khi runtime đổi |

Đầu ra bàn giao: PDF có identity, page metadata, job/state và dữ liệu extraction.
OCR thật trên bộ đại diện còn được nghiệm thu tại QA-03b/QA-07c, không tự coi DONE.

<a id="bo-sung-phase-2"></a>
### Phase 2 — Chunking, bảng và provenance · DONE

Chia nội dung theo cấu trúc, kế thừa heading, giới hạn chunk/overlap, giữ header,
hàng/ô bảng và tài liệu/trang nguồn để citation tái hiện được. Có fixture cho
section, bảng và provenance. OCR/bảng mới của QA không tự thay nghiệm thu gốc.
[Hồ sơ Phase 1/2](docs/ingestion/ingestion_acceptance.md) ·
[Đặc tả](docs/planning/phase_details.md#phase-2).

#### Kế hoạch chi tiết Phase 2

Phụ thuộc: extraction Phase 1; cung cấp evidence cho embedding và grounding.

| Hạng mục | Công việc / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| P2-A | Golden fixtures cho section, heading và thứ tự nội dung | Section inheritance đúng nguồn, không trộn tài liệu |
| P2-B | Chia chunk theo cấu trúc, giới hạn kích thước/overlap | Không mất fact tại biên chunk; không nới budget âm thầm |
| P2-C | Serialization bảng với header/hàng/ô, nối trang có căn cứ | Giữ quan hệ cột/hàng, không ghép ô tạo fact mới |
| P2-D | Provenance tài liệu/trang/span/table identity | Citation truy ngược được về source thật |
| P2-E | Version schema/cache và regression theo thay đổi | Derived data stale không được tái sử dụng như evidence hiện hành |

Đầu ra: chunks và bảng có provenance ổn định. Hạng mục OCR table mới có bằng
chứng engineering riêng; không thay cho toàn bộ ngưỡng chất lượng PDF đại diện.

<a id="bo-sung-phase-3"></a>
### Phase 3 — Embedding và vector search · ĐÃ TRIỂN KHAI

Có embedding multilingual, dense index bền qua restart, kiểm tra model/corpus
identity và từ chối index hỏng hoặc sai phiên bản; hash provider dành cho test.
**Report dense độc lập cũ vẫn CONDITIONAL**: corpus nhỏ và negative chưa được
calibrate đầy đủ; không đổi nhãn artifact cũ thành PASS. Pipeline ứng dụng đã
phát triển tiếp qua hybrid và QA, nhưng đó là bằng chứng theo scope khác.
[Report gốc](evaluation/results/retrieval_acceptance.json) ·
[Đặc tả](docs/planning/phase_details.md#phase-3).

#### Kế hoạch chi tiết Phase 3

Phụ thuộc: chunks/provenance Phase 2. Phân biệt việc đã triển khai với các
điều kiện chưa đạt trong dense acceptance độc lập cũ.

| Hạng mục | Công việc / đầu ra | Trạng thái / kiểm tra cần thiết |
|---|---|---|
| P3-A | Encoder multilingual, recipe/version và batching | Đã triển khai; hash provider chỉ dành cho test/dev |
| P3-B | Build/load index bền, corpus/model identity và corruption guard | Đã triển khai; không rebuild theo từng query |
| P3-C | Dense lookup theo scope/filter và lưu provenance | Có runtime; release phải kiểm đúng corpus/model được phân phối |
| P3-D | Recall/MRR/latency và negative handling độc lập | Report gốc còn CONDITIONAL; không sửa artifact thành PASS |
| P3-E | Kiểm tương thích tài nguyên CPU/GPU của candidate | Đối soát trong L13-01/02 và L14-03, không mở sweep model mới |

Đầu ra bàn giao: index truy hồi được và identity tái tạo được. Khoảng trống
negative/corpus nhỏ của report cũ phải được nêu trong ma trận L14-01; chỉ mở
việc mới khi chứng minh còn ảnh hưởng profile local, không tự chạy lại mọi phép đo.

<a id="bo-sung-phase-4"></a>
### Phase 4 — Basic RAG · DONE trong offline contract

Ghép retrieval → context có budget → prompt Việt/Anh → answer; cache theo
corpus/version và abstention khi thiếu evidence. Offline contract chứng minh
schema, cache, context và đường từ chối; chất lượng model thật được đánh giá ở
các phase sau, không suy ra từ fixture.
[Report](evaluation/results/basic_rag_report.json) ·
[Đặc tả](docs/planning/phase_details.md#phase-4).

#### Kế hoạch chi tiết Phase 4

Phụ thuộc: retriever Phase 3; grounding/citation nâng cao được hoàn thiện ở Phase 5.

| Hạng mục | Công việc / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| P4-A | Retrieval → context → prompt → generator → response | Schema và luồng lỗi/abstention có contract rõ |
| P4-B | Context budget, prompt Việt/Anh và evidence serialization | Không cắt mất provenance hoặc đưa gold vào provider payload |
| P4-C | Cache theo request/source/config/model/policy identity | Không hit cache sai nguồn, lịch sử hoặc phiên bản |
| P4-D | Offline contract report và regression | Chỉ chứng minh contract; không gắn nhãn chất lượng model thật |

Đầu ra: service RAG dùng được, có context/cache/abstention. Chất lượng live và
native format của profile phát hành được chốt tại Phase 14, không suy từ fixture.

<a id="bo-sung-phase-5"></a>
### Phase 5 — Citation, grounding và abstention · DONE nội bộ

**10/10 task, 5/5 gate, chốt 25/10/2026** trên `a21a4cd5` / `grounding-v29`.
Đã hoàn thành audit/contract, schema public/internal, citation/provenance,
claim grounding, abstention, benchmark/review, confidence/calibration/cache,
qualification, kiểm tra gates và bàn giao.

- **400/400 ca**: dev 120, test 130, holdout 150; kiểm tra vật lý độc lập PASS.
- Grounding/citation và abstention precision/recall **100%**, leakage **0**;
  reason accuracy **97,67%**, holdout ECE/Brier/risk **0**.
- Ba full regressions liên tiếp, mỗi lượt **2.663 PASS / 2 live SKIP**.
- Tái sử dụng 426 captures Gemini có HTTP input khớp, chạy lại pipeline;
  không gọi đó là inference mới hoặc fresh holdout.

Đây là nghiệm thu nội bộ có công khai exposure và owner duyệt. Giữ đóng Phase 5;
fresh holdout trước phân phối bản release vẫn là gate riêng ở Phase 14.
[Closure](evaluation/results/phase5-mixed-absence-20261024/phase5-closure.json) ·
[Handoff](docs/grounding/phase5_completion.md) ·
[Ngưỡng bất biến](configs/grounding_release.json).

#### Kế hoạch chi tiết Phase 5 — giữ 10/10 task đã đóng

Phụ thuộc: source/chunk/retrieval và basic RAG Phase 1–4. Bảng dưới giữ đầy đủ
task nghiệm thu nội bộ; không biến fresh release holdout thành lý do mở lại chúng.

| ID gốc | Nội dung / đầu ra | Trạng thái |
|---|---|---|
| P5-01 | Audit baseline, contract và bindings bằng chứng | DONE |
| P5-02 | Schema đầu ra public/internal và trường được công bố | DONE |
| P5-03 | Citation, trang, quote và provenance từ nguồn | DONE |
| P5-04 | Grounding từng claim và nội dung UI hiển thị | DONE |
| P5-05 | Abstention, reason và scope kiểm nguồn | DONE |
| P5-06 | Benchmark, review, nguồn gold và phép chấm | DONE |
| P5-07 | Confidence, calibration dev-only và cache version | DONE |
| P5-08 | Qualification runtime và regression | DONE |
| P5-09 | Kiểm report và đủ 5 quality gates | DONE |
| P5-10 | Handoff, tài liệu và cleanup có kiểm bindings | DONE |

Gate gốc: giữ nguyên ngưỡng trong config và closure, 400/400 ca có evidence.
Fresh holdout phát hành là L14-02; chốt cohort/protocol trước output và không
đổi nhãn tập đã exposure thành fresh. Không sinh lại captures đã hợp lệ chỉ để có log mới.

<a id="bo-sung-phase-6"></a>
### Phase 6 — BM25 + dense + RRF · DONE trong release lịch sử

Kết hợp lexical/dense, route mã môn, filter document/program/year, RRF, dedupe,
confidence và giới hạn candidate. Có đo chất lượng/latency riêng các nhánh và
artifact nhận diện corpus/index/config. Manifest lịch sử không tự chứng nhận
máy hoặc corpus mới.
[Manifest](evaluation/results/hybrid_release_manifest.json) ·
[Đặc tả](docs/planning/phase_details.md#phase-6).

#### Kế hoạch chi tiết Phase 6

Phụ thuộc: BM25/dense cùng corpus và provenance; bàn giao cho core quality Phase 7.

| Hạng mục | Công việc / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| P6-A | Lexical/dense candidates, exact-code route và selected filters | Không retrieval ngoài scope/document/program/year đã chọn |
| P6-B | RRF, dedupe, candidate budget và confidence | Cấu hình/calibration có version, không fit test/holdout |
| P6-C | Đo riêng BM25/dense/hybrid và negative | Giữ protocol, denominator và source của report lịch sử |
| P6-D | Cache/index lifecycle và grounding regression | Source/index/config đổi thì kiểm lại phần bị ảnh hưởng |
| P6-E | Manifest và runbook tái hiện | Historical release không tự chứng nhận candidate mới |

Đầu ra: hybrid retriever có budget và bằng chứng release lịch sử. Local workload
hiện hành được đo tại L14-03, không khởi động lại toàn bộ hardening backlog cũ.

<a id="bo-sung-phase-7"></a>
### Phase 7 — Chất lượng sản phẩm cốt lõi · DONE trong scope Chat

Scope owner chốt 13/10/2026: retrieval/context/scope, answer, citation, negative,
cache và fallback. **42/42 đáp án + 26/26 negative đúng**, 74 supported claims,
90 supported claim-citation pairs; 60/60 fault cases. Optional reranker giữ OFF;
nhánh qualification cũ vẫn RELEASE-BLOCKED nếu muốn bật lại. Performance API thật
chưa được nghiệm thu trong scope này, theo dõi ở R-01.
[Handoff](docs/phase7_product_handoff.md) ·
[Task và giới hạn](docs/planning/phase_details.md#phase-7).

#### Kế hoạch chi tiết Phase 7 — scope đã được điều chỉnh

Phụ thuộc: core RAG/grounding/hybrid. Giữ nguyên task ID và phần deferred.

| ID gốc | Nội dung / đầu ra | Trạng thái |
|---|---|---|
| C7-01 | Snapshot source/index/calibration/config và baseline | DONE trong scope đã chốt |
| C7-02 | Retrieval/context/scope, mã môn/bảng/nhiều hop và cache | DONE trên population đã khóa |
| C7-03 | Output review, source-grounded quality và paired app replay | DONE · 68/68 ca |
| C7-04 | Grounding/security/fault/restart/fallback regression | DONE · 60/60 fault cases |
| C7-05 | Workload HTTP end-to-end với provider thật | DEFERRED / NOT PASSED · giữ R-01 |
| C7-06 | Handoff, hashes, lệnh tái hiện và cleanup | DONE trong scope Chat đã điều chỉnh |

Không biến scope Chat DONE thành 6/6 live PASS. Optional reranker, GPU sweep,
learned router và canary giữ hoãn/OFF; chỉ mở khi có yêu cầu bật tính năng đó.

<a id="bo-sung-phase-8"></a>
### Phase 8 — Benchmark và evaluation · DONE trong scope Chat

Frozen v5 có 300 ca: **145/145 đáp án nguồn đúng + 155/155 negative đúng**,
178 supported claims, schema ứng dụng 300/300; exact-gold citation 144/145,
một chunk thay thế vẫn hợp lệ. Review tự động AI có provenance, không giả chữ
ký con người. Raw format chỉ 17 valid / 128 invalid; normalization không chứng
minh native provider format. Bộ đã exposure là regression; R-02 còn riêng.
[Evaluation](docs/phase8_evaluation.md) ·
[Completion](evaluation/results/phase78-chat-quality-completion-20261013.json).

#### Kế hoạch chi tiết Phase 8

Phụ thuộc: core quality Phase 7; benchmark/evaluator là nền regression các phase sau.

| ID gốc | Nội dung / đầu ra | Trạng thái |
|---|---|---|
| P8-01 | Benchmark, metric definitions, schema/group/split/source checks | DONE |
| P8-02 | Review và freeze v5, giữ lịch sử review | DONE · automated review đúng role |
| P8-03 | Thu output và replay actual application, đủ ID không trùng | DONE · 300/300 ca |
| P8-04 | Chấm content/citation/grounding/abstention/schema | DONE trong scope Chat |
| P8-05 | Audit baseline/bindings, giới hạn và handoff | DONE trong scope đã chốt |

Giữ raw format failures, exposure, review provenance và denominator; không sửa
raw hoặc gold để làm đẹp số. Native API format, latency và availability còn R-02,
nghiệm thu ở L14-03; bộ đã exposure chỉ dùng regression.

<a id="bo-sung-phase-9"></a>
### Phase 9 — Temporal RAG · DONE

**6/6 task, 5/5 gate; 24/24 ca** được source review và replay ứng dụng. Phân biệt
năm/khóa/phiên bản với ngày hiệu lực; lọc source eligibility trước generation,
so sánh hai phiên bản có nguồn; thiếu căn cứ “hiện hành/mới nhất” thì abstain.
Không suy hiệu lực chỉ từ tên file hoặc ngày ký.
[Handoff và protocol](docs/phase9_temporal_handoff.md).

#### Kế hoạch chi tiết Phase 9

Phụ thuộc: scope/provenance/grounding Phase 5–8; cung cấp temporal eligibility cho 10/11.

| Hạng mục (nhóm P9-01–06) | Nội dung / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| Contract/source audit | Loại ngày, precision, kỳ/khóa/version và source family | Không suy ngày hiệu lực từ filename/ngày ký |
| Metadata/eligibility | Lưu clause nguồn và quyết định khả năng áp dụng | Unknown/invalid phải được biểu diễn, không tự điền ngày |
| Resolver/integration | Lọc phiên bản trước retrieval/generation, bind cache | Không chọn “mới nhất/hiện hành” khi thiếu proof |
| So sánh phiên bản | Evidence đủ hai phía, xử lý conflict/amendment có giới hạn | Không ngầm coi sửa đổi một phần là thay toàn văn |
| Acceptance/handoff | 24 frozen cases, 5 gates và lệnh tái hiện | DONE · P9-01–06; giữ bindings và regression |

ID/tiêu chí từng task đầy đủ vẫn ở đặc tả gốc. Không nới sang giải quyết mọi
quan hệ văn bản pháp quy; trường hợp vượt contract phải abstain rõ.

<a id="bo-sung-phase-10"></a>
### Phase 10 — Multi-document / multi-hop · DONE

**5/5 task, 5/5 gate; 24/24 ca**, 32 supported claims và 24 valid citations.
Ghép evidence có vai trò rõ, tối đa một truy hồi phụ khi identifier được nguồn
chứng minh; giữ quyền/source scope và temporal contract. Thiếu một hop, ô trống
hoặc quan hệ mâu thuẫn thì không suy diễn đáp án.
[Handoff](docs/phase10_multi_hop_handoff.md) ·
[Completion](evaluation/results/phase10-completion-20261014.json).

#### Kế hoạch chi tiết Phase 10

Phụ thuộc: temporal/source authorization và core quality đã có; không cần graph/reranker.

| Hạng mục (nhóm P10-01–05) | Nội dung / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| Scope/contract | Khóa source roles, toán hạng và yêu cầu đủ hop | Không trả một phần rồi bỏ điều kiện người dùng |
| Planning/budget | Một lượt retrieval gốc, tối đa một lượt phụ có proof | Không model planner hoặc vòng truy hồi không giới hạn |
| Composition | Ghép facts từ hàng/ô đúng nguồn và vai trò | Mã giống nhau không tự chứng minh tương đương học phần |
| Grounding/negative | Kiểm từng claim/hop, nguồn thiếu/trống/mâu thuẫn | Fail closed khi không có đủ cầu nối evidence |
| Acceptance/handoff | 24/24 ca, 32 claims, 24 citations, đủ 5 gates | DONE · giữ protocol/baseline/replay và limits |

Giữ nguyên ID/task contract trong đặc tả gốc; bổ sung này không đổi thuật toán,
không mở rộng số hop hoặc coi replay timing là thời gian API thật.

<a id="bo-sung-phase-11"></a>
### Phase 11 — Chỉ mục quan hệ có nguồn · DONE, mặc định OFF

**5/5 task, 5/5 gate** cho SQLite sidecar tùy chọn: tiên quyết trực tiếp, truy vấn
ngược và chuỗi hai cạnh, mỗi quan hệ có proof hàng/ô nguồn. Có budget, scope,
fingerprint, invalidation và rollback; không cần dịch vụ graph riêng. Chỉ bật
trên profile/corpus đã qualification; bản local có thể phát hành khi vẫn OFF.
[Handoff](docs/phase11_relation_index_handoff.md) ·
[Completion](evaluation/results/phase11-completion-20261014.json).

#### Kế hoạch chi tiết Phase 11

Phụ thuộc: source/table proof, temporal eligibility và Phase 10; nhánh tùy chọn.

| Hạng mục | Nội dung / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| Scope/value gate | Chốt tiên quyết trực tiếp, inverse lookup và chuỗi hai cạnh | Không tuyên bố graph tổng quát hoặc suy quan hệ mới |
| Build/index | SQLite sidecar và manifest source/extractor/schema/policy | Không publish cạnh blank/AND/OR/conflict/thiếu endpoint |
| Query/grounding | Authorization trước lookup, budget và proof từng cạnh | Không traversal ngoài quyền; hai cạnh không thành một cạnh trực tiếp |
| Lifecycle/rollback | Rebuild ngoài request, stale/corrupt fail closed, OFF rollback | Không dùng proof cũ sau source/delete/version đổi |
| Acceptance/handoff | 5/5 task, 5/5 gates và tài liệu bật/tắt | DONE trong pilot đã chốt; mặc định OFF |

Release local không bắt bật sidecar. Muốn bật profile/corpus khác phải có
qualification tương ứng; giữ budget, source proof và activation guard hiện có.

<a id="bo-sung-phase-12"></a>
### Phase 12 — Web app MVP · DONE trong local single-user

UI Python/HTML/CSS/JavaScript cùng app: thư viện, collections, upload/job, chat,
source/citation, feedback, delete và hướng dẫn. Có launcher Windows, responsive,
accessibility và browser acceptance. Upload tối đa **5 PDF mỗi lượt**, được thêm
các lượt tiếp trong cùng chat. Hoàn thành MVP không đóng thay QA mở rộng.
[UI, setup và bằng chứng](docs/ui/phase12-ui.md).

#### Kế hoạch chi tiết Phase 12

Phụ thuộc: service/contracts Phase 1–10; Phase 11 không bắt buộc.

| Hạng mục | Nội dung / đầu ra đã có | Điều kiện giữ nghiệm thu |
|---|---|---|
| UI shell/navigation | Chat, library, collections và guide | Responsive, focus/keyboard và thông báo lỗi rõ |
| Upload/jobs | Tối đa 5 PDF/lượt, thêm được lượt tiếp, progress/cancel/retry | Không báo ready trước khi index; không giới hạn toàn chat ở 5 PDF |
| Chat/source | Scope đã chọn, conversation, answer/citation/source và feedback | Chỉ công bố nội dung qua grounding, không lộ diagnostics nội bộ |
| Lifecycle | Delete, OCR từ chi tiết, restart và provider-error UX | Giữ quyền nguồn, hủy worker, quota/cooldown và dữ liệu nhất quán |
| Acceptance/handoff | Offline/browser/accessibility và launcher local | DONE trong MVP; QA mở rộng/final RC vẫn còn riêng |

Đầu ra: web app single-user dùng được trên loopback. Packaging cài sạch và
nghiệm thu artifact phân phối thuộc Phase 13/14; không biến UI DONE thành release DONE.

<a id="bo-sung-qa-goal-progress"></a>
<a id="bo-sung-viec-con-lai"></a>
## 4. QA mở rộng — đầu vào của bản local release

Nguồn yêu cầu: `goal.txt`. Chi tiết: [QA audit](QA_AUDIT.md),
[test scenarios](TEST_SCENARIOS.md), [performance](PERFORMANCE_REPORT.md),
[improvements](IMPROVEMENT_LOG.md). Giữ các task DONE đóng.

### Việc còn mở, làm theo thứ tự

1. [ ] **QA-03b / QA-07c — PDF đại diện.** Dùng inventory 34 PDF, đối chiếu
   trang/text/bảng/ô với nguồn; extraction ≥98%, OCR ≥90%, evidence/retrieval
   ≥95%, không mất trang, nhầm tài liệu hoặc dữ liệu. Chốt denominator và cách
   tính trước khi chấm; fixture không thay nghiệm thu PDF thật. QA-03b1 (chữ ẩn)
   và QA-03b2 (VietOCR riêng) đã DONE. **QA-03b3 engineering DONE:** đủ 5 bảng,
   77 chunks; 14/14 kiểm tra truy hồi đúng bảng, chặn 13/13 lỗi nhầm giờ học thành
   tín chỉ trên một PDF. Chưa đóng chất lượng đại diện. [Bằng chứng](docs/ui/evidence/ocr-table-grounding-20261028.json).
2. [ ] **QA-08c — Streaming model thật.** Mục tiêu p95 TTFT ≤5 giây trên môi
   trường cố định; không tính heartbeat/cache/trích đoạn thành token model.
   Engineering SSE đã DONE, mặc định OFF; cohort 20 câu có 17 đúng nguồn và
   3 timeout, p95 gồm lỗi **chưa đạt**. Không bỏ lỗi khỏi denominator.
   Nếu giữ streaming OFF cho v1, ghi gate DEFERRED và bỏ mọi tuyên bố đạt TTFT;
   đây là điều chỉnh scope release, không phải đổi QA-08c thành PASS.
   [Evidence](docs/ui/evidence/query-streaming-20261028.json).
3. [ ] **QA-09d — Nghiệm thu cuối.** Khi runtime RC ổn định: 3 full regressions
   liên tiếp cùng source, required tests/flows 100%, critical E2E 100%, tổng E2E
   ≥98%, không crash/exception chưa xử lý; không còn P0/P1 hoặc High/Critical
   đã xác nhận. Lượt full mới nhất: **3.168 PASS / 0 FAIL / 2 live SKIP**;
   chưa thay chuỗi 3 lượt trên runtime cuối. Thực hiện một lần tại L14-07.

<a id="bo-sung-da-done"></a>
### Các mốc QA đã DONE — bằng chứng được giữ lại

| Nhóm đã hoàn thành | Kết quả / hồ sơ |
|---|---|
| QA-01, QA-02 | Export từ Git có 114 app tests PASS; Phase 5 nội bộ đã đóng như trên |
| QA-03a, QA-07a | So CPU/CUDA trên 5 PDF; inventory 34 SHA và kiểm trang. [Inventory](docs/ui/evidence/phase5-v27-20261024/pdf-parser.json) |
| QA-03b1 | Loại chữ vô hình khỏi evidence; 34 PDF/268 trang giữ nguồn, 344 tests PASS. [Evidence](docs/ui/evidence/pdf-visibility-20261027.json) |
| QA-03b2 | VietOCR opt-in riêng, đủ 18 trang; mã đúng 20/20, scan fixture 97,2%; 282 tests PASS. [Evidence](docs/ui/evidence/vietnamese-ocr-20261028.json) |
| QA-03b3 — DONE | Giữ liên kết ô/hàng bảng OCR; đọc lại vùng tên môn/tín chỉ bị gom từ ảnh, không điền số từ gold. PDF 18 trang: 67,84s, 5 bảng/77 chunks. Truy hồi BGE-M3 đúng bảng 14/14, chặn nhầm giờ học 13/13. Native 35 PDF/368 trang giữ nguyên bảng/schema. 278 focused tests và full 3.168 tests PASS; mặc định OCR không đổi. Đây là engineering/diagnostic, không phải nghiệm thu chất lượng đại diện. [Evidence](docs/ui/evidence/ocr-table-grounding-20261028.json) |
| QA-03c / QA-08d | 20/20 fresh uploads PDF text 100 trang/10 MB, p95 12,25s ≤15s; model/OS cache warm trên CUDA. Startup riêng 42,51s. [Evidence](docs/ui/evidence/native100-performance-20261027.json) |
| QA-04–06, QA-10–11, QA-13 | Mixed PDF, OCR từ chi tiết, job identity cũ, cancel/progress, OCR process Việt/Anh và ảnh trong trang text. [Isolation](docs/ui/evidence/ocr-isolation-20261025.json), [OCR](docs/ui/evidence/ocr-evaluation-20261025.json) |
| QA-07b cùng các bản sửa | Natural100 accuracy bảo thủ ≥95/100, answerable ≥75/80, hallucination phát hiện 0/100; context 15/15 và 17 trường. Bộ dev exposed, không phải fresh holdout. [Quality](evaluation/results/full-app-natural-20261026/quality-qualification.json), [Context](evaluation/results/full-app-natural-20261026/context-quality.json) |
| QA-08a / QA-08b | 400/400 HTTP 200 trên workload API local; Web Vitals lab 9/9. Không suy thành tải generation AI đồng thời. [Coverage](docs/ui/evidence/hybrid-coverage-20261025.json) |
| QA-08c1 | SSE, cancel, quota/cooldown và UI chỉ công bố kết quả sau grounding; 346 related tests, 9 JS checks, UI 43/44 checks theo nhánh. [Evidence](docs/ui/evidence/query-streaming-20261028.json) |
| QA-09a / QA-09b | Unit/integration và 43/43 browser flows ở mốc lịch sử. [Browser](docs/ui/evidence/hybrid-final-ui-20261025/browser-results.json) |
| QA-09c1–c2c | Recovery local, 10 checkpoint kill/restart, deep JSON trả 400, Host guard localhost; 229 related tests và secret scan PASS. [Evidence](docs/ui/evidence/request-safety-recovery-20261027.json) |
| QA-12 | Cache metadata/library có invalidation, đọc đúng scope; quyền/delete/retry vẫn kiểm tra mới. [QA audit](QA_AUDIT.md) |

Các số test có thể chồng lấn, không cộng lại thành tổng tests độc lập. Không
thử lại TableFormer + OCR từng ô đã bị loại do chậm/sai nếu chưa có lý do mới.

<a id="phase-13"></a>
<a id="bo-sung-phase-13"></a>
<a id="bo-sung-phase-13--deployment"></a>
## 5. Phase 13 — Đóng gói và vận hành bản local

**Đánh giá:** app local đã tồn tại và có recovery/performance evidence; thiếu
nghiệm thu tái tạo bản phát hành ngoài môi trường dev. Không cần xây lại server,
frontend hay pipeline. Chọn **source bundle/checkout theo tag + môi trường Python
khóa bằng `uv.lock` + launcher** cho v1; chưa cần tự ép thành một file `.exe`.
Windows x64 là đích ưu tiên; chỉ công bố OS/Python/CPU/GPU thực sự đã kiểm chứng.
Metadata Python hiện khai báo 3.11–3.14 không có nghĩa mọi tổ hợp đều đã test.

Phụ thuộc: Phase 12, runtime hiện có; đóng QA PDF trước khi khóa RC cuối. Có thể
làm packaging/docs song song về mặt tiến độ, nhưng source-bound receipt phải
được tạo từ candidate cụ thể. **Task mới chưa được tự tick theo bằng chứng cũ.**

| ID | Công việc cụ thể | Điều kiện đóng / đầu ra | Trạng thái |
|---|---|---|---|
| L13-01 | Chốt release contract | Ghi Windows/Python đã test, browser, CPU tối thiểu; GPU tăng tốc tùy chọn; phân biệt cài mới cần mạng với chạy sau setup; chốt streaming/graph/reranker OFF mặc định | [ ] |
| L13-02 | Khóa cấu hình và runtime assets | Bind commit, `uv.lock`, profile, encoder revision/hash, OCR/model/language data và license; setup có checksum, lỗi rõ, không tự tải model trong upload/query | [ ] |
| L13-03 | Tạo artifact tái tạo được | Bundle đủ `src`, `scripts`, UI, config mẫu, lock, launcher và docs; manifest SHA-256/file list; loại `.venv`, credential, PDF cá nhân, runtime state/cache và temp; phân biệt source bundle với wheel thư viện | [ ] |
| L13-04 | Cài sạch ngoài working tree dev | Giải nén/checkout candidate trong thư mục mới, tạo env từ lock, setup model/OCR, nhập key riêng; start/stop/restart và smoke upload → chat → citation → delete đạt; không mượn module/index/state của dev | [ ] |
| L13-05 | Chốt thư mục dữ liệu và preflight local | Tài liệu hóa đường dẫn PDF/store/index/job/cache/quota/log/model; tạo lần đầu, quyền ghi, dung lượng, port bận, thiếu model/key, CPU fallback; không ghi dữ liệu vào vùng cài đặt chỉ đọc | [ ] |
| L13-06 | Tài liệu người dùng và hỗ trợ | Quick start Windows, setup online/OCR tùy chọn, cấu hình key không lộ, stop/update/backup/uninstall; lỗi thường gặp, cấu hình CPU/GPU đã đo và giới hạn PDF; người mới làm được từ docs | [ ] |
| L13-07 | Khóa release candidate | Candidate có version/commit, artifact checksum, dependency/model/config identities, feature flags, báo cáo install/smoke và known issues; chuyển đúng candidate sang Phase 14 | [ ] |

**Gate đóng Phase 13:** 7/7 task, artifact không chứa secret/dữ liệu cá nhân,
cài sạch tái tạo được và vận hành end-to-end trên profile đã công bố. QA PDF
còn mở hoặc candidate thiếu asset/module thì chưa được gọi là RC sẵn sàng.

Không bê tỷ lệ **6/64 tiêu chí, 0/16 task cloud** sang kế hoạch local: chúng khác
contract. Kế hoạch cloud cũ được giữ làm lịch sử, không còn là backlog bắt buộc.
Provider admission, cache, cooldown và cấu hình portable đang có vẫn được dùng.

<a id="phase-14"></a>
<a id="bo-sung-phase-14"></a>
## 6. Phase 14 — Hardening, nghiệm thu và phát hành local

**Đánh giá:** rủi ro còn lại nằm ở PDF/OCR thật, độ tin cậy model/provider, bảo vệ
dữ liệu trên máy và tính tái tạo của gói. Không cần Kubernetes, reverse proxy,
đăng nhập đa người dùng hay SLO cloud cho scope loopback single-user. Host guard,
quyền nguồn, timeout, quota, cancellation và grounding vẫn bắt buộc.

Phụ thuộc: RC Phase 13 có identity rõ. Đây là nghiệm thu của **candidate cụ thể**,
không mở lại toàn bộ phase cũ. Dùng lại evidence còn tương thích, chỉ chạy mới
phần thay đổi hoặc gate release yêu cầu. Không tự tạo nhãn human signoff.

| ID | Công việc cụ thể | Điều kiện đóng / đầu ra | Trạng thái |
|---|---|---|---|
| L14-01 | Khóa ma trận yêu cầu và phạm vi | Map QA/R-01/R-02/fresh holdout tới case, profile, threshold và evidence; phân biệt blocking với optional deferred; giữ nguyên lỗi và các gate chưa PASS | [ ] |
| L14-02 | Nghiệm thu PDF/AI trên RC | Đóng QA-03b/QA-07c với 34 PDF; giữ gold/threshold; thêm fresh holdout đóng băng trước output, tách dev/test, có source review và denominator theo loại câu; không tune rồi gọi chính bộ đó là fresh | [ ] |
| L14-03 | Đo provider và hiệu năng local thật | Đóng R-01/R-02 bằng protocol phù hợp profile local đã khóa trước run; đo cold/warm/cache riêng, p50/p95/errors/timeouts/RSS/usage, native format; dùng profile/budget đã được phép, không xoay key/retry vô hạn | [ ] |
| L14-04 | Bảo mật và quyền riêng tư local | Secret/dependency scan, loopback/Host/origin và request validation, path/symlink/upload limits, quyền nguồn/cache, cancel/timeout; không có P0/P1/High/Critical đã xác nhận; privacy notice mô tả payload/provider/log/retention thực tế | [ ] |
| L14-05 | Backup, restore và update/rollback | Backup nhất quán PDF/metadata/job/config cần thiết; restore vào state sạch rồi kiểm hash, citation, chat/delete; test ngắt process, hết đĩa, state/index hỏng, đổi version; rollback không làm mất source và dữ liệu cũ | [ ] |
| L14-06 | Chẩn đoán và runbook | Request ID/log có giới hạn, stage latency, lỗi quota/503/OCR và health; không log key hoặc toàn bộ tài liệu; hướng dẫn restart, reset index an toàn, cấp quyền, thu log đã lọc và uninstall có lựa chọn giữ dữ liệu | [ ] |
| L14-07 | Regression cuối đúng RC | Đóng QA-09d: 3 full liên tiếp cùng runtime, required/critical flows 100%, E2E ≥98%; test launcher/install/browser/OCR/source/delete/recovery trên artifact; live SKIP không tính live PASS | [ ] |
| L14-08 | Hồ sơ phát hành và bàn giao | Release notes/known limits, manifest/checksum, install/backup/restore docs, evidence source-bound và danh sách hoãn; owner duyệt candidate cụ thể rồi tạo tag/phát hành bản local theo phạm vi được phép | [ ] |

### Xử lý các điều kiện release cũ

| Điều kiện | Quyết định cho local release |
|---|---|
| R-01 — Performance Phase 7 | Vẫn NOT PASSED. Giữ protocol cũ 100 HTTP/54 provider calls, p95 ≤10s, timeout ≤0,5%, RSS ≤75% RAM làm mốc. Nếu workload/profile v1 khác, phải khóa amendment trước run và báo riêng; không sửa nhãn lịch sử |
| R-02 — Phase 8 live API | Vẫn NOT PASSED. Chat/replay/normalized output không thay native API latency/availability/format; nghiệm thu trên profile thực sự phân phối, báo đủ lỗi và thiếu mẫu |
| R-03 — Public cloud deployment | Rút khỏi scope theo quyết định 28/10/2026, không ghi PASS. Nghĩa vụ bảo mật, dữ liệu, recovery và vận hành local chuyển L13/L14 |
| Fresh holdout Phase 5 | Giữ gate trước phân phối release, độc lập DONE nội bộ. Khóa số mẫu/strata/review và ngưỡng trước chạy; giữ thresholds [grounding](configs/grounding_release.json), không sửa nhãn/gold để qua gate |
| QA-08c streaming ≤5s | Nếu OFF mặc định: được DEFERRED với giới hạn công khai, không claim PASS/TTFT. Muốn đưa streaming vào tính năng đã nghiệm thu phải qua gate thật, tính cả timeout |
| Graph/reranker | OFF mặc định; không bắt qualification tính năng tắt. Bật lại cần nghiệm thu đúng profile và guards lịch sử |

**Gate đóng Phase 14 / hoàn thành dự án:** 8/8 task; Phase 13 đóng; các gate
blocking chất lượng, an toàn dữ liệu, provider và final regression có bằng chứng
khớp candidate; không còn lỗi nghiêm trọng đã xác nhận; owner duyệt bản local.
Chỉ công bố máy/profile/workload đã đo. Không hứa AI offline, hỏi miễn phí vô
hạn, hỗ trợ mọi PDF/OS hoặc availability 100% khi chưa có chứng cứ.

### Thứ tự thực hiện từ hiện tại

1. Hoàn tất PDF đại diện (QA-03b/QA-07c), chốt backend OCR đủ điều kiện cho v1.
2. Làm L13-01–06; định nghĩa ma trận L14-01 và protocol live/holdout trước đo.
3. Khóa L13-07, chạy L14-02–06 trên candidate đó; giữ sửa lỗi trong scope local.
4. Chốt runtime rồi thực hiện L14-07 một lần đủ chuỗi; thay source/config sau đó
   chỉ vô hiệu hóa evidence bị ảnh hưởng, phải có lý do và phạm vi kiểm tra lại.
5. Chuẩn bị hồ sơ L14-08, owner duyệt candidate, phát hành local và bàn giao.

<a id="bo-sung-quy-tac-cap-nhat"></a>
## 7. Quy tắc giữ plan và bằng chứng

1. Chọn một task còn mở, ghi lỗi/khoảng trống, điều kiện đóng và evidence. Tick
   ngay khi đủ; không tính % bằng cộng task có khối lượng khác nhau.
2. Giữ task DONE đóng; chỉ mở lại vì source/phụ thuộc liên quan đổi, lỗi mới,
   môi trường ngoài scope hoặc nghiệm thu cuối bắt buộc. Ghi lý do trước.
3. Sửa tài liệu không kích hoạt full regression/400 ca/API/PDF benchmark.
   Sửa runtime chạy focused tests trước; không cộng các lượt tests chồng lấn.
4. Không tune test/holdout, không giả reviewer, không tính replay/cache/SKIP
   thành native inference/live PASS. Dùng lại captures chỉ khi binding hợp lệ.
5. Giữ giới hạn chi phí, dữ liệu và provider đã thống nhất; không bật billing,
   đổi key/model hoặc gọi API chỉ để tạo report. Local release không bỏ quota.
6. Dọn file tạm sau khi kiểm tra references/bindings. Giữ source, config, tests,
   baseline, raw failures và artifact cần tái hiện; không xóa bằng chứng phase cũ.
7. Giữ `plan.md` tại root và tracked Git; commit/push qua `origin` CampusAI,
   không đẩy sang repository financial cũ. Thay đổi chưa liên quan giữ riêng.

## 8. Tra cứu lịch sử và tương thích liên kết

[Đặc tả phase cũ](docs/planning/phase_details.md) giữ ID task, ngưỡng, contract,
cloud checklist và lịch sử thử nghiệm. **Plan hiện hành này quyết định phạm vi,
trạng thái và thứ tự công việc.** Các yêu cầu cloud cũ đã được thay thế; không
xóa/đổi byte báo cáo lịch sử để hợp thức hóa local release.

[Hardening Phase 3–6](docs/planning/release_hardening_plan.md) là backlog tham
chiếu lịch sử; đánh giá khoảng trống liên quan qua L14-01, không tự chạy lại toàn
bộ hoặc đổi trạng thái DONE của các phase đã nghiệm thu.

<a id="bo-sung-ưu-tiên-hiện-tại--hỏi-liên-tục-không-quá-tải-chi-phí-dịch-vụ-0"></a>
Continuity local ngày 16/10 đã đóng trong phạm vi đã đo:
[hồ sơ](docs/deployment/phase13/free-continuity-goal.md). Không đồng nghĩa provider
miễn phí vô hạn hoặc đã đạt R-01/R-02.

<a id="bo-sung-phase-7--hoàn-thiện-chất-lượng-sản-phẩm-phạm-vi-tinh-gọn"></a>
<a id="bo-sung-phase-7--reranker"></a>
<a id="bo-sung-phase-7--reranker-release-qualification"></a>
<a id="bo-sung-phase-7-joint-dev-feasibility--2026-10-04"></a>
Optional reranker giữ OFF; qualification cũ chỉ mở khi cần bật lại.
[Đặc tả lịch sử](docs/reranker/phase7_task_spec.md) ·
[Artifact storage/restore](docs/operations/artifact_storage.md).
