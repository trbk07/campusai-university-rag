# Kiểm tra câu trả lời với bộ QA chủ dự án cung cấp — 31/10/2026

Đã khắc phục các ca từ chối nhầm được tái hiện: quy đổi bảng điểm, đổi trường ở câu tiếp theo, giới hạn tín chỉ, phúc khảo và so sánh hai nguồn. App local dùng `configs/free_multi_project.yaml`. Các câu thiếu bằng chứng vẫn được từ chối; không đổi ngưỡng kiểm chứng.

## Những phần đã sửa

- Xác định trường từ tiêu đề thật trong nguồn, giữ chủ đề khi hỏi tiếp và thay trường/kỳ học theo câu mới. Không dùng danh sách câu hỏi hay bảng đáp án trong runtime.
- Giữ đúng quan hệ hàng/cột của bảng điểm, đoạn văn bị tách thành ô và đơn vị `TC`/`tín chỉ`. Khi có quy tắc quy đổi duy nhất trong một nguồn, tính trực tiếp từ khoảng điểm và điểm số được in trong nguồn; vẫn kiểm tra citation/claim như câu trả lời thông thường.
- Dành chỗ cho từng nguồn khi so sánh; ưu tiên đoạn quy định hạn mức và giữ cả điều kiện lẫn con số khi cắt context. Trước sửa, context của Thủ đô bị mất đoạn quy định cho sinh viên bình thường dù đã truy hồi đúng chunk.
- Với output model dương tính bị chặn, profile web cho phép tối đa một lần sửa cách diễn đạt trên cùng evidence. Câu sửa phải vượt lại toàn bộ kiểm chứng; không thử lại lỗi HTTP, không nối thêm lượt full-document sau khi đã dùng lượt sửa này.
- Không tự mở rộng tên đầy đủ của trường khi evidence không chứng minh được. Lượt kiểm tra từng phát hiện tên NUAE bị model viết thành một trường khác dù các quy định được trích đúng.
- PDF scan Thủ đô được OCR lại bằng Tesseract `vie+eng`, giữ nguyên PDF gốc. Đo trên 34 trang: OCR cũ 237,925s; OCR mới 21,805s. Đây là phép đo trên tài liệu này, không phải cam kết tốc độ cho mọi PDF.

## Kết quả thực tế

Giữ nguyên CSV/Markdown chủ dự án đưa: **56 case, 60 lượt**. Mỗi lượt chọn cả ba PDF HUST, NUAE, Thủ đô; câu hỏi tiếp dùng lịch sử trả lời thật. Runtime không đọc `expected`, `school`, `source`, `pass_criteria` hoặc đưa gold vào model.

| Lượt kiểm tra | Hoàn tất | Câu trả lời / abstain | Lỗi provider | Thời gian hoàn tất |
|---|---:|---:|---:|---|
| Baseline trước sửa | 60/60 | 28 / 32 | 0 | Trung vị khoảng 2,24s |
| Toàn bộ sau sửa nguồn/OCR, trước phục hồi cuối (`run-final`, v53) | 60/60 | 48 / 12 | 0 | Trung vị khoảng 2,00s; p95 2,827s |
| Kiểm lại 7 case, 9 lượt (`run-repair-final`, v55) | 9/9 | 7 / 2 | 0 | Trung vị 2,643s; p95 8,640s, gồm thời gian chờ/sửa output |
| Hai case quy đổi còn lại (`run-grade-final`, v57) | 3/3 | 3 / 0 | 0 | 0,440–1,555s; **0 calls Gemini**, không cache |

Ba lượt cuối trả đúng: Bách khoa **A / 4,0**, rồi đổi sang NUAE **A / 3,7**. Đây là suy luận local từ nguồn, không được tính thành model predictions. Các lượt gọi model khác là API thật; không dùng output sinh từ gold. Các lượt thuộc những phiên bản kế tiếp nhau, **không phải một lượt đủ 60 câu trên bản cuối**.

Kiểm tra vật lý citation đối chiếu với index đúng thời điểm: baseline 30, lượt v53 53, lượt v55 9 và lượt v57 4 citation đều khớp chunk thuộc đúng tài liệu, trang và quote/phép chiếu bảng hợp lệ. Kiểm tra này không thay thế đánh giá ngữ nghĩa.

Thử nghiệm riêng Gemini 3.1 hoàn tất 60 lượt nhưng có 3 timeout và p95 47,716s; đã quay về 3.5. Source cũng thay đổi giữa các lượt, vì vậy không coi đây là A/B để xếp hạng chất lượng model.

## Chất lượng còn phải theo dõi

[Bảng đánh giá từng case](evidence/owner-golden-qa-20261031.csv) đối chiếu với gold gốc. Đánh giá do assistant thực hiện, không phải independent review hoặc owner sign-off mới.

- Lượt toàn bộ v53: **31 PASS, 18 PARTIAL, 6 FAIL, 1 REVIEW_REQUIRED**.
- Kết quả mới nhất quan sát được, gộp các lần kiểm lại đã ghi rõ cohort: **36 PASS, 19 PARTIAL, 1 REVIEW_REQUIRED**. Không gọi số này là accuracy của một lượt nghiệm thu bản cuối.
- PARTIAL gồm các câu đúng ý chính nhưng chưa nói hết ý bổ sung/điều kiện trong gold: thời gian chuẩn, ngoại lệ phúc khảo, điều kiện hoãn thi đã học/đóng học phí, hoặc điều kiện khác của khóa luận. Công việc chất lượng tổng thể `FIX-05` vẫn mở.
- **F24 cần review gold:** gold ghi tối thiểu 15 tuần/học kỳ; đoạn kiểm tra được ở trang PDF 6 ghi **không vượt quá 15 giờ/tuần** cho một học phần học tập trung. Quy định 2 học kỳ chính với tổng tối thiểu 30 tuần/năm chưa chứng minh từng học kỳ ít nhất 15 tuần. Giữ nguyên gold và `review_required`; không ép app trả 15 tuần.
- N03 không nêu trường. Không dùng nhãn `school=HUST` trong CSV để ngầm chỉ đường inference khi cả ba PDF đang được chọn.

Không dùng bộ đã quan sát/tuning này làm fresh holdout, không đổi release thresholds hoặc tự tuyên bố grounding public release PASS.

## Tái hiện và evidence

Source/config/index/PDF hashes, raw outputs của cả các lượt lỗi, runtime-only packets, collector và test reports được giữ trong artifact `evaluation/results/owner-golden-qa-20261031/reproduction.zip`, đăng ký tại [manifest](../../evaluation/artifacts/manifest.json). Chỉ archive ba nguồn công khai trong bài kiểm; không có API key hoặc `.env`.

Gói raw nằm trong kho local `.local_artifacts` theo cơ chế hiện có; Git giữ manifest và báo cáo, không đẩy bản sao raw lên GitHub. Giữ kho này để lệnh restore bên dưới hoạt động.

Bảng CSV công khai giữ ID, kết quả và nhận xét; bản question/gold gốc nằm trong bundle local, không chép lại thành dataset công khai.

```powershell
.venv\Scripts\python.exe -m scripts.dev.manage_artifacts restore evaluation/results/owner-golden-qa-20261031/reproduction.zip
```

Số test cuối và binding archive được ghi trong [evidence hiện hành](evidence/owner-issues-20261030.json). Các thư mục fixture/draft tạm được xóa sau khi kiểm tra archive; source, tests, baseline và dữ liệu cần audit được giữ.

Bản cuối: **3.740 PASS, 2 live opt-in SKIP** trên mã đã đóng băng; **427 focused PASS**. Export chỉ source/config/tests đã stage cũng **427 PASS**, xác nhận patch không phụ thuộc việc gộp các thay đổi encoder/packaging đang có riêng trong worktree. Hai lượt 427 là cùng bộ test, không cộng thành 854.
