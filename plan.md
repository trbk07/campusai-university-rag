# CampusAI — Roadmap local

Cập nhật: **31/10/2026 · Asia/Bangkok**.

Đích phát hành: **Windows x64, một người dùng, chạy local**. Gemini cần mạng và
credentials riêng. Giữ `plan.md` tại root và tracked Git đến khi chủ dự án xóa.

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

## Ưu tiên còn mở

- [ ] **FIX-03b:** đo p95 OCR trên PDF ảnh thực tế với workload xác định.
- [ ] **FIX-05:** kiểm chất lượng/tốc độ trên cùng bản cuối. Bộ owner gần nhất
  còn 19 PARTIAL và F24 cần review nguồn/gold; cohort gộp không phải một lần
  chạy đủ 60 lượt trên bản cuối.
- [ ] **QA-03b / QA-07c:** chốt PDF đại diện: native, scan, mixed, bảng, lỗi font.
- [ ] **R-01 / R-02:** hiệu năng, availability và format API thật trên profile
  phân phối; vẫn **NOT PASSED**.
- [ ] **Fresh holdout:** đóng băng tập chưa exposure, protocol/ngưỡng trước đo;
  không dùng tập đã tuning làm holdout.
- [ ] **QA-09d:** vòng kiểm cuối và bàn giao candidate đã khóa.

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
