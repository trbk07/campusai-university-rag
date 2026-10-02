# Phase 7 — vòng sửa và đo tiếp theo, 02/10/2026

Phase 7 **chưa đạt 10/10**. Validator vẫn trả về M0 PASS, M1–M12 BLOCKED,
`score = null`. Các thay đổi và số đo dưới đây không tạo artifact PASS hoặc
thay đổi ngưỡng release. Việc bạn và nhóm đã review trực tiếp được ghi nhận
trong trao đổi; vòng này không yêu cầu lập biên bản review.

## Thay đổi đã kiểm chứng

- Bộ thử nghiệm phân biệt tiền tố metadata với nội dung gốc, xử lý cả dấu
  xuống dòng đơn của chunk bảng và dòng trống của chunk văn bản.
- Bảng JSON được biểu diễn thành hàng có tên cột, giữ giá trị ô và giữ nguyên
  chunk nguồn, document ID, trang và tọa độ trích dẫn.
- Cửa sổ bảng dùng câu hỏi và cấu trúc bảng, không dùng gold, QID hoặc nhãn
  difficulty. Câu hỏi nhiều học kỳ giữ đủ các kỳ được yêu cầu; khoảng số giữ
  cả kỳ trung gian; các môn trùng tên giữ mọi vị trí đồng hạng. Nếu yêu cầu
  một kỳ không có trong bảng, giữ toàn bộ ngữ cảnh để không che mất sự thiếu
  bằng chứng. Các hàng bị lược khỏi đầu vào chấm điểm có thông báo rõ ràng.
- Công cụ đo tải nhận `--capacity-cap`, lưu cap trong raw report và truyền
  đúng cap vào worker. Kết quả cap 10 không được dùng đại diện cho cap 20.
- Loader nghiên cứu GTE dùng implementation được pin và kiểm tra trong
  snapshot local; không bật tải hoặc thực thi remote code động. Adapter khôi
  phục buffer vị trí/RoPE không lưu trong checkpoint theo công thức gốc và
  tương thích attention mask với Transformers 5. Không thay learned weights.

Các định dạng đầu vào và adapter GTE chỉ nằm trong công cụ nghiên cứu. Chúng
chưa được tích hợp vào policy production đã kiểm chứng.

## Chất lượng trên dev

Chỉ dùng lại 57 câu **AI dev** gồm 49 positive và 8 negative. Không đọc hoặc
tuning trên test/holdout trong vòng này. Mỗi study có input hashes, source
hash, model identity và raw scores riêng; kết quả cũ và lần chạy lỗi được giữ.

| Mô hình / đầu vào, FP16 512 token | Cap | Recall@5 khi FPR dev = 0 | MRR | Đạt đồng thời recall ≥95%, FPR ≤1%? |
|---|---:|---:|---:|---|
| BGE, chunk đầy đủ, vòng trước | 40 | 85,71% | 0,7534 | Không |
| BGE, bỏ tiền tố metadata văn bản | 40 | 87,76% | 0,7031 | Không |
| BGE, giữ section + body | 40 | 79,59% | 0,6435 | Không |
| BGE, bảng theo câu hỏi + tiền tố gốc | 20 | 89,80% | 0,8085 | Không |
| BGE, bỏ tiền tố + bảng theo câu hỏi, giữ các kỳ so sánh | 40 | 91,84% | 0,7371 | Không |
| GTE, chunk đầy đủ | 40 | 77,55% | 0,5959 | Không |
| GTE, bảng theo câu hỏi | 20 | 77,55% | 0,4963 | Không |
| MiniLM, bỏ tiền tố + bảng theo câu hỏi | 8 | 18,37% | 0,1429 | Không |

Cap 40 vượt tập cap release 8/10/12/16/20. Với đầu vào BGE bỏ tiền tố và bảng
theo câu hỏi, giới hạn cap 20 chỉ đạt recall 89,80%. Kết quả 0/8 negative là
số quan sát trong dev, không chứng minh FPR tổng quát ≤1%. BGE bảng theo câu
hỏi đạt recall 95,92% khi bỏ quyết định abstention, nhưng FPR tăng lên 87,5%.
Đổi ngưỡng để đạt riêng recall sẽ không giải quyết yêu cầu chất lượng.

## Tải và phần cứng

RTX 4060 Laptop 8 GB, batch 32, FP16, cửa sổ gom batch 2 ms, cache điểm tắt,
timeout 1.000 ms, queue 19. Mỗi mức đồng thời có 100 yêu cầu trên ba câu hard
dev, chỉ đo provider reranker, không phải toàn service hoặc M7 chính thức.

| Cấu hình | Cap tải | Đồng thời | p95 | Lỗi / 100 | Yêu cầu thành công / giây |
|---|---:|---:|---:|---:|---:|
| GTE, chunk đầy đủ | 10 | 1 | 78,96 ms | 0 | 13,77 |
| GTE, chunk đầy đủ | 10 | 5 | 282,14 ms | 0 | 18,24 |
| GTE, chunk đầy đủ | 10 | 20 | 909,21 ms | 0 | 22,03 |
| BGE, bảng theo câu hỏi | 20 | 1 | 282,73 ms | 0 | 3,77 |
| BGE, bảng theo câu hỏi | 20 | 5 | 531,48 ms | 98 | 1,29 |
| BGE, bảng theo câu hỏi | 20 | 20 | 1.014,32 ms | 100 | 0 |

p95 của BGE đồng thời 5 bị kéo thấp bởi nhiều lần từ chối nhanh khi circuit
đã mở; không phải bằng chứng đáp ứng tải. Báo cáo giữ cả lỗi từng request và
throughput thành công. GTE nhanh hơn nhưng chất lượng chưa đủ để thay BGE.
Một lần BGE warm-up hết hạn 60 giây cũng được giữ trong attempt riêng; lần
thử lại hoàn tất, không ghi đè hoặc xóa lần lỗi.

## Kiểm chứng cuối vòng

**363 passed, 2 skipped; coverage 87,93%**, vượt gate 85%. Hai test LLM live
skip vì chưa có API key provider trong môi trường. Kiểm tra compile và diff
được chạy riêng; kiểm thử định dạng bảng gồm nhiều kỳ, khoảng số, môn lặp,
kỳ không tồn tại, dữ liệu lỗi và bảo toàn nội dung nguồn.

- Raw studies: `.release/reranker/studies/loop2-*`.
- Tests: `.tmp/reranker-loop2-pytest-final.xml`.
- Coverage: `.tmp/reranker-loop2-coverage-final.json`.
- Readiness: `.tmp/reranker-loop2-readiness.json`.
- Summary: `.tmp/reranker-loop2-summary.json`.

## Điều kiện còn thiếu để đạt 10/10

File benchmark chuẩn và frozen splits chưa hiện diện ở các đường dẫn mà
validator sử dụng. Cần dữ liệu đánh giá độc lập chưa dùng để tuning, policy
đạt đồng thời chất lượng/routing, phép đo toàn service trên cấu hình triển
khai, grounding LLM thật và canary/fault observations. Những phép đo này
chưa thể suy ra từ unit tests hoặc dev probes.

Các số đo hiện tại cho thấy hai nút thắt kỹ thuật khác nhau: BGE có chất
lượng tốt hơn nhưng tải cap 20 thất bại; các mô hình nhanh hơn chưa phân
biệt đủ câu thiếu bằng chứng. Policy hiện tại trả Phase 6 khi reranker không
đạt threshold, nên chỉ chỉnh threshold rerank không sửa được FPR của
baseline. Quyết định đủ bằng chứng cần được thiết kế và đánh giá độc lập,
trong khi lỗi provider vẫn phải fallback chính xác về Phase 6.

Chưa có cơ sở khẳng định một phương pháp là tối ưu toàn cục. Kết luận của
vòng này chỉ áp dụng cho họ cấu hình, tập dev và phần cứng đã đo. Tất cả
cấu hình không đạt được giữ ở trạng thái conditional.

Snapshot GTE: [model card chính thức](https://huggingface.co/Alibaba-NLP/gte-multilingual-reranker-base),
revision `8215cf04918ba6f7b6a62bb44238ce2953d8831c`; implementation revision
`40ced75c3017eb27626c9d4ea981bde21a2662f4`, được đưa vào snapshot và checksum.
