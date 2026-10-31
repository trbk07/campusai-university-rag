# CampusAI

Web app local hỏi đáp tài liệu đại học bằng tiếng Việt/Anh, có trích dẫn theo
trang. PDF, chỉ mục và OCR xử lý trên máy; Gemini cần Internet và API key riêng.

Repository: [trbk07/campusai-university-rag](https://github.com/trbk07/campusai-university-rag).

## Chạy ứng dụng

Nhấp đúp **`start-campusai.cmd`**, giữ cửa sổ launcher mở và truy cập
**http://127.0.0.1:8000**. Tải tối đa 5 PDF mỗi lượt, chọn tài liệu và hỏi.
App chạy OCR nền khi cần, cho phép hỏi trên phần đã đọc và xem citation tại
trang nguồn. Không cần Node hoặc bước build frontend.

Kiểm tra cấu hình và model mà không gọi Gemini:

```powershell
.venv/Scripts/python.exe -m scripts.operations.local --check
```

Đọc [hướng dẫn cài đặt và vận hành](docs/operations/local-install.md) khi cài
máy mới, backup hoặc xử lý lỗi. Giữ `.env` và `configs/key.yaml` trên máy.

## Cấu trúc

| Thành phần | Mục đích |
|---|---|
| `src/campusai/` | Backend, ingestion/OCR, truy hồi, kiểm chứng và UI HTML/CSS/JS |
| `scripts/operations/` | Khởi động, preflight và setup encoder/OCR |
| `scripts/release/package_local.py` | Đóng gói source từ một Git commit |
| `scripts/dev/secret_scan.py` | Kiểm tra credential trước commit |
| `configs/` | Profile AI và manifest model/OCR |
| `pyproject.toml`, `uv.lock` | Dependency và phiên bản cài đặt |
| `docs/PROJECT_OVERVIEW.md` | Tổng quan chất lượng, hiệu năng, giới hạn và dọn dẹp |
| `plan.md` | Roadmap |


Benchmark, bộ kiểm thử, log, ảnh nghiệm thu, archive và môi trường thử nghiệm
cũ đã được bỏ khỏi cây dự án theo yêu cầu ngày 31/10/2026. File đã commit vẫn
có lịch sử Git; đầu ra local đã xóa không được cam kết khôi phục. Đọc
[báo cáo tổng quan](docs/PROJECT_OVERVIEW.md) và [roadmap](plan.md) trước khi
coi số liệu lịch sử là nghiệm thu bản hiện tại.
