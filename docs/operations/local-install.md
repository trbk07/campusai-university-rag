# Cài đặt và vận hành CampusAI local

Trạng thái: hướng dẫn đang được kiểm chứng trong [Phase 13](../../plan.md#bo-sung-phase-13).
Chưa có RC được nghiệm thu; chưa dùng hướng dẫn này để khẳng định cài sạch đã PASS.
Đích v1 là Windows x64, một người dùng, server tại `http://127.0.0.1:8000`.
Generation cần mạng và API key riêng; model truy hồi/OCR chạy trên máy.
Streaming, graph và reranker mặc định tắt. Không cam kết Free Tier vô hạn.

## Setup Windows

Lệnh dưới đây đang được dùng để kiểm L13-02/L13-04, chưa có RC để tải. Khi có
ZIP đã chốt, kiểm SHA-256 với receipt rồi giải nén vào thư mục mới, ví dụ
`D:/CampusAI App`. Mở PowerShell trong thư mục đó. Cài `uv` và Python x64 3.14;
máy tham chiếu hiện dùng Windows 11 build 26200 / Python 3.14.6. Metadata Python
3.11–3.14 của thư viện không phải bảng phiên bản đã được nghiệm thu.

```powershell
uv sync --frozen --python 3.14 --extra feasibility --extra ocr
Copy-Item .env.example .env
$modelCache = Join-Path $env:LOCALAPPDATA 'CampusAI/models'
.venv/Scripts/python.exe -m scripts.operations.setup_encoder --model-cache "$modelCache"
```

Mở `.env` bằng trình soạn thảo và nhập `GEMINI_API_KEY` riêng. Không đặt key trực
tiếp trên dòng lệnh hoặc gửi nó cho người hỗ trợ. Lệnh setup encoder tải khoảng
2,3 GB từ revision đã khóa; bước cài dependency cần mạng và thêm dung lượng cho
Python/wheels. Sau setup, upload/truy hồi/OCR không tải model. Generation vẫn
cần mạng tới Gemini. Node/Playwright không phải dependency cài app.

Nếu dùng model cache riêng, đặt **cùng đường dẫn tuyệt đối** vào
`CAMPUSAI_MODEL_CACHE` trong `.env`; truyền đường dẫn ấy qua `--model-cache` khi
setup. Setup scripts không tự đọc `.env`; flag/biến môi trường của lệnh setup
phải khớp cấu hình app. Encoder nằm ở `bge-m3/<revision>` trong model cache.
Không đổi `CAMPUSAI_DENSE_MODEL` để né lỗi missing model; revision/model phải
khớp manifest được bind. Kiểm tất cả file có thể mất vài giây lúc check/start.

Để cài offline từ các **asset đã tải đúng revision**, copy tường minh:

```powershell
.venv/Scripts/python.exe -m scripts.operations.setup_encoder --model-cache "$modelCache" --source-dir "D:/Pinned BGE snapshot"
```

Lệnh không mượn module/index/state của snapshot nguồn; nó copy bytes sang cache
đích và kiểm hash. Dependency Python offline cũng cần wheel cache phù hợp `uv.lock`.

OCR RapidOCR có sẵn trong extra `ocr`; launcher kiểm ba model ONNX trong wheel.
Để nhận tiếng Việt/Anh bằng Tesseract, setup dữ liệu ngôn ngữ một lần:

```powershell
.venv/Scripts/python.exe -m scripts.operations.setup_ocr --output "$modelCache/ocr/tessdata_fast"
```

Launcher tự chọn Tesseract khi package và dữ liệu pinned hợp lệ; các cấu hình
backend explicit vẫn có ưu tiên. VietOCR là lựa chọn riêng:

```powershell
uv sync --frozen --extra feasibility --extra ocr --extra ocr-vietnamese
.venv/Scripts/python.exe -m scripts.operations.setup_vietocr --output "$modelCache/ocr/vietocr"
```

Khi chọn VietOCR, đặt `CAMPUSAI_OCR_BACKEND=vietocr` và đường dẫn tuyệt đối tới
`<modelCache>/ocr/vietocr` trong `CAMPUSAI_OCR_DATA_DIR`. Chi tiết hash, byte và
license: [runtime assets](local-third-party.md). Chưa công bố gate chất lượng
đại diện chỉ từ việc cài thành công các model này.

Sau setup, chạy `--check`, rồi mở `start-campusai.cmd`. Chọn mục tải tài liệu,
thêm tối đa 5 PDF mỗi lượt và đợi trạng thái sẵn sàng; có thể tải lượt tiếp.
Trong Trợ lý AI, chọn nguồn cần hỏi, nhập câu hỏi rồi mở citation để xem đúng
tài liệu/trang. Với scan hoặc mixed PDF chưa đọc đủ, mở chi tiết tài liệu và
theo dõi OCR nền và coverage; các tác vụ đã hủy/lỗi cần lựa chọn thử lại.
Xóa tài liệu từ thư viện khi không dùng nữa.

## Thư mục và cấu hình

Chạy lệnh từ thư mục source. Launcher đọc `.env` nhưng không chạy biểu thức shell;
biến môi trường đã đặt có ưu tiên. Không đưa `.env` hoặc `configs/key.yaml` vào Git,
ZIP hay log. Trong `.env`, nên dùng dấu `/` cho đường dẫn Windows, ví dụ
`CAMPUSAI_STATE_ROOT=D:/CampusAI Data` (hoặc không đặt để dùng mặc định).

Cài mới dùng `%LOCALAPPDATA%/CampusAI` làm state root. Đường dẫn tương đối của
các override dữ liệu tính từ state root; đường dẫn profile và key tương đối
tính từ thư mục source. Đường dẫn tuyệt đối do người dùng đặt được giữ nguyên.

| Dữ liệu | Mặc định bên trong state root | Override |
|---|---|---|
| PDF upload, registry, parsed text, bảng | `data/store` (PDF ở `uploads/<sha>/`) | `CAMPUSAI_STORE_DIR` |
| BM25/dense index | `data/index` | `CAMPUSAI_INDEX_DIR` |
| Journal job/recovery | `data/operations/ingestion-jobs.sqlite3` | `CAMPUSAI_JOB_DB` |
| Câu trả lời cache | `data/cache/grounded-answers.sqlite3` | `CAMPUSAI_RAG_CACHE_PATH`; `:memory:` nếu không lưu qua restart |
| Quota và cooldown | `data/operations/flash-lite-quota.sqlite3`, `gemini-provider-health.sqlite3` | đường dẫn trong profile AI |
| Model cache | `models` | `CAMPUSAI_MODEL_CACHE`, `HF_HOME`, `HF_HUB_CACHE` |
| OCR Tesseract đã setup | `models/ocr/tessdata_fast` | `CAMPUSAI_OCR_DATA_DIR` |
| Log console | cửa sổ launcher; chưa có file log tự động | chỉ thu log đã lọc khi cần hỗ trợ |

Đường dẫn cache/quota/cooldown **tương đối trong profile AI** cũng tính từ state
root khi dùng launcher local. Đường dẫn tuyệt đối được giữ nguyên. Không đổi
scope/policy quota khi cập nhật app. Không đặt state vào thư mục tạm hoặc vùng
cài đặt chỉ đọc. Không cần quyền ghi source khi chạy với state/model tách riêng.

## Dữ liệu từ phiên bản trước

Launcher dừng nếu thấy dữ liệu ở `data/store`, `data/index` hoặc `data/operations`
trong source mà chưa có lựa chọn state root rõ ràng. Đặt `CAMPUSAI_STATE_ROOT`
bằng đường dẫn tuyệt đối của dự án cũ để tiếp tục dùng dữ liệu tại chỗ. App
không tự di chuyển, xóa hoặc nhập dữ liệu. Tránh chạy hai phiên dùng chung state.

Profile mặc định chuyển cooldown từ `.tmp/gemini-provider-health.sqlite3` sang
`data/operations/gemini-provider-health.sqlite3`. Nếu tiếp tục dùng state root cũ
và chỉ có file cũ, launcher dừng để tránh reset cooldown. Sau khi dừng toàn bộ
process CampusAI, backup SQLite bằng API `sqlite3.Connection.backup` sang đường
dẫn mới (không ghi đè file đích đã tồn tại); giữ bản cũ cho tới khi xác minh được.
Không copy riêng file DB đang mở hoặc xóa quota để bỏ qua thời gian chờ.

## Kiểm tra trước khi mở

Sau khi cài môi trường và setup model, đặt key trong `.env` rồi chạy:

```powershell
.venv/Scripts/python.exe -m scripts.operations.local --check
```

Lệnh này không gọi provider, không tạo thư mục/state và không ghi database.
Kiểm quyền ghi là advisory khi check; lúc start app sẽ tạo file tạm, flush và
xóa nó trong từng thư mục state trước khi load ứng dụng. Một check PASS chỉ là
prerequisites cùng checksum asset, không phải nghiệm thu release hoặc live AI.

| Lỗi / trạng thái | Cách xử lý |
|---|---|
| Thiếu `GEMINI_API_KEY` | Nhập key riêng vào `.env`; không gửi key trong log hỗ trợ |
| `dense_model_missing_or_checksum_mismatch_run_setup` | Setup encoder vào model cache đã chọn; giữ file sai hash riêng để kiểm tra, không tự ghi đè hoặc trông chờ upload tải |
| `ocr_assets_missing_or_checksum_mismatch` | Chạy lại setup OCR đã chọn với dữ liệu pinned; không bỏ qua checksum |
| `state_not_writable` | Chọn state root có quyền ghi của tài khoản hiện tại |
| `insufficient_disk_space` | Dọn dung lượng hoặc chọn ổ khác; preflight yêu cầu ít nhất 1 GiB trống, chưa gồm dung lượng tải model |
| `port_in_use` | Dừng process đang dùng cổng 8000 rồi mở lại |
| `cuda_unavailable_using_cpu` | App dùng CPU; chưa có SLO cho cấu hình chưa đo |
| `unsupported_device` | Chọn `cpu`, `cuda` hoặc `cuda:0` |

## Dừng, backup và cập nhật

Dùng Ctrl+C trong cửa sổ launcher để dừng. Đóng tab trình duyệt không dừng server.
Để backup: dừng server và worker, sao lưu toàn bộ state root, profile cấu hình
riêng và các override nằm ngoài state root. Bảo vệ key riêng; không đưa key vào
gói hỗ trợ. Model cache có thể setup lại, nhưng phải giữ đúng revision/checksum.

Khi cập nhật, giữ nguyên state root/profile; giải nén source mới vào thư mục
khác, setup từ lock của bản mới và chạy check trước khi mở. Giữ source cũ và
backup trước cập nhật. Chưa công bố rollback/migration đã nghiệm thu; phần đó
được kiểm ở Phase 14. Gỡ source và `.venv` không xóa state. Chỉ xóa state khi chủ
dữ liệu chủ động chọn xóa; bản backup vẫn có thể còn PDF/câu trả lời.

## Quyền riêng tư và giới hạn hiện tại

PDF, parsed text, index, job và cache câu trả lời nằm trên máy. Profile mặc định
gửi câu hỏi/ngữ cảnh trích được tới Gemini để generation; local không đồng nghĩa
AI offline. Không gửi toàn bộ PDF mặc định. Giữ quota/cooldown và cancellation
hiện có. OCR tùy chọn chạy cục bộ với giới hạn 50 trang / 120 giây mỗi lượt.
Upload tối đa 5 PDF mỗi lượt; có thể thêm lượt tiếp theo. Giới hạn từng PDF hiện
là 50 MiB / 218 trang; đây là giới hạn chấp nhận, không cam kết chất lượng/tốc độ
mọi PDF. Nghiệm thu đại diện QA PDF và cài sạch/RC vẫn đang mở trong plan.

Các bước tải ZIP/setup encoder, thông số máy đã đo và clean-install receipts sẽ
được chốt trong chính hướng dẫn này qua L13-01–04/06; không cần Node/Playwright
để người dùng chạy app.

## Ba project Gemini độc lập

Khi chủ dự án đã xác nhận key thuộc các project độc lập, đặt
`CAMPUSAI_LLM_CONFIG=configs/free_multi_project.yaml` trong `.env`.
Launcher đọc `key_1`, `key_2`, `key_3` từ `configs/key.yaml` đã được Git ignore;
biến môi trường tương ứng có sẵn luôn được ưu tiên. Profile chia đều lượt gọi,
tạm bỏ qua project đang cooldown và chuyển câu hỏi sang project khác khi nhận
HTTP 429, tối đa một lần mỗi project. Mọi attempt vẫn tính vào ngân sách chung;
không xóa usage/cooldown. Cả ba project hết hạn mức thì app trả lỗi có thời gian
chờ. Profile một key vẫn dùng được độc lập qua `configs/free_llm.yaml`.
Profile không đặt trần 100 câu trong phiên. Tiếp tục xoay các project còn quota;
khi tất cả đang bị giới hạn, chờ cooldown/reset rồi app có thể dùng chúng lại.
