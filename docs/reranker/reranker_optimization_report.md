# Phase 7: kết quả tối ưu ngày 02-10-2026

Phase 7 đã được nâng cấp về runtime, kiểm soát tài nguyên, calibration và tích
hợp HTTP. Các cấu hình mới đã được đo trên GPU thật. **Chưa đạt điều kiện
release 10/10**: chưa có cấu hình đạt đồng thời routing, recall, FPR và tải 20
yêu cầu; bộ artifact benchmark chuẩn và telemetry staging cũng chưa đầy đủ.

Việc thiếu artifact có thể chạy lại là một hạn chế của bằng chứng release.
Các số đo dưới đây không được gán thành PASS hoặc dùng để tạo điểm 10.

## Những thay đổi đã triển khai

- Hỗ trợ FP16/BF16 trên CUDA, tách cache mô hình theo snapshot, dtype và giới
  hạn token. CPU tiếp tục dùng FP32. Model chỉ được nạp từ snapshot local đã
  kiểm tra checksum.
- Batching gộp nhiều request trong một cửa sổ ngắn, với số cặp query/chunk và
  queue hữu hạn. Tách điểm trả về theo từng request, giữ nguyên scope và
  provenance. Request đã timeout không được nhận kết quả muộn; inference đang
  chạy giữ admission permit cho đến khi thực sự kết thúc.
- Cache điểm tùy chọn chỉ lưu raw scores. Cache key ràng buộc mô hình, query,
  nội dung và tọa độ nguồn; mỗi lần trả kết quả dựng lại original rank/RRF.
  Phép đo luôn tắt cache này. Batching và cache điểm không được bật cùng nhau.
- Calibration tìm toàn bộ ngưỡng đặc trưng retrieval quan sát trên dev, thay
  cho lấy mẫu quantile có thể bỏ sót ngưỡng khả thi. Các đặc trưng ràng buộc
  dùng cú pháp query; không dùng gold, topic ID hoặc template ID.
- CLI truyền đầy đủ dtype, batch size, token limit và batching settings từ M3
  sang M5. Calibration chính thức từ chối cấu hình khác identity M3.
- Manifest production phải khớp timeout, queue size, circuit limit và cache
  đã đo. Validator kiểm tra binding của từng capacity profile.
- HTTP cấp request ID ở server, kiểm tra JSON/body size, document scope,
  filters, top_k và language. Cấu hình ứng dụng sử dụng activation có guard,
  LLM được cấu hình và canary bắt đầu ở 0%.
- Startup lỗi và shutdown đều dọn provider, cache và LLM, kể cả khi một bước
  cleanup lỗi. Các khóa single-flight của answer cache được thu hồi sau khi
  holder và waiter cuối cùng rời đi, tránh tích lũy theo số query độc nhất.

Các ngưỡng release và cơ chế bảo toàn Phase 6 khi provider lỗi được giữ nguyên.
Precision/batching mới phải được calibration và đo lại trước khi activation.

## So sánh hiệu năng

Môi trường: RTX 4060 Laptop 8 GB, runtime CUDA riêng trong
`.tmp/reranker-gpu-runtime`. Mỗi profile dùng provider mới, 100 yêu cầu không
cache điểm, với ba hard-dev query và candidate thật. Đây là **reranker-only**,
chưa bao gồm retrieval, LLM hoặc transport HTTP.

| Cấu hình | Cap-10 p95 mẫu (ms) | Concurrency 5 | Concurrency 20 |
|---|---:|---|---|
| BGE FP32, batch 8, 512 token | 407 | 98 lỗi/100 | 98 lỗi/100 |
| BGE FP16, batch 8, 512 token | 174 | p95 835 ms; 1 lỗi/100 | 90 lỗi/100 |
| BGE FP16, batch 32, 512 token, window 2 ms | 158 | p95 564 ms; 0 lỗi/100 | 100 lỗi/100 |
| MiniLM FP16, batch 32, 512 token, window 2 ms | 37 | p95 135 ms; 0 lỗi/100 | p95 475 ms; 0 lỗi/100 |

FP16 BGE không thay đổi thứ hạng trong các mẫu đối chiếu FP32; sai khác logit
lớn nhất khoảng 0,00549. BF16 có đổi thứ hạng trong 9/27 quan sát lặp lại.
Không suy rộng kết quả này thành bảo đảm chất lượng trên mọi input. Allocation
FP16 batch 8 khoảng 1,24 GB so với FP32 2,47 GB; batch 32 dùng khoảng 1,52 GB.

Circuit fast-fail không được tính thành throughput thành công. Profile BGE
20 đồng thời cuối cùng có `successful_requests_per_second=0`, dù tổng request
kết thúc rất nhanh sau khi circuit mở. MiniLM đạt khoảng 55 successful rps
trong profile 20 này, nhưng chất lượng chưa đủ để chọn làm mặc định.

## So sánh chất lượng trên dev

Tập nghiên cứu: 57 câu dev, gồm 49 positive và 8 negative, tách biệt khỏi bộ
480 natural inputs. Không mở test/holdout để chọn cấu hình trong vòng này.
So sánh cap 8/10/12/16/20/40, fusion trọng số 0/0,1/0,25/0,5/0,75/1, và các
tín hiệu top logit, top margin, peak trừ mean. Đây là các họ phương pháp đã
thử nghiệm; không phải chứng minh tối ưu toàn cục.

| Cấu hình | Recall@5 | MRR top-five | nDCG@5 |
|---|---:|---:|---:|
| Phase 6 baseline (FPR 7/8) | 83,67% | 0,6412 | 0,6823 |
| BGE FP16, 512 token | 85,71% | 0,7534 | 0,7769 |
| BGE FP16, 1024 token | 83,67% | 0,7823 | 0,7929 |
| BGE FP16, 256 token | 71,43% | 0,5935 | 0,6150 |
| MiniLM FP16, 512 token | 30,61% | 0,2585 | 0,2667 |

Baseline ở dòng đầu là đối chiếu, không có FPR bằng 0. BGE 512 cải thiện MRR
khoảng 17,5% trong thử nghiệm dev này, nhưng recall vẫn thấp hơn target 95%.
MiniLM khi bỏ evidence threshold đạt Recall@5 97,96%, đồng thời FPR 87,5% và
MRR 0,6388. Tốc độ hoặc recall riêng lẻ chưa đủ để chọn cấu hình.

Các dòng còn lại chọn cấu hình tốt nhất quan sát khi FPR dev bằng 0. BGE 512
và hai cấu hình 256/MiniLM chọn cap 40; cap này là nghiên cứu, vượt tập cap
8/10/12/16/20 cho M5 release chính thức. Không được chuyển trực tiếp kết quả
này thành calibration đã PASS.

Quan sát FPR 0/8 chỉ là kết quả trên tám negative dev; chưa chứng minh FPR
tổng quát ≤1%. Evidence abstention/fusion ở đây là thí nghiệm offline, chưa
được tích hợp thành policy production đã PASS. Đặc biệt, cơ chế reranker hiện
tại giữ Phase 6 khi điểm thấp; chỉ tuning threshold rerank không thể sửa FPR
của fallback baseline. Cần xử lý và kiểm chứng quyết định thiếu bằng chứng
trước khi có thể đạt gate chất lượng.

Routing dev cải thiện hard recall từ 54,55% lên 81,82% (9/11), nhưng easy
unnecessary rerank vẫn 27,27% (3/11). Target tương ứng là ≥95% và ≤20%; routing
vẫn infeasible và không được promoted.

## Kiểm chứng và trạng thái release

Bộ kiểm thử cuối vòng tối ưu ban đầu: **351 passed, 2 skipped**, không có failure/error hoặc
resource warning. Coverage **87,93%**, vượt mức yêu cầu 85%. Compile và
`git diff --check` đều thành công. Các test mới kiểm tra precision/snapshot
cache, batching đồng thời, timeout/cancellation, provenance, resource binding,
scope HTTP, startup/shutdown và single-flight cleanup.

Báo cáo test, coverage, readiness và raw study nằm tại các đường dẫn trong
summary `.tmp/reranker-optimization-summary.json`. Hai integration test LLM trực
tiếp chưa chạy vì môi trường không có API key provider. Cấu hình bị lỗi và
artifact lịch sử được giữ lại; không ghi đè kết quả cũ.

Validator chính thức: **M0 PASS; M1–M12 BLOCKED; score = null**. File benchmark
chuẩn `data/benchmark/human_retrieval.jsonl`, các frozen split và artifact gắn
với từng record chưa hiện diện. Ngoài ra cần chất lượng held-out đạt chuẩn,
capacity toàn service, LLM grounding thật và staging canary đủ cửa sổ. Báo cáo
code/test này chưa thay thế được những phép đo đó.

Đề xuất kỹ thuật dựa trên số đo hiện tại: tiếp tục BGE FP16 với context 512
token, giữ batching tùy chọn và chọn queue theo profile đo. Không rút context
xuống 256 hoặc thay bằng MiniLM chỉ vì nhanh hơn. Production tiếp tục bị guard
từ chối cho đến khi tất cả artifact chính thức đạt chuẩn. WSGI shell local
vẫn là công cụ smoke/demo, chưa phải deployment đã kiểm chứng tải.

## Tái chạy và nguồn phương pháp

Vòng sửa và đo tiếp theo có **363 passed, 2 skipped**; các số đo bảng học
phần, GTE và tải đúng cap được cập nhật trong
[inference_optimization_report.md](inference_optimization_report.md). Trạng thái release vẫn conditional.

Hai công cụ mới `evaluation.reranker.benchmark_reranker_precision` và
`evaluation.reranker.optimize_reranker_dev` lưu raw scores, input hashes và lỗi từng
request. Output bắt buộc ở `.release/reranker/studies`, không ghi đè attempt
đã có. `--raw-scores` cho phép thử tín hiệu mới trên raw dev đã ràng buộc
dataset/index/calibration, không gọi model lại hoặc đọc held-out.

FP16/BF16 và batching được đối chiếu với [Sentence Transformers efficiency
documentation](https://www.sbert.net/docs/cross_encoder/usage/efficiency.html).
Snapshot mô hình nhỏ được pin theo [model card MiniLM
mMARCO](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1).
Việc lựa chọn ở báo cáo này dựa trên phép đo của project, không dựa riêng vào
khuyến nghị chung hoặc kích thước mô hình.
