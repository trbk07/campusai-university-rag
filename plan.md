# CampusAI — Roadmap local

Cập nhật: **02/11/2026 · Asia/Bangkok**.

## Trạng thái

Web app MVP có upload PDF, OCR nền/checkpoint, truy hồi hybrid, hỏi đáp có
citation, hội thoại và quản lý tài liệu. Phase 5 hoàn tất nội bộ; Phase 7/8
đóng theo phạm vi Chat-quality của chủ dự án. Chưa nghiệm thu bản phát hành cuối.

Theo yêu cầu ngày 31/10, các báo cáo được gom tại
[báo cáo tổng quan](docs/PROJECT_OVERVIEW.md); log, bộ kiểm thử, benchmark và
artifact nghiệm thu cũ đã bỏ khỏi cây làm việc. Mốc công việc dưới đây giữ
trạng thái lịch sử. Muốn chứng nhận lại cần bằng chứng mới khớp source được
chọn; không dựa vào đường dẫn artifact đã xóa.

## Tài liệu

- [x] **DOC-01 — README tiếng Anh DONE (01/11):** viết lại giới thiệu, tính năng,
  sơ đồ xử lý, setup Windows/Docker, quyền riêng tư, development/CI và mục lục tài
  liệu; đối chiếu lệnh với code/config, kiểm tra liên kết nội bộ. Không thêm file báo cáo.

## Đọc PDF và OCR — yêu cầu bổ sung 02/11

- [x] **OCR-02 — Tốc độ và chữ nhỏ DONE:** render xám cho trang giấy, tăng độ phân
  giải có chọn lọc cho chữ nhỏ một cột; giữ RGB/độ phân giải cũ cho vùng ảnh màu.
  OCR tối đa 4 worker dùng chung, không hạ giới hạn pixel, timeout hoặc coverage.
  Workload 5 PDF / 41 trang cần OCR, hai lần A/B: trung bình **8,42 → 6,59s**
  (nhanh hơn 21,8%, chỉ phần OCR). Sáu mẫu raster Việt/Anh có reference xác định:
  CER **34,01% → 0,58%** trên 4.998 ký tự; không suy thành accuracy mọi PDF.
- [x] **OCR-03 — Cache và upload DONE:** upload lại PDF có policy OCR cũ sẽ xử lý
  nâng cấp, giữ cùng tài liệu; policy hiện hành vẫn trả duplicate nhanh. Checkpoint,
  coverage và audit vùng ảnh khớp policy mới, không mất audit giữa các lô.
- [x] **OCR-04 — Không đọc lại bảng mỗi lô DONE (`c05007b0`):** tái dùng kết quả
  giải mã vật lý trong cùng job; ràng buộc source/visibility, cô lập từng snapshot
  và job, giải phóng khi hoàn tất hoặc lỗi. Không thêm cache/báo cáo trên đĩa.
  A/B toàn pipeline NUAE 148 trang: **122,51 → 94,94s**, bảng **3 → 1 lần đọc**,
  output giống hệt; phần đầu sẵn sàng **53,07s**, vẫn còn chi phí index lần đầu.
  **196 tests hiện hành PASS**, gồm 6 ca OCR thật local; CI không có font/model
  sẽ skip 6 ca này. Kiểm tra tương thích bảng: 24 PASS, 3 ca thiếu corpus cũ.
  CI Windows/Linux, package/container PASS. QA-07c accuracy nguồn thật còn mở;
  không tuyên bố mọi PDF đạt 99–100% hoặc mọi upload hoàn tất trong vài giây.

## Goal đã hoàn tất — cải thiện hỏi đáp PDF

Goal hoàn tất ngày **01/11/2026**, source **`cacb4bdd`**. Tập trung chất lượng trao đổi với người dùng,
không mở lại OCR/Docker hoặc qualification đã DONE nếu không có hồi quy.
Theo yêu cầu mới: lặp tái hiện → sửa → hồi quy, chỉ mời owner kiểm khi đã đạt
mục tiêu 99–100% trên bộ ca hợp lệ chốt trước và không còn lỗi nghiêm trọng đã biết.
Đếm riêng semantic quality, thiếu ý, từ chối nhầm và HTTP/schema; không tính ca
cần review gold là PASS. Không tạo JSON/log nghiệm thu rời nếu không cần thiết;
giữ checklist/kết quả trong tài liệu hiện có, chỉ thêm regression test khóa lỗi.

- [x] **ASK-01 — Rà soát ban đầu DONE:** C04 bị guard tên trường chặn cả hai
  lượt do tách nhầm tên/predicate và thiếu proof tên trong đoạn truy hồi; C02 có
  claim thời hạn đã kiểm chứng nhưng phần trả lời bỏ mất; A06 nhầm chức danh
  “hiệu trưởng” thành tên trường. Giữ các ca này làm hồi quy, dùng dữ liệu phản
  chứng/tên giả trong test; F24 vẫn review gold riêng, không sửa đáp án để tăng điểm.
- [x] **ASK-02 — Nhiều nguồn DONE:** sửa nhận diện tên trong nguồn được trích,
  chặn đảo số liệu và chuẩn hóa `TC`/`tín chỉ`. Đoạn văn bị trích thành bảng cột
  rỗng được giữ đủ dòng, không làm mất cấu trúc bảng thật. C01–C04 trả đúng nguồn
  trong lượt 60 HTTP trên `cacb4bdd`, không cache.
  Tests vẫn chặn mâu thuẫn nội bộ, tên bịa, sai phủ định và số liệu tráo nguồn.
- [x] **ASK-03 — Câu trả lời đủ nghĩa DONE:** giữ điều kiện, ngoại lệ, thời hạn,
  đối tượng, khoảng điểm và ngữ cảnh cùng hàng/mục nguồn. Chín ca thiếu ý
  F01/F04/F17/F19/F20/F25/F26/N01/N04 đã đủ ý trong lượt cuối; R06 cũng giữ lưu ý
  về các điều kiện khác trên nhánh local. Không đoán nhóm đầu vào hoặc cộng thêm
  lượt AI. Mục chưa khép, bảng thật, bằng chứng mơ hồ hoặc thông tin đã hiện đủ
  không được dùng để thêm/lặp ghi chú. Mọi phần bổ sung phải kiểm chứng lại.
  F24 giải thích thiếu bằng chứng từng kỳ, không suy từ tổng năm hoặc tự kết luận
  toàn tài liệu không đề cập. Bốn ca cần review gold/scope giữ riêng ở ASK-08.
- [x] **ASK-04 — Hội thoại tự nhiên DONE trong phạm vi lỗi đã xác định:** 4 hội thoại
  M01–M04/8 lượt giữ đúng trường, điểm, học kỳ và chủ đề. Role “hiệu trưởng” không
  còn bị nhận nhầm thành tên trường; thiếu thời điểm thì yêu cầu nguồn cập nhật.
  Regression dùng tên/đối tượng giả, không whitelist trường hoặc câu hỏi owner.
- [x] **ASK-05 — Tốc độ DONE trong workload đã đo:** 60 HTTP liên tục trên
  `cacb4bdd`, p95 **4,700s**, tối đa **7,735s**, không timeout hoặc lỗi provider;
  25 lượt local, 0 cache, 35 lượt có provider/37 attempts (2 lượt sửa diễn đạt).
  Giữ quota/cooldown; đây là thời gian hoàn tất, không phải TTFT hoặc cam kết mọi PDF.
- [x] **ASK-06 — Chốt goal DONE:** **173 tests hiện hành + 164 tương thích PASS**;
  1 test cũ thiếu corpus không chạy. Đủ **56 case / 60 HTTP trên cùng `cacb4bdd`**,
  155 file runtime không đổi; C01–C04, M01–M04 và thiếu ý đều được đối chiếu.
  Chấm dev: **52 PASS / 0 PARTIAL / 4 REVIEW_REQUIRED**; 52/52 ca đủ input/gold
  đạt trong bộ đã exposure, không phải chứng nhận độc lập hoặc accuracy mọi PDF.
  CI Windows/Linux, package/container PASS; code đã push đúng origin CampusAI.
- [x] **ASK-07 — OCR nhanh hơn DONE (`c54b2b8b`):** OCR song song có giới hạn,
  lô tăng theo tốc độ thực và chỉ encode đoạn mới/thay đổi. PDF scan 34 trang:
  toàn bộ pipeline **52,81 → 29,48s**, phần đầu sẵn sàng **4,27s**, đủ 34/34 trang;
  hash toàn văn giống baseline. Hai PDF scan/mixed chạy cùng lúc: OCR **14,92 →
  4,65s**, text/layout/confidence giống bản tuần tự. Đã kiểm cancel, partial timeout,
  checkpoint, giới hạn worker và rollback index. Đây là A/B warm một lượt/workload,
  không phải p95 hay chứng nhận accuracy trên mọi PDF; giữ nguyên FIX-03b trước đó.
- [ ] **ASK-08 — Review input/gold, giữ mở:** F02/F05/N03 cần nêu trường trong
  input hoặc nghiệm thu hành vi hỏi rõ nguồn; không dùng school label để trả thay.
  F24 cần bằng chứng quy định số tuần **từng kỳ** hoặc gold abstention đã review;
  tổng 30 tuần/năm không chứng minh mỗi kỳ tối thiểu 15 tuần. Không tự sửa gold,
  không đếm bốn ca thành PASS. Fresh holdout/public release vẫn theo gate riêng.

Không hard-code bộ owner vào runtime, không đưa gold/nhãn vào inference và
không hạ gate grounding/citation. Hoàn tất goal này là đóng các lỗi hỏi đáp đã
xác định và kiểm chứng; fresh holdout/review gold/public release vẫn theo gate riêng.

## Những lỗi đã xử lý

| ID | Kết quả |
|---|---|
| FIX-01 | OCR tự động, giữ cancel/retry và lịch sử job |
| FIX-02 | Hỏi trên phần đã đọc, hiển thị coverage và số trang gốc |
| FIX-03a | Tiếp tục OCR từ checkpoint hợp lệ qua các lô/restart |
| FIX-04a | Tách câu trả lời chính, trích đoạn và lỗi provider/quota |
| FIX-04b | Giữ điều kiện/deadline và quan hệ bảng khi phân bổ context |
| FIX-06 | Chờ slot có giới hạn thay vì từ chối ngay khi AI bận |
| FIX-07 | Chia lượt qua ba project Gemini độc lập, giữ quota/cooldown |
| FIX-08 | Sửa từ chối nhầm đã tái hiện, đổi trường khi hỏi tiếp và quy đổi điểm từ nguồn |
| FIX-09 | [x] DONE — Nhận diện trường từ metadata/nội dung nguồn, xác minh khi quy định chưa rõ trường; giữ câu hỏi qua xác nhận/đổi trường. Sách, bài báo, hướng dẫn và PDF khác vẫn hỏi đáp nội dung bình thường. 25 tests PASS; HTTP 3 lượt đúng nguồn. |
| FIX-09b | [x] DONE — Khi viết tắt chưa có trong PDF, tối đa 1 lượt Gemini đối chiếu với tên trường trong nguồn được chọn; chỉ khớp rõ một trường mới tiếp tục câu hỏi gốc. Mơ hồ/lỗi API thì nói rõ và hỏi tên đầy đủ. Native `hust/HUST/Hust` đúng nguồn, chỉ 1 lượt đối chiếu; 44 tests liên quan PASS. |
| FIX-10 | [x] DONE — Thêm nút “Chọn tất cả” trong bộ chọn nguồn. Chọn mọi PDF sẵn sàng, không giới hạn 5 tài liệu; cập nhật checkbox và nút chọn/bỏ chọn đồng bộ. Kiểm tra callback/render PASS với 6 PDF sẵn sàng và 1 PDF chưa sẵn sàng. |
| FIX-11 | [x] DONE — Giữ chủ đề và trường đang hỏi khi nối tiếp/đổi trường (HUST → NUAE → HUST); tái dùng câu trả lời đã kiểm chứng đúng nguồn. 143 tests liên quan PASS; đã kiểm tra HTTP thật. |
| FIX-12 | [x] DONE — Câu hỏi tổng số trang bằng dạng số nhiều PDF/file được trả lời bằng metadata: HTTP thực tế 0,049s, không gọi model. |
| FIX-13 | [x] DONE — Tách “học trước” khỏi “tiên quyết”, bổ sung truy hồi địa chỉ/khóa áp dụng và nhận diện so sánh “giống/khác nhau”; vẫn chặn mâu thuẫn trong cùng nguồn. |
| FIX-14 | [x] DONE — Tra giới hạn đăng ký và khóa áp dụng từ mệnh đề nguồn rõ ràng, giữ điều kiện năm cuối, mức cảnh báo và học kỳ; không có nguồn đúng mẫu thì giữ pipeline model. Bốn ca HTTP 0,51–0,98s. |

## Hạ tầng bổ sung — 31/10/2026
- [x] **Supermemory:** dừng theo yêu cầu; không thêm SDK, key hoặc gửi hội thoại tới dịch vụ này.

- [x] **CI/CD implementation:** thêm GitHub Actions cho Windows/Linux, package và Docker;
  Release publish image GHCR, deploy opt-in có health check/rollback. 56 tests local
  PASS, Compose config PASS. Hướng dẫn: [ci-cd.md](docs/operations/ci-cd.md).
- [x] **CI run:** [run 41192650931](https://github.com/trbk07/campusai-university-rag/actions/runs/41192650931)
  trên source `dadfcfa0` PASS: 56 tests ở cả 4 môi trường, package, build image CPU,
  entrypoint và Compose. Publish/deploy chưa chạy vì chưa tạo Release/máy đích.
- [x] **Docker Windows prerequisites:** đã bật Virtual Machine Platform và WSL feature.
- [x] **WSL:** đã cài WSL 3.0.3 từ MSI Microsoft, kiểm tra SHA-256 và chữ ký hợp lệ.
- [x] **Docker local:** virtualization/hypervisor đã hoạt động sau restart;
  Docker Desktop 4.89.0 / Linux Engine 29.7.2 và container `hello-world` PASS.
  Đây là kiểm tra Engine, chưa phải nghiệm thu CampusAI chạy trong container.
- [ ] **Production deployment:** cần máy Linux/runner và environment; chưa triển khai thực tế.

## Nghiệm thu đang chốt — 01/11/2026

- [x] **FIX-03b — DONE:** 20 trang ảnh thật / 3 PDF, lặp 3 lần; 60/60 lượt trang,
  0 lỗi/timeout; p95 **1,874s/trang**, **12,676s/batch**. Workload/threshold được
  khóa trước đo. Đây là đo tốc độ OCR; độ đúng ký tự thuộc QA-07c.
- [x] **QA-03b — DONE:** khóa đủ 5 loại: native, scan, mixed, bảng trên PDF đang
  giữ, cộng 1 PDF font-mapping lỗi **có kiểm soát, ghi rõ synthetic**. Fixture font
  tái tạo được bằng test; không thay kiểm chất lượng font lỗi thực tế.
- [ ] **QA-07c:** đo extraction ≥98%, OCR ≥90%, evidence/retrieval ≥95% trên bộ
  đại diện với reference được review; không dùng confidence OCR thay accuracy.
- [x] **FIX-05a — DONE phần sửa đã kiểm:** giữ ý định câu hỏi tiếp; trả đủ điểm
  chữ/hệ 4 và so sánh bằng chứng riêng từng nguồn; xử lý đăng ký hè khẩu ngữ,
  học phần học trước; chặn suy diễn tổng tuần cả năm thành một học kỳ và kết luận
  thiếu thông tin khi chưa kiểm đủ nguồn. Không dùng ID/đáp án benchmark trong runtime.
- [ ] **FIX-05 — nghiệm thu chất lượng cuối:** phần sửa lỗi và chấm dev **DONE**
  ở ASK-01–ASK-06: đủ 60 lượt trên `cacb4bdd`, **52 PASS / 0 PARTIAL / 4 REVIEW_REQUIRED**.
  C04, điều kiện và nhánh local đã khắc phục. Còn review gold F24, scope
  F02/F05/N03 và nghiệm thu chính thức; không dùng điểm dev của bộ đã exposure
  thay independent review/holdout hoặc tự tạo owner sign-off.
- [x] **R-01 — DONE qualification profile trên `3289f41f`:** 112/112 HTTP,
  83 inference provider thật, 0 timeout/lỗi HTTP, 0 cache hit; p95 **8,514s**,
  RSS đỉnh **8,00% RAM**. Đạt nguyên ngưỡng ≥100 HTTP/≥54 inference, p95 ≤10s,
  timeout ≤0,5%, RSS ≤75%; không reset quota. Receipt: `owner112-final.json`.
- [x] **R-02 — DONE trên cùng lượt 112:** public schema/citation vật lý hợp lệ
  112/112; provider thực báo `gemini-3.5-flash-lite`, bind profile/index/source hash.
  Không có lỗi output schema. Đây không phải chứng nhận độ đúng semantic.
- [ ] **Fresh holdout:** đóng băng tập chưa exposure, protocol/ngưỡng trước đo;
  không dùng tập đã tuning làm holdout.
- [ ] **QA-09d:** vòng kiểm cuối và bàn giao candidate đã khóa.

R-01/R-02 ghi đúng bản đã đo. Bản vá parser bullet GPA sau `3289f41f` đã kiểm
tập trung: **4/4 HTTP PASS** trên `fc8a56af`; N06 trả đúng literal nguồn trong
0,539s, không cache/provider; 3 lượt còn lại dùng cache đã kiểm chứng. Nghiệm thu
chất lượng và bàn giao toàn bộ bản mới vẫn nằm ở FIX-05/QA-09d.
Hồi quy hiện hành trên `cacb4bdd`: **173 tests hiện tại + 164 tương thích = 337 PASS**;
1 test lịch sử thiếu fixture đã dọn không chạy, không tính PASS. Kết quả
106 + 164 trên `fc8a56af` giữ là mốc lịch sử.

Evidence local đang giữ: `data/operations/local-acceptance-20261101/`.
Lệnh đo dùng `scripts/release/measure_ocr.py`, collector HTTP dùng
`scripts/release/verify_answers.py`; không gửi expected/gold/school vào inference.
Chi tiết kết quả mới cập nhật tại [báo cáo tổng quan](docs/PROJECT_OVERVIEW.md).

Streaming mặc định OFF; p95 TTFT ≤5 giây chưa đạt nghiệm thu. Graph/reranker OFF.
R-03 cloud đã rút khỏi scope, không ghi PASS.

<a id="phase-13"></a>
<a id="bo-sung-phase-13"></a>
## Phase 13 — Cài đặt và đóng gói local

Đã có triển khai encoder pin, launcher, state root và script đóng gói; chưa
chốt nghiệm thu RC/cài sạch.

| Task | Việc cần hoàn tất |
|---|---|
| L13-01 | Khóa Windows/Python/browser, máy tham chiếu, profile/OCR/flags và giới hạn PDF |
| L13-02 | Dependency từ lock, revision/hash model, dung lượng và giấy phép |
| L13-03 | Source từ commit sạch, đủ UI/config/launcher/docs, không kèm secrets/state |
| L13-04 | Cài sạch gói phân phối vào đường dẫn có khoảng trắng, state/model riêng |
| L13-05 | Xác minh state root, quyền ghi/preflight và giữ quota/cooldown |
| L13-06 | Chốt hướng dẫn cài, dùng, backup/restore và lỗi thường gặp |
| L13-07 | Khóa candidate: source commit, ZIP/hash, dependency/model/profile |

Hướng dẫn: [local-install.md](docs/operations/local-install.md).
Asset: [runtime-assets.json](configs/local/runtime-assets.json).

<a id="phase-14"></a>
<a id="bo-sung-phase-14"></a>
## Phase 14 — Kiểm chứng và bàn giao

| Task | Điều kiện hoàn tất |
|---|---|
| L14-01 | Ma trận requirement → protocol/ngưỡng → kết quả và vấn đề còn mở |
| L14-02 | PDF đại diện, câu trả lời, citation và holdout; giữ cả ca lỗi |
| L14-03 | Đo riêng startup/upload/query, cold/warm/cache, latency/errors và RSS |
| L14-04 | Dữ liệu, secrets/dependency, local HTTP, upload và quyền nguồn trên gói cuối |
| L14-05 | Backup/restore và rollback thật, giữ PDF/job/quota/cooldown |
| L14-06 | Chẩn đoán version/profile, model/OCR, lỗi provider và vị trí dữ liệu |
| L14-07 | Ba lượt hồi quy đầy đủ trên RC cuối, smoke UI/HTTP, kiểm nguồn và ảnh hưởng source |
| L14-08 | Owner duyệt candidate cụ thể cùng hướng dẫn, giới hạn và cách quay về bản trước |

Mốc R-01 cũ: 100 HTTP/54 provider calls, p95 ≤10s, timeout ≤0,5%, RSS ≤75% RAM.
Nếu đổi workload local, khóa protocol mới trước chạy và báo riêng. Mốc PDF
đại diện: extraction ≥98%, OCR ≥90%, evidence/retrieval ≥95%, không mất/nhầm
trang. Đây vẫn là mục tiêu, chưa được xác nhận bởi đợt dọn file.

Thứ tự: chốt QA PDF/profile → cài và đóng gói → khóa candidate → kiểm chất
lượng/provider/dữ liệu/recovery → vòng cuối → owner duyệt bàn giao. Chỉ cập
nhật trạng thái có căn cứ; không tự mở lại task đã đóng.

## Duy trì

Giữ source, cấu hình chạy/cài, hướng dẫn và dữ liệu/model đang sử dụng. Kết quả
kiểm tra mới cập nhật vào báo cáo tổng quan; xóa đầu ra tạm khi hết cần thiết.
Đợt tinh gọn không tuyên bố nghiệm thu bản cuối, không gọi API chỉ để tạo báo
cáo và không reset quota. Commit/push qua `origin` CampusAI; legacy financial
remote chỉ để fetch.
