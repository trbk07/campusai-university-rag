# Runtime assets và giấy phép bên thứ ba

Identity máy đọc được nằm ở [runtime-assets.json](../../configs/local/runtime-assets.json)
và [dense-manifest.json](../../configs/local/dense-manifest.json). Không có key,
PDF người dùng hoặc weights trong source ZIP. Các dependency Python được cài từ
`uv.lock`; giữ các LICENSE/NOTICE trong wheel khi sao lưu hoặc phân phối lại môi trường.

| Asset | Revision / nguồn | License công bố | Dung lượng file sau setup |
|---|---|---|---:|
| BGE-M3 encoder | `BAAI/bge-m3`, `5617a9f61b028005a4858fdac845db406aefb181` | MIT theo [model card pinned](https://huggingface.co/BAAI/bge-m3/blob/5617a9f61b028005a4858fdac845db406aefb181/README.md) | 2.293.331.623 byte, 11 file |
| RapidOCR bundled ONNX | wheel `rapidocr-onnxruntime==1.4.4`; detector/recognizer/classifier | Apache-2.0 theo metadata wheel | 16.189.007 byte |
| Tesseract language data | `tessdata_fast/4.1.0`, `vie` + `eng` | [Apache-2.0 upstream](https://github.com/tesseract-ocr/tessdata_fast/blob/4.1.0/LICENSE) | 4.644.363 byte |
| VietOCR tùy chọn | `vgg_seq2seq.pth` pinned SHA-256 và detector RapidOCR | [Apache-2.0 upstream](https://github.com/pbcquoc/vietocr/blob/master/LICENSE); [license adapter giữ trong source](../../src/campusai/ingestion/vietocr.LICENSE) | 94.320.888 byte |

BGE/Tesseract/VietOCR được tải hoặc copy tường minh trong bước setup. Byte tải
asset bằng tổng byte file chưa có; lần setup sau tái sử dụng file đúng hash.
RapidOCR ONNX đã nằm trong wheel khoảng 14,2 MiB; không tải khi upload.
Không tính dung lượng của Python environment, cache wheel, index, PDF hoặc state
vào các số trên. Các giá trị đó phụ thuộc extras, cache và dữ liệu người dùng;
phải dự trù thêm dung lượng trước khi cài. Preflight 1 GiB là khoảng trống để
vận hành, không phải tổng dung lượng cần cho setup.

Setup từ chối weights có hash khác. Runtime local kiểm inventory/checksum và
chỉ cho SentenceTransformer đọc snapshot local với `trust_remote_code=False`.
Không tự đổi revision, key hoặc model nếu thiếu asset. Optional VietOCR không
cài training stack và không thay backend mặc định. Source bundle giữ license
adapter; mô tả này không cấp lại giấy phép cho phần mềm/dữ liệu bên thứ ba.
