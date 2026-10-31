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
- [ ] **FIX-05:** nghiệm thu chất lượng/tốc độ trên cùng candidate cuối. Đã chạy
  đủ 60/60 lượt owner ở baseline: schema/citation vật lý đều hợp lệ, 0 timeout,
  p95 15,098s nên chưa đạt tốc độ. Các lỗi đã tái hiện được sửa và kiểm riêng;
  cần chấm lại toàn bộ trên candidate khóa. F24 vẫn `review_required`;
  F02/F05/N03 thiếu trường khi chọn cả 3 PDF, không đưa cột school vào inference.
- [ ] **R-01:** đo lại 100 HTTP / ít nhất 54 inference provider thành công,
  p95 ≤10s, timeout ≤0,5%, RSS ≤75% RAM, profile phân phối và quota hiện có.
  Đếm RPC inference thật, tách local answer/cache/countTokens; chưa ghi PASS.
- [ ] **R-02:** kiểm schema/public citation và model/config version thực nhận
  trên chính lượt candidate cuối; không ghép cohort khác source.
- [ ] **Fresh holdout:** đóng băng tập chưa exposure, protocol/ngưỡng trước đo;
  không dùng tập đã tuning làm holdout.
- [ ] **QA-09d:** vòng kiểm cuối và bàn giao candidate đã khóa.

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
