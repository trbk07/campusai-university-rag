# CampusAI — Kế hoạch và tiến độ

Cập nhật: **26/10/2026 · Asia/Bangkok**

Repository: [trbk07/campusai-university-rag](https://github.com/trbk07/campusai-university-rag)

## 1. Đọc nhanh

**Phase 5 đã DONE 100% trong phạm vi nghiệm thu nội bộ.** Goal đang làm là
kiểm thử và tối ưu **toàn bộ ứng dụng**, có phạm vi rộng hơn Phase 5.

| Nội dung | Trạng thái |
|---|---|
| Phase 5 — citation, grounding, abstention | **DONE · 10/10 task, 5/5 gate** |
| Web app MVP | **DONE** trong phạm vi local |
| Goal QA và tối ưu toàn ứng dụng | **ĐANG LÀM** · còn 5 nhóm việc bên dưới |
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
2. [ ] **QA-08c — Tốc độ streaming AI thật.**
   Đo **p95 thời gian đến token đầu tiên ≤5 giây** trong môi trường cố định.
   Không tính heartbeat, cache hoặc trích đoạn local thành token model mới.
3. [ ] **QA-03c / QA-08d — Tốc độ PDF text 100 trang / 10 MB.**
   Đo **p95 ≤15 giây** trên pipeline coverage-v3. Phép đo cũ 100 trang / 6,17 MB
   giữ làm baseline, chưa đủ để đóng yêu cầu này.
4. [ ] **QA-09c2 — Recovery và bảo mật còn thiếu.**
   Chỉ bổ sung tình huống chưa được kiểm chứng. Điều kiện đóng: không còn lỗi
   **P0/P1 hoặc High/Critical được xác nhận**, mọi recovery quan trọng có bằng chứng.
   **Đã xong QA-09c2a:** sửa khóa đường dẫn tuyệt đối trong catalog bằng chứng;
   validator Phase 7 hoạt động lại, hash/dữ liệu gốc giữ nguyên, 54 tests liên quan PASS.
5. [ ] **QA-09d — Nghiệm thu cuối goal.**
   Khi runtime cuối ổn định: chạy **3 full regressions liên tiếp** trên cùng source,
   kiểm 100% luồng/tests bắt buộc, critical E2E 100%, tổng E2E ≥98% và không có
   crash/exception chưa xử lý. Đối chiếu toàn bộ yêu cầu rồi mới đóng goal.
   Lượt full gần nhất: **3.013 PASS / 4 FAIL / 2 live SKIP**. Bốn lỗi cùng do một
   khóa catalog sai đã được sửa; **54 tests liên quan PASS** sau sửa. Bộ tính năng
   ngữ cảnh/lịch học có **546 tests liên quan PASS**. Chưa chạy chuỗi 3 full cuối;
   không cộng các run thành một lượt full PASS.

<a id="da-done"></a>
### 2.2. Task đã DONE — giữ đóng

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
