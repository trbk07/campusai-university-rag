# CI/CD và Docker

## Tự động kiểm tra

[GitHub Actions](https://github.com/trbk07/campusai-university-rag/actions) chạy
khi push `main`, mở pull request hoặc chọn **Run workflow**:

- Tests offline trên Linux/Python 3.11/3.12/3.14 và Windows/Python 3.14.
- Quét credential; đóng gói wheel, sdist và ZIP source từ đúng commit.
- Build Docker image CPU và kiểm tra entrypoint/Compose.

Tests không gọi Gemini hoặc tải model. CI xanh chỉ chứng nhận các kiểm tra này;
không thay nghiệm thu chất lượng câu trả lời, OCR hay hiệu năng trên PDF thực.

## Chạy Docker trên máy

Windows cần Docker Desktop với Linux Engine, WSL >=2.1.5 và virtualization bật
trong BIOS. Nếu Desktop báo thiếu virtualization, vào BIOS bằng F2/Fn+F2,
bật Intel Virtualization Technology (hoặc SVM trên AMD), lưu và khởi động lại.
Tham khảo [Docker Windows](https://docs.docker.com/desktop/setup/install/windows-install/).

Đặt `GEMINI_API_KEY` trong environment hoặc file `.env` local đã được Git ignore.
Không đưa key vào Dockerfile, image hay repository. Từ thư mục dự án:

```sh
docker compose build
docker compose --profile setup run --rm assets
docker compose up -d --wait --wait-timeout 180 app
```

Bước `assets` tải encoder/OCR đã pin và kiểm tra hash vào volume riêng, chỉ cần
làm khi setup/cập nhật model. Image không chứa PDF, key hoặc model weights.
Mở http://127.0.0.1:8000. Dừng app local đang dùng cổng 8000 trước khi chạy container.

```sh
docker compose logs --tail 100 app
docker compose stop app
```

State/PDF/index/quota nằm trong volume `campusai-state`, vẫn giữ khi stop hoặc
recreate container. Không dùng `down --volumes` khi cần giữ dữ liệu. Container
CPU dùng Python 3.12 để tương thích metadata của OCR và có thể chậm hơn profile
CUDA trên Windows. Cấu hình này phục vụ máy riêng;
chưa cung cấp authentication/TLS cho public hosting.

## Publish và triển khai

Khi chủ dự án **publish GitHub Release**, workflow `Release container` chạy lại
CI, rồi đẩy image lên GHCR với tag và digest, kèm provenance/SBOM. Không tạo
release chỉ để thử pipeline khi bản ứng dụng chưa được nghiệm thu.

Deploy tự động chỉ bật khi có máy Linux đích:

1. Đăng ký self-hosted runner có labels `self-hosted`, `linux`, `campusai`, cài
   Docker Compose; runner chỉ nhận workflow của repository tin cậy.
2. Tạo GitHub environment `production`. Trên máy đích chuẩn bị file environment
   riêng chứa key, quyền đọc hạn chế và setup volume/model như hướng dẫn trên.
3. Đặt repository variable `CAMPUSAI_DEPLOY_ENV_FILE` là đường dẫn tuyệt đối tới
   file đó, rồi đặt `CAMPUSAI_DEPLOY_ENABLED=true`.

Pipeline deploy đúng digest đã build, chờ `/ready`; nếu cập nhật không healthy
thì thử khôi phục image trước và báo workflow thất bại. Đây là rollback image,
không thay backup dữ liệu; phải kiểm tra tương thích state trước release có migration.
Chưa có runner/máy đích thì deploy được skip, không được ghi là đã triển khai.
