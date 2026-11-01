# CampusAI — Roadmap local

Cập nhật: **01/11/2026 · Asia/Bangkok**.

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

## Goal hiện tại — cải thiện hỏi đáp PDF

Goal active ngày **01/11/2026**. Tập trung chất lượng trao đổi với người dùng,
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
  trong lượt 60 HTTP trên `f5a5356f`; C03/C04 kiểm lại trên `190fa8bb` không cache.
  Tests vẫn chặn mâu thuẫn nội bộ, tên bịa, sai phủ định và số liệu tráo nguồn.
- [ ] **ASK-03 — Câu trả lời đủ nghĩa:** giữ điều kiện, ngoại lệ, thời hạn và
  đối tượng áp dụng. **Code đã DONE cho các lỗi đã tái hiện:** giữ điều kiện trong
  cùng danh sách, ngoại lệ ở câu liền sau và khoảng điểm làm căn cứ; kiểm chứng
  lại thay vì hạ gate. Giải thích thiếu bằng chứng thời lượng từng kỳ; không nhận
  tài liệu không đề cập chỉ từ tổng thời lượng năm. Tránh lặp ghi chú khi ngoại lệ
  đã hiện rõ. **F01 DONE trên `9ec52954`:** đủ tín chỉ và thời gian từ cùng hàng
  bảng đã kiểm chứng, không đoán nhóm đầu vào, không thêm lượt AI. **Còn:** 8 ca
  trong backlog PARTIAL và 4 ca review nguồn/scope;
  danh sách và phạm vi review nằm trong báo cáo tổng quan. Không tự tính thành PASS.
- [x] **ASK-04 — Hội thoại tự nhiên DONE trong phạm vi lỗi đã xác định:** 4 hội thoại
  M01–M04/8 lượt giữ đúng trường, điểm, học kỳ và chủ đề. Role “hiệu trưởng” không
  còn bị nhận nhầm thành tên trường; thiếu thời điểm thì yêu cầu nguồn cập nhật.
  Regression dùng tên/đối tượng giả, không whitelist trường hoặc câu hỏi owner.
- [x] **ASK-05 — Tốc độ DONE trong workload đã đo:** 60 HTTP trên `f5a5356f`,
  p95 **4,513s**, tối đa **8,423s**, không timeout; 25 lượt local, 0 cache,
  35 lượt có provider/36 attempts. Giữ quota/cooldown; không đổi chất lượng lấy tốc độ.
- [ ] **ASK-06 — Chốt:** regression cả ca đúng/sai/phản chứng và HTTP trên bản
  đang chạy. **Đã xong:** 149 tests hiện hành + 164 tests tương thích PASS,
  1 test cũ thiếu corpus không chạy; 7 HTTP trọng tâm trên `9ec52954` không cache,
  đúng hành vi và schema/citation, code đã push origin CampusAI. **Còn:** hoàn thiện
  chất lượng/rubric; lượt đủ 60 gần nhất trên `f5a5356f` là 43 PASS / 9 PARTIAL /
  4 REVIEW_REQUIRED. F01 kiểm riêng sau đó; chưa ghép kết quả thành điểm cohort mới
  hoặc nhận đạt mốc 99–100%.
- [x] **ASK-07 — OCR nhanh hơn DONE (`c54b2b8b`):** OCR song song có giới hạn,
  lô tăng theo tốc độ thực và chỉ encode đoạn mới/thay đổi. PDF scan 34 trang:
  toàn bộ pipeline **52,81 → 29,48s**, phần đầu sẵn sàng **4,27s**, đủ 34/34 trang;
  hash toàn văn giống baseline. Hai PDF scan/mixed chạy cùng lúc: OCR **14,92 →
  4,65s**, text/layout/confidence giống bản tuần tự. Đã kiểm cancel, partial timeout,
  checkpoint, giới hạn worker và rollback index. Đây là A/B warm một lượt/workload,
  không phải p95 hay chứng nhận accuracy trên mọi PDF; giữ nguyên FIX-03b trước đó.

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
- [ ] **FIX-05 — chất lượng cuối:** đã có một lượt đủ 60 câu gốc trên `3289f41f`
  (nằm trong 112 HTTP), không còn ghép cohort để báo đủ 60. Vẫn cần chấm semantic
  và điều kiện đầy đủ; C04 còn từ chối. F24 cần review gold; F02/F05/N03 cần review
  scope, không đưa nhãn school vào inference. Bản vá bullet GPA sau đó kiểm riêng,
  không ghép vào lượt 112 để tự nhận bản cuối PASS.
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
Hồi quy gần nhất: 106 tests hiện tại + 164 tests tương thích = **270 PASS**;
1 test lịch sử thiếu fixture đã dọn không chạy, không tính PASS.

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
