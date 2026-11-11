# Thay đổi và phần chưa thực hiện

Owner chọn giữ khóa, chỉ phân tích đáp án đã lưu; sau đó cho phép chạy câu thiếu. Không sửa production/config/model/index/PDF trong task này.

Đã thêm hai script đánh giá:

- `scripts/release/audit_saved_three_schools.py`: khớp câu hỏi theo hash Unicode, kiểm case/lượt, dùng một run, giữ gold/missing, xuất trace/CSV/manifest; không có inference.
- `scripts/release/supplement_three_schools.py`: scope một câu chưa có, kiểm central registry và SQLite journal, giữ ba nguồn theo PDF hash, reserve trước POST, không retry và không truyền gold.

Đã tạo báo cáo, review receipts và ảnh PDF làm bằng chứng. Central registry thêm khóa ABS07. Các file runtime và test đã modified trước task được giữ nguyên.

Ưu tiên cho một task sửa tiếp theo (chưa triển khai, không tính là cải thiện):

1. Kiểm tra code hiện tại đã có sửa OCR modifier hay chưa; lỗi OCR R15 là lịch sử, không đủ lý do ghi đè cách sửa mới. Regression bằng PDF/tên/giá trị giả định, dùng pixel làm proof; không hardcode A+ benchmark.
2. Ghi snapshot retrieval trước generation và packed context thật, tách thứ tự retrieval khỏi evidence bổ sung sau đó; observer không thay đổi output/rank/context size.
3. Tái hiện thiếu điều kiện/ngoại lệ trong pipeline bằng fixture tổng quát. Chỉ sửa khi xác định được thông tin bị mất trong packing hay generation; giữ validator nghiêm ngặt.
4. Kiểm temporal gate bằng dữ liệu cohort/ngày giả định; không nới phạm vi phiên bản một cách mù quáng.
5. Rà quyết định validator khi draft đã đúng nhưng final từ chối. Chưa có exact packed prompt nên không tự kết luận prompt LLM là bottleneck.

Không có vòng sửa production, regression production hoặc phép đo trước/sau mới. Không tái chạy các câu đã có đáp án đầy đủ chỉ vì FAIL. Không dùng supplement khác candidate để nâng điểm R15.
