# Ghi chú quy trình review Phase 7

Ngày soạn: **02/10/2026**, cập nhật **03/10/2026**, Asia/Bangkok. Trạng thái:
**HỒ SƠ CŨ ĐƯỢC GIỮ LÀM LỊCH SỬ**. Chủ dự án cho phép owner self-review trong
project cá nhân; báo cáo phải ghi `owner_self_review`, không gọi đó là review độc lập.
[Roadmap gốc](../../plan.md#phase-7--reranker).

Hồ sơ mới theo policy này là [cycle owner-review r3](phase7_review_cycles/phase7-release-20261003-r3/phase7_review_questions.draft.md)
và [JSON dossier](../../data/benchmark/phase7_review_cycles/phase7-release-20261003-r3/phase7_review_draft.json).
Nó có **180 câu giữ nguyên văn**, 135 positive, 45 negative, 15 câu có context và 59
connected groups; mọi quyết định vẫn pending. Hashes PDF/BM25, inputs và hồ sơ được
manifest của cycle khóa lại. Chuẩn bị hồ sơ chưa phải approval hay release evidence.

## 1. Những thông tin đã có

Giữ nguyên [xác nhận nguồn gốc đã được Trương Bảo Kiên duyệt](human_review_confirmation.draft.md):
các câu do chủ dự án và nhóm nghiên cứu soạn, cùng thảo luận/kiểm chứng/đồng thuận.
Không cần duyệt lại nguồn gốc. Nhãn `LEGION` được giữ làm alias gốc; nhóm bổ sung
thành viên thực tế khi xác nhận ai là tác giả, ai review câu do người khác viết.

Review đồng thuận đã được ghi nhận. Theo chỉ đạo mới của chủ dự án, người duyệt từng
record có thể là chính chủ dự án. Không cần chờ thành viên khác xác nhận, nhưng người
duyệt vẫn phải kiểm tra nội dung từng câu, giữ nguyên quyết định đúng/sai, ghi đủ bảy
review checks và nộp packet hiện tại. Không dùng timestamp hoặc quyết định được sinh
tự động. Nếu chọn reviewer độc lập cho một record, vai trò đó vẫn phải khác tác giả.

## 2. Đề xuất scope của 45 câu negative

Đề xuất dùng **toàn bộ 10 PDF đã có trong index Phase 6** làm phạm vi kiểm chứng cho
45 câu negative hiện chưa khai báo doc IDs. Danh mục D01–D10, tên PDF và hash nằm
ở đầu [hồ sơ từng câu](phase7_review_cycles/phase7-release-20261003-r3/phase7_review_questions.draft.md#danh-mục-tài-liệu-được-index).
Ba PDF scan-only chưa index không thuộc scope đề xuất này.

Đây là đề xuất để chủ dự án kiểm tra. Một câu có thể cần đổi nhãn nếu một PDF trong
scope chứa bằng chứng trả lời. Không xác nhận no-evidence chỉ vì danh sách gold rỗng.

Chủ dự án ghi quyết định theo từng qid:

- Scope D01–D10: **chờ duyệt**.
- Câu chỉ nên xét một số PDF: ghi qid → doc IDs hoặc mã Dxx.
- Câu thiếu đối tượng/ngành/năm: giữ hoặc sửa `ask_clarification`, ghi lý do cụ thể.
- Câu không có evidence trong scope: xác nhận `abstain` sau khi kiểm tra.
- Câu có evidence: ghi nhãn mới, doc/chunk/page và các điều kiện cần thiết.

## 3. Lịch sử exposure và nhóm câu

Registry hiện có **89 câu xác minh đã dùng trên dev**, **91 câu chưa đủ lịch sử**.
Danh sách câu cần xác minh nằm trong [hồ sơ](phase7_review_cycles/phase7-release-20261003-r3/phase7_review_questions.draft.md#danh-sách-chưa-rõ-exposure).
Trùng văn bản với bộ khác không dùng để suy tác giả; đã dùng để tune/đánh giá là
thông tin riêng, phải ghi dataset/split/cycle và hồ sơ liên quan.

Chủ dự án kiểm tra 91 câu: đã dùng/chưa dùng/chưa biết; nếu đã dùng, ghi mục đích,
thời điểm và vị trí hồ sơ. Chỉ xác nhận “chưa dùng” khi đã kiểm tra lịch sử phù hợp.
Giữ nguyên bằng chứng exposure đã xác minh; không chuyển câu/nhóm đã exposure thành
held-out mới bằng một lần chia lại. Các câu cùng connected group ở cùng split.
Đề xuất dev/test/holdout và F0 sẽ được lập **sau khi** owner hoàn tất xác minh này.

## 4. Quyết định review từng câu

Ghi identity/role của người thực sự review, ngày giờ có timezone, danh sách hoặc khoảng
qid đã kiểm tra và các ngoại lệ. Mẫu phân công:

| Người / mã | Vai trò | Qids thực sự soạn | Qids thực sự review | Ngày giờ review | Hồ sơ / ghi chú |
|---|---|---|---|---|---|
| Trương Bảo Kiên | `project_owner` khi tự review | Alias gốc `LEGION` cần đối chiếu | Chờ duyệt từng qid | Ghi lúc nộp packet | Chưa duyệt từng record |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

Mỗi câu cần đủ bảy tiêu chí: **tự nhiên; answerability; đủ evidence; phạm vi tài liệu
và thời gian; độ khó; leakage; hành vi mong đợi**. Review cả context/selection của
15 câu follow-up. Với positive, kiểm tra từng gold chunk trên PDF, số/đơn vị/mã
môn/ngành/năm/điều kiện và mọi hop. Ghi gold claims cần câu trả lời đáp ứng để soạn
rubric answer/citation trước khi mở held-out. Rubric có quy trình riêng tại
[paired answer review protocol](../reranker/paired_answer_review_protocol.md).

Trong JSON, `decision` là phần để điền; `record`, `record_sha256`, `exposure` và
`evidence_catalog` là snapshot đối chiếu. Giữ bản draft gốc, ghi quyết định vào
bản sao `phase7_review_decisions.json`. Nếu cần sửa nhãn/scope/gold/context, ghi
trong `notes` và các trường xác nhận; sau đó tạo record đã sửa, bind hash mới và
review đúng bytes đó trước khi nộp vào intake. Không dùng approval trên record cũ
để duyệt ngầm record đã sửa.

Có thể trả kết quả qua chat theo mẫu sau, với phạm vi đã thực sự kiểm tra:

```text
Thành viên và phạm vi tác giả/reviewer:
- <mã người>: soạn <qids>; review <qids>; thời điểm <ISO-8601 có timezone>.

Scope negative:
- D01–D10: <duyệt / cần sửa>; ngoại lệ <qid → Dxx, hành vi, lý do>.

Exposure:
- <qids>: <đã dùng / chưa dùng / chưa biết>; hồ sơ <đường dẫn/cycle/split>.

Review câu hỏi/context/gold/bảy tiêu chí:
- <qids>: <duyệt / cần sửa / loại>; ngoại lệ và gold claims <nội dung>.
```

Chủ dự án có thể tự nhập review từng câu bằng vai trò `project_owner`; các mục chưa
được kiểm tra vẫn giữ `pending`. Owner approval không xác minh lịch sử exposure và
không thay thế bằng chứng nguồn cho câu negative.

## 5. Công việc mở sau khi owner review

Ghi quyết định owner, sửa metadata có correction log, kiểm tra packets/hash rồi
lập gap report và F0 dev eligibility. Chỉ thu thêm dữ liệu khi thiếu held-out độc
lập, quota/folds hoặc lực thống kê. Sau đó đo joint dev feasibility, freeze F1/F2/F3
và chạy M0–M12 cùng S1–S6 trên local RTX 4060 theo
[đặc tả Phase 7](../reranker/phase7_task_spec.md).

Phase 7 chỉ đạt **10/10** khi validator và mọi evidence bắt buộc PASS. Hiện dossier
chờ chủ dự án duyệt từng câu và hoàn tất exposure/scope; chưa bật production và chưa
có điểm nghiệm thu 10.
