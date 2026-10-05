# Xác nhận nguồn gốc và review nhóm của bộ 180 câu — đã duyệt

Ngày lập: **02/10/2026**, Asia/Bangkok. Chủ dự án: **Trương Bảo Kiên**

## Dữ liệu được xác nhận

- File gốc: `data/benchmark/human_candidate_pool.jsonl`, **180 câu**.
- SHA-256: `324507c978335f4c858d854b08252af59b024f979780d281d09590e02f8d6277`.
- Các câu do chủ dự án và nhóm nghiên cứu soạn theo cách hỏi tự nhiên của người dùng.
- Nhóm đã cùng thảo luận, kiểm chứng và thống nhất nội dung; trước phiên làm việc này
  chưa có bản xác nhận riêng bằng văn bản.
- Không yêu cầu viết lại câu chỉ vì văn bản trùng với dataset khác. Bước chuẩn hóa giữ
  nguyên file gốc và câu hỏi, thêm qid ổn định, schema/correction log và lineage.

## Cách review đã được chủ dự án mô tả

**Review đồng thuận của nhóm nghiên cứu**. Nhãn cũ `Independent Reviewer` là tên
vai trò chung, không phải danh tính một người review đã được đối chiếu.

Với thông tin hiện có, chưa xác định thành viên nào review riêng các câu do người
khác viết. Bản này không tự khẳng định review độc lập với tác giả. Nếu có review như
vậy, nhóm có thể bổ sung mã định danh ổn định của reviewer, phạm vi câu và quyết định;
không cần công khai thông tin cá nhân nhạy cảm hoặc tạo lịch sử review giả.

## Những việc vẫn phải kiểm chứng bằng artifacts

1. Scope của **45 câu negative**: file gốc chưa có danh sách doc IDs rõ ràng cho chúng.
2. Đối chiếu exposure: **89 câu** có bằng chứng từng được đo trên dev; **91 câu** còn
   chờ audit đủ lịch sử. Tổng **155 câu** trùng văn bản với dataset sẵn có. Trùng văn bản
   và đã exposure là hai thông tin riêng; cả hai không dùng để suy tác giả là AI.
3. Review packet gắn với đúng question/context/evidence/index hash; grouping/splits
   phải được kiểm tra trước freeze. Dataset staging hiện có **59 connected groups**.
4. Ranking, answer/citation, GPU capacity, lỗi/rollback và staging phải được thực đo
   trên cấu hình freeze. Xác nhận này không xác nhận các metric hoặc điểm 10.

## Nội dung được chủ dự án duyệt

“Tôi xác nhận phần **Dữ liệu được xác nhận** và **Cách review đã được chủ dự án mô tả**
phản ánh đúng quá trình làm việc của nhóm đối với file và SHA-256 nêu trên.”

Trạng thái: **ĐÃ ĐƯỢC CHỦ DỰ ÁN DUYỆT QUA CHAT**.

Người duyệt: **Trương Bảo Kiên**.

Thời điểm ghi nhận duyệt (Asia/Bangkok): **2026-10-02T23:43:29+07:00**.

Phạm vi review độc lập: **chưa bổ sung thông tin**; xác nhận hiện tại ghi nhận
review đồng thuận của nhóm nghiên cứu như mô tả ở trên.

Roadmap: [plan.md](../../plan.md#phase-7--reranker).
Lineage: [human_candidate_lineage.json](../../data/benchmark/human_candidate_lineage.json).
Exposure: [phase7_exposure_registry.json](../../data/benchmark/phase7_exposure_registry.json).

## Cập nhật quy trình theo chỉ đạo của chủ dự án — 03/10/2026

Chủ dự án xác nhận đây là project cá nhân và cho phép **owner review/self-approval**
thay cho yêu cầu reviewer độc lập. Các báo cáo phải ghi rõ `owner_self_review`; không
được mô tả quyết định đó là review độc lập. Chỉ đạo này thay đổi vai trò reviewer,
không tự duyệt câu hỏi, scope, gold evidence hay lịch sử exposure. Quyết định từng
record vẫn cần được chủ dự án ghi vào packet có hash; các lịch sử chưa xác minh vẫn
không đủ điều kiện làm held-out.
