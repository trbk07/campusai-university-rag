# Phase 7 — kiểm chứng chất lượng qua Gemini Chat

Chỉ gửi các file `batch-01.md`, `batch-02.md`, `batch-03.md` lên Gemini Chat.
Mỗi file đã có toàn bộ prompt, nguồn được truy xuất và JSON Schema; không cần
đính kèm PDF, rubric, manifest, đáp án chuẩn hoặc file cấu hình/key.

Chọn Gemini 3.8 Flash nếu giao diện có tùy chọn này. Mở một cuộc trò chuyện mới
cho mỗi batch, đính kèm đúng một file và dùng prompt:

> Xử lý toàn bộ INPUT trong file đính kèm theo đúng hướng dẫn và schema của từng
> INPUT. Chỉ dùng nguồn có trong chính INPUT đó; không dùng web hoặc suy luận
> từ INPUT khác. Giữ nguyên case_id. Trả kết quả thành file UTF-8 JSONL, mỗi dòng
> là {"case_id":"...","response":{...}}. Escape đúng dấu nháy và xuống dòng trong
> quote; ưu tiên dùng JSON serializer nếu có công cụ. Không bỏ sót, gộp câu hoặc
> rút ngắn đáp án để vừa đầu ra. Nếu bị cắt, dừng ở record hoàn chỉnh và nêu riêng
> case_id chưa xử lý; không tự nhận đã hoàn tất.

Số INPUT cần nhận: batch 01 **24**, batch 02 **24**, batch 03 **20**. Lưu file
kết quả từng batch và đưa lại cho Codex. Có thể ghi kèm tên model hiển thị và
thời điểm; không coi thông tin tự khai trong câu trả lời là API modelVersion.
Nếu Chat không tạo file, sao chép nguyên JSONL, không sửa quote/citation bằng tay.

Đây là **68 lượt model của hai nhánh trên cùng 68 câu primary**: 42 current và
26 baseline. Các nhánh không cần gọi model vẫn phải chạy qua ứng dụng khi replay.
Các ID xuất ra đã được ẩn nhãn nhánh để giảm thiên lệch khi trả lời. Không có
gold/rubric hoặc kết quả nghiệm thu trong file đưa cho Chat. Corpus, split,
comparator, rubric và ngưỡng cũ giữ nguyên; dữ liệu đã exposure, không phải fresh.

Pipeline sau khi nhận output:

Kết quả gộp 68 câu đã nhận và review ngày 13/10: [C7-03 PASS](../../results/phase7-chat-quality-20261013/paired-quality-review.json).
Sau sửa grounding mã môn có tiền tố và cache policy v5, 42/42 câu dương và
26/26 câu âm đúng qua ứng dụng. Giữ cả bản JSON lỗi và bản xuất lại; không cần
gửi lại ba batch. Lệnh tái hiện đúng bộ đã nhận:

```powershell
.venv\Scripts\python.exe evaluation/results/phase7-chat-quality-20261013/review-chat-outputs.py.txt
.venv\Scripts\python.exe evaluation/results/phase7-chat-quality-20261013/review-paired-application.py.txt
```

Lệnh import cho các lần thu batch riêng (không chạy lại trên receipt đã tồn tại):

```powershell
.venv\Scripts\python.exe -m scripts.benchmarks.product_chat_quality import --batch 1 --input <file-output-batch-01.jsonl>
.venv\Scripts\python.exe -m scripts.benchmarks.product_chat_quality import --batch 2 --input <file-output-batch-02.jsonl>
.venv\Scripts\python.exe -m scripts.benchmarks.product_chat_quality import --batch 3 --input <file-output-batch-03.jsonl>
.venv\Scripts\python.exe -m scripts.benchmarks.product_chat_quality replay
```

Importer lưu nguyên raw, báo thiếu/trùng/schema lỗi, không tự sửa escaping và
không nhận schema PASS là chất lượng PASS. Replay cần đủ cả ba batch, kiểm tra
body/evidence của từng nhánh và chặn transport ra ngoài. Sau đó Codex review
từng claim/citation theo nguồn gốc và rubric, tính đủ các denominator theo split,
false abstention và so sánh baseline trước khi quyết định C7-03.

Gemini Chat không thay cho nghiệm thu API latency/availability, usage/token/cost
hoặc hai live integration. Không tự bật lại API packet cũ. C7-05 và phần live của
C7-06 vẫn cần bằng chứng riêng; không có tuyên bố 6/6 DONE ở bước xuất file này.
