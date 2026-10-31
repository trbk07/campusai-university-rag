# CampusAI — Tổng quan chất lượng và vận hành

**Cập nhật 31/10/2026 · Phạm vi: web app local, một người dùng trên Windows.**

Tài liệu này thay các báo cáo kiểm tra, nghiệm thu, hiệu năng và nhật ký rời.
Các số lịch sử bên dưới được tổng hợp trước khi xóa đầu ra cũ; chúng không
chứng nhận phiên bản hiện tại đã hoàn tất nghiệm thu. Công việc tiếp theo nằm
trong [roadmap](../plan.md); thao tác cài và backup nằm trong
[hướng dẫn local](operations/local-install.md).

## 1. Ứng dụng hiện có

CampusAI nhận PDF, đọc chữ và bảng, OCR nền khi cần rồi lập chỉ mục hybrid.
Người dùng chọn nguồn để hỏi; câu trả lời phải qua kiểm chứng và có citation
theo trang. Nguồn thiếu hoặc chưa đọc đủ được thể hiện rõ thay vì suy đoán
toàn văn. OCR hỗ trợ checkpoint, hủy, thử lại và tiếp tục sau restart.

Gemini sinh câu trả lời qua Internet; model truy hồi và OCR chạy trên máy.
Profile đang dùng là `configs/free_multi_project.yaml`, chia tải qua ba Google
project độc lập đã được chủ dự án xác nhận. Quota, cooldown và số lượt thử vẫn
được kiểm soát; không cam kết miễn phí vô hạn. Streaming, graph và reranker
không nằm trong cấu hình mặc định đang phát hành.

## 2. Kết quả đã quan sát và giới hạn diễn giải

| Nội dung | Kết quả lịch sử | Phạm vi / giới hạn |
|---|---|---|
| Grounding Phase 5 | 400/400 kết quả, 5/5 gates nội bộ | Bộ đã exposure; chưa thay fresh holdout cho bản cuối |
| Natural100 | Accuracy bảo thủ ≥95/100; phát hiện hallucination 0/100; context 15/15, đủ 17 trường | Bộ dev đã dùng để sửa lỗi, không phải tập kiểm độc lập |
| Upload PDF text 100 trang / khoảng 10 MB | 20/20 lượt; p95 12,25s, tối đa 14,16s | CUDA, model/OS cache warm, upload tuần tự; startup đo riêng 42,51s |
| OCR nguồn tiếng Việt 31 trang | 98,38% ký tự; 46,33s; đủ 120 điều | Một tài liệu và reference riêng từ cơ quan xuất bản; không suy rộng mọi scan |
| Liên tục ba project Gemini | 100/100 HTTP hoàn tất; 96 trả lời, 4 abstain; 0 timeout/quota/HTTP failure; p95 4,654s | Thời gian hoàn tất, không phải TTFT; số trả lời không phải accuracy |
| Bộ QA owner 31/10 | 56 case, 60 lượt; tổng hợp mới nhất 36 PASS, 19 PARTIAL, 1 REVIEW_REQUIRED | Ghép các cohort của các phiên bản kế tiếp; chưa chạy đủ 60 lượt trên cùng bản cuối |
| Hồi quy trước đợt tinh gọn | Mốc gần nhất đã ghi: 3.740 PASS, 2 live opt-in SKIP; 427 focused PASS | Kết quả lịch sử, không phải bộ kiểm được giữ trong cây dự án hiện tại |

Các bản sửa đã xử lý nhận diện trường khi hỏi tiếp, quan hệ hàng/cột bảng
điểm, đơn vị tín chỉ, phân bổ bằng chứng giữa hai nguồn và điều kiện khi cắt
context. Quy đổi điểm có quy tắc rõ được tính từ nguồn, vẫn kiểm citation;
không dùng bảng đáp án owner làm dữ liệu inference. Profile web cho phép tối
đa một lượt sửa cách diễn đạt khi output dương tính bị validator chặn và phải
kiểm lại đầy đủ.

Riêng scan Thủ đô 34 trang: lần đo Tesseract `vie+eng` là 21,805s so với OCR cũ
237,925s. Ba lượt quy đổi điểm trả A/4,0 rồi A/3,7 trong 0,440–1,555s, không
cache, không gọi Gemini. Đây là các quan sát trên ca cụ thể.

## 3. Vấn đề chưa đóng

| Nhóm | Việc còn lại |
|---|---|
| Chất lượng câu trả lời — FIX-05 | Kiểm đủ các điều kiện trong câu trả lời, chốt trên một bản cuối; 19 case còn PARTIAL |
| Gold F24 | Nguồn đã xem nói không vượt quá 15 giờ/tuần cho học phần học tập trung; chưa chứng minh từng học kỳ ít nhất 15 tuần như gold. Giữ trạng thái cần review |
| Nguồn mơ hồ | N03 không nêu trường; khi chọn cả ba PDF không được dùng nhãn trường trong CSV để ngầm định hướng inference |
| PDF/OCR — QA-03b, QA-07c, FIX-03b | Hoàn thiện bộ PDF đại diện, đo p95 OCR trên ảnh thật, kiểm scan/mixed/bảng/lỗi font và nguồn/trang |
| Provider — R-01/R-02 | Chưa đạt nghiệm thu đầy đủ hiệu năng, availability và native API format trên profile phân phối |
| Streaming — QA-08c | Mục tiêu p95 TTFT ≤5s chưa được nghiệm thu; giữ OFF mặc định |
| Phát hành local — Phase 13/14 | Cài sạch, khóa RC, holdout, backup/restore/rollback và vòng kiểm cuối còn mở |

Phase 5 DONE nội bộ và các sửa lỗi riêng vẫn giữ nguyên phạm vi lịch sử.
Đợt dọn file không chuyển các mục đang mở thành PASS.

## 4. Phạm vi dọn dự án

Theo yêu cầu của chủ dự án, đã loại các thành phần không tham gia vận hành web
app local: bộ kiểm thử và fixture; mã benchmark/đánh giá/nghiệm thu cũ; dữ liệu
benchmark/corpus dùng thử; JSON/XML/log/ảnh/bundle kết quả; tài liệu phase và
nhật ký trùng lặp; model LLM thử nghiệm; cache tải gói; môi trường Python và
model đóng gói thử; thư mục tạm và kho raw artifact.

Giữ backend/UI, script launcher/setup/đóng gói, profile đang dùng và fallback,
manifest model/OCR, dependency lock, hướng dẫn cài, giấy phép, README, roadmap
và quy tắc repository. Dữ liệu PDF/index/job/cache/quota người dùng được giữ,
kể cả kho local trước đây. `.env` và file key vẫn ở local, được Git ignore.

Đầu ra local không có trong Git đã bị xóa và không còn cơ chế restore artifact
cũ. File từng commit có thể xem trong lịch sử Git. Không viết lại hoặc xóa
lịch sử Git trong đợt này. Muốn tái đánh giá phải chuẩn bị bộ đo phù hợp và ghi
kết quả mới; các con số trong mục 2 chỉ còn là bản tổng hợp lịch sử.

## 5. Dung lượng và xác minh sau dọn

| Thành phần | Trước dọn | Sau dọn |
|---|---:|---:|
| Toàn dự án, gồm môi trường/model/Git | Khoảng 46,31 GB | Khoảng 8,02 GB |
| Python `.venv` đang dùng | 5,15 GB | Giữ nguyên |
| Encoder BGE-M3 đang dùng | 2,29 GB | Giữ nguyên |
| PDF, index và state người dùng còn giữ | — | Khoảng 196 MB |
| Lịch sử Git | Khoảng 380 MB | Giữ nguyên, tăng nhẹ sau commit |
| Ngôn ngữ OCR đang dùng | 4,64 MB | Giữ nguyên |

GB/MB dùng hệ thập phân, tổng kích thước file logic đã đọc được. Một số fixture
bị chặn quyền trước khi khôi phục quyền và xóa nên số trước dọn là xấp xỉ.
Dung lượng trống ổ D tăng khoảng 39,1 GB tại thời điểm đo; có thể chịu tác động
từ hoạt động khác trên cùng ổ. Không cộng hai cách đo thành dung lượng tiết
kiệm. Source, UI, lock và tài liệu chỉ khoảng vài MB; phần lớn 8 GB còn lại
phục vụ runtime trên máy.

Xác minh ngày 31/10/2026:

- **126 bài kiểm tra liên quan PASS** trước khi bỏ bộ test cũ: launcher,
  state/model, HTTP/document API, routing Gemini và OCR nền.
- Tiến trình mới tải được encoder thật; preflight với port trống đạt
  **PREREQUISITES_PASS**, gồm checksum encoder/OCR. Check port 8000 khi app
  đang mở báo `port_in_use`, đúng với server đang hoạt động.
- Đã dừng server cũ để bỏ log bị giữ mở, rồi khởi động lại bằng
  `scripts.operations.local`, cùng `.env`, model và dữ liệu hiện có.
- **9/9 yêu cầu HTTP sau restart trả 200**: health, trang chính, bốn CSS,
  JavaScript chính/chat và API tài liệu. API vẫn nhận đủ **3 tài liệu**, AI
  đã cấu hình, streaming OFF. Không gọi Gemini để tạo báo cáo này.
- Đã đối chiếu SHA-256 của 732 file được bảo vệ sau đợt xóa. Chỉ journal
  SQLite đang hoạt động đổi hash; model, PDF/index, credentials/config và
  source trong lần đối chiếu đó giữ nguyên. Quota/cooldown không bị xóa.
- `uv lock --check --offline` đạt; lockfile dependency không đổi.

Trong lúc dọn có công việc khác tiếp tục sửa runtime và tạo lại
`tests/test_institution_context.py`. Các thay đổi mới này được giữ nguyên;
file test mới thuộc công việc đang diễn ra, không phải bộ nghiệm thu lịch sử.
Không xóa lặp lại file đang được tạo bởi công việc hiện hành.

Các bước trên xác nhận khởi động và các đường đọc cơ bản sau dọn; chưa thay
nghiệm thu chất lượng câu trả lời hoặc tốc độ provider trong mục 3.

## 6. Giữ dự án gọn về sau

**FIX-09, 31/10:** Web xác định tên/viết tắt trường từ metadata và nội dung nguồn,
không dùng danh sách trường hoặc câu trả lời cố định. Chỉ hỏi xác minh trường khi
câu hỏi về quy định còn mơ hồ giữa các nguồn; affiliation trong sách/bài báo không
biến tài liệu đó thành quy chế. PDF thông thường tiếp tục truy hồi nội dung.
Xác nhận tên trường và đổi trường giữ lại câu hỏi gốc trong lịch sử có giới hạn.
25 tests liên quan PASS (15 mới và 10 tương thích trước đó; 1 test cũ không chạy
do phụ thuộc fixture đã dọn). Không phải full regression. HTTP local ba lượt:
hỏi trường 0,166s; NUAE trả A/3,7 trong 0,150s (cache); đổi Bách khoa trả A/4,0
trong 0,262s (không cache), citation đúng từng PDF. Đây là kiểm tra luồng cụ thể,
không phải đo chất lượng trên mọi PDF hay nghiệm thu toàn bộ bản phát hành.

**FIX-09b, 31/10:** Bổ sung đối chiếu viết tắt chưa có trong PDF qua Gemini hiện
cấu hình, tối đa một lượt phân loại cho một viết tắt và bộ nguồn; chỉ gửi viết
tắt và các tên trường lấy từ nguồn được chọn. Chỉ chấp nhận một candidate hợp lệ
được model xác nhận là alias/name variant, không chọn tên gần giống nhất. Tri
thức model ở bước này chỉ dùng chọn nguồn; câu trả lời vẫn phải kiểm chứng bằng
PDF và citation. Kết quả nhớ tạm 5 phút, phân biệt bộ nguồn; lỗi dịch vụ giữ 30
giây để tránh gọi dồn. Không thêm retry, key hoặc reset quota.

Kết quả chưa rõ thì app giải thích thông tin còn thiếu, liệt kê tên trường từ
PDF và hỏi tên đầy đủ/chọn nguồn. API lỗi được báo riêng. Xác nhận lại không làm
mất câu hỏi gốc. Prompt và thông báo phân biệt thiếu phạm vi người dùng với thiếu
bằng chứng nguồn; không mặc định mọi PDF là tài liệu đại học.

44 tests liên quan PASS (34 hiện tại và 10 tương thích từ mốc `f9d8ba10`; 1 test
cũ phụ thuộc fixture đã dọn không chạy), gồm alias được xác nhận, mơ hồ/unknown, kết quả sai schema/ngoài
scope, lỗi API, cache theo nguồn và hướng dẫn bổ sung thông tin. HTTP thật với
3 PDF: câu hỏi gốc → `hust` → `HUST` → `Hust`; cả ba câu trả lời tiếp tục quy đổi
điểm và chỉ trích PDF Bách khoa Hà Nội. Thời gian 2,554s / 0,644s / 0,736s;
metric đối chiếu tăng đúng 1, không lỗi, khoảng 1,21 giây. Các số này là kiểm tra luồng
cụ thể, không phải full regression hay accuracy cho mọi tên trường/PDF.

**FIX-11, 31/10 — Hội thoại liền mạch:** Client giữ ý định câu hỏi đã giải quyết
theo cuộc chat, bộ PDF và ngôn ngữ, thay vì chỉ dựa vào 6 tin gần nhất. Ý định
được giữ riêng với câu trả lời/citation; lịch sử chat không trở thành bằng chứng
nguồn. Chat mới xóa bộ nhớ. Câu hỏi ngắn đổi trường được viết lại giữ thuộc tính
đang hỏi và thay tên nguồn cũ; hỗ trợ alias nằm trong cả câu hỏi đầy đủ. Mơ hồ
về đối tượng so sánh vẫn hỏi lại, không tự suy đoán.

Tái dùng chỉ câu trả lời dương tính đã được cache kiểm chứng chấp nhận, khi câu
hỏi đã đủ nghĩa và nêu rõ trường, cùng PDF/corpus, model, cấu hình và ngôn ngữ.
Câu cá nhân, trích đoạn đang chọn, câu còn phụ thuộc ngữ cảnh và câu trả lời
chưa xác minh không dùng cơ chế này. Policy cache của các phase khác vẫn giữ
qua opt-in web; context policy đổi sang `request-context-v13` để tránh dùng lại
cách mở rộng lịch sử cũ. Không đổi ngưỡng grounding hoặc citation.

Kiểm tra: 52 tests hiện tại + 91 tests tương thích từ `f9d8ba10` = 143 PASS.
Một assert phiên bản cache của test cũ được chuyển v12 → v13; logic/ngưỡng khác
giữ nguyên. Có 120 lần đổi trường và 250 lượt hội thoại **giả lập**, kiểm tra
đổi chủ đề, reset chat, cô lập nguồn, giữ trường qua 15 câu mới không nhắc tên
và không đưa câu trả lời AI thành user intent.
Đây là focused regression, không phải full regression hay 250 inference thật.

HTTP thật nguyên ví dụ: “quy định của hust là gì” → “còn nuae thì sao” → “còn
hust thì sao”; cả ba trả lời đúng nguồn HUST/NUAE/HUST, citation lần lượt trang
5 / 84,85,109 / 5. Lượt cuối 2,952s / 0,548s / 0,910s, **cả ba dùng câu trả lời
đã kiểm chứng trong cache**; lượt đầu vẫn đối chiếu alias qua Gemini. Các lượt
sinh câu trả lời trước đó đo 10,606s cho HUST và 8,384s cho NUAE. Không coi số
cache warm này là latency inference mới hoặc accuracy cho mọi hội thoại.

Tiếp tục thêm 6 câu mới về quy đổi điểm, không nhắc tên trường trong câu hỏi:
6/6 trả lời từ PDF HUST, vẫn giữ trường khi câu nhắc HUST ban đầu đã ra khỏi
6 tin gần nhất. Các câu dùng phép chiếu bảng nguồn (`grade0/grade1`), hoàn tất
trong 1,014–1,325s; đây không phải 6 inference Gemini mới.

Thiết kế tham khảo [bộ nhớ theo thread của LangChain](https://docs.langchain.com/oss/python/langchain/short-term-memory),
[query rewriting trong RAG nhiều lượt của NVIDIA](https://docs.nvidia.com/rag/latest/multiturn.html)
và [cách lưu/truy hồi memory của Supermemory](https://supermemory.ai/docs/concepts/how-it-works).
Phần triển khai hiện dùng state local và Gemini sẵn có; chưa tích hợp dịch vụ
Supermemory hay huấn luyện thêm RNN. FIX-05 và nghiệm thu release cuối vẫn mở.

Không commit PDF cá nhân, model, môi trường Python, database, cache hoặc log.
Chỉ tạo đầu ra chẩn đoán khi xử lý sự cố cụ thể và xóa khi xong. Kết quả cần
lưu lâu dài cập nhật ngắn gọn vào chính báo cáo này; các bước còn làm cập nhật
vào `plan.md`. Đường dẫn dữ liệu do `.env` chọn phải được kiểm tra trước mọi
lần dọn thư mục.
