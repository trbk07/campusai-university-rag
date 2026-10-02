# Phase 7 — abstention và phép đo policy cố định, 02/10/2026

Phase 7 vẫn chưa đạt 10/10. Vòng này sửa một giới hạn trong đường phục vụ:
threshold rerank cũ không thể giảm FPR của Phase 6 vì điểm thấp vẫn trả
nguyên baseline. Một lựa chọn abstain đã được thêm, nhưng policy đo trong
vòng này không đủ chất lượng để kích hoạt production.

## Hành vi và kiểm chứng

`low_score_action` được lưu trong policy calibration: `phase6` là mặc định
tương thích, `abstain` là lựa chọn phải fit trên dev. Khi provider trả đủ
candidate, score hữu hạn và provenance đúng, điểm top thấp hơn threshold
có thể trả rỗng với reason `reranker_no_evidence`. Margin thấp vẫn giữ
Phase 6 vì hai chunk cùng liên quan không đồng nghĩa với thiếu bằng chứng.

Lỗi provider, timeout, queue full, circuit open, sai scope/provenance và
rollback vẫn giữ chính xác kết quả Phase 6. Các trường policy khác, route
hard-only và cap release không đổi. Policy action tham gia cache fingerprint;
đổi action không dùng lại câu trả lời cache của policy trước.

Calibrator, cap sweep, release command và validator dùng cùng hàm quyết định
score. Validator tái tính output và recall/FPR từ observations theo action
đã lưu; action lạ hoặc cap trial dùng action khác bị chặn. Không hạ ngưỡng
quality, latency hoặc thay benchmark tác giả AI thành benchmark tác giả người.

Kiểm tra phục vụ cũng xác nhận abstention không gọi LLM, không có citation,
cache có hiệu lực cho cùng policy và đổi policy làm mất hiệu lực cache.

## Đo trên hai tập dev, không fit lại

Giữ cố định score threshold `-0.8828125` (giá trị lưu thực tế là số float
kế tiếp lớn hơn), margin `0`, cap `20`, BGE FP16 512 token, batch 16 và
định dạng đầu vào bảng theo câu hỏi. Threshold/cap lấy từ study vòng 2;
route lấy từ `route-v2`, vốn vẫn infeasible. Đóng băng các tham số trong
`attempt.json` trước khi chạy. Không thay chúng sau khi thấy kết quả.

Phép đo chạy đường `HybridRetriever.search(..., mode="phase7")` thật với
model offline. Baseline Phase 6 được đo riêng. Output policy cũ được replay
từ cùng inference, chỉ thay nhánh score thấp về baseline. Đây là phép đo
quality chẩn đoán, timeout 60 giây để không trộn lỗi tải vào chất lượng;
không đại diện cho M7 hoặc production với timeout 1.000 ms.

| Tập dev / policy | Recall@5 | MRR | FPR |
|---|---:|---:|---:|
| 57 câu formal AI — Phase 6 | 83,67% | 0,6412 | 87,50% (7/8) |
| 57 câu formal AI — rerank, low score → Phase 6 | 87,76% | 0,7126 | 87,50% (7/8) |
| 57 câu formal AI — rerank, low score → abstain | 87,76% | 0,7126 | 0% (0/8) |
| 156 câu natural AI — Phase 6 | 70,00% | 0,5339 | 88,89% (32/36) |
| 156 câu natural AI — rerank, low score → Phase 6 | 69,17% | 0,5318 | 88,89% (32/36) |
| 156 câu natural AI — rerank, low score → abstain | 28,33% | 0,2335 | 8,33% (3/36) |

57 câu formal gồm 49 positive, 8 negative. 156 câu natural gồm 120 positive,
36 negative. Chỉ các record split dev được giữ và chạy từ file natural có
nhiều split. Không đo hoặc fit trên test/holdout trong vòng này.

Tập natural dùng raw query và doc scope theo upload fixture, không thay bằng
`normalized_query` hoặc dùng gold làm đầu vào truy xuất. Có 7 record cần
history và 6 record cần selected text; đường truy xuất đang đo không nhận
hai đầu vào đó, và raw report ghi rõ hạn chế này. Không sửa nhãn hoặc loại
các câu lỗi ra khỏi mẫu để nâng điểm. Các con số không chứng minh chất
lượng end-to-end có history/selection hay trên dữ liệu tác giả người độc lập.

Chênh lệch giữa kết quả formal và natural là lý do không promoted threshold
này. Lựa chọn abstain sửa được cơ chế, nhưng học một cutoff từ tập formal
nhỏ chưa tạo policy trả lời đúng trên câu hỏi viết tắt, lỗi gõ, cách hỏi đời
thường và ngữ cảnh hội thoại. Cần dữ liệu dev đại diện và đánh giá độc lập
trước khi tuyên bố tối ưu hoặc đạt 10/10.

## Artifact và điều kiện còn thiếu

Kiểm chứng cuối: **374 passed, 2 skipped, coverage 88,15%** (gate 85%). Compile
và `git diff --check` thành công. Hai test LLM live vẫn skip vì không có
credential provider; kết quả mock không thay thế phép đo grounding live.

- Raw results và freeze: `.release/reranker/studies/loop3-fixed-policy-natural-dev-v1/`.
- Harness chẩn đoán có SHA riêng: `.tmp/evaluate_fixed_phase7_policy.py`.
- Tests: `.tmp/phase7-loop3-pytest-final.xml`.
- Coverage: `.tmp/phase7-loop3-coverage-final.json`.
- Readiness: `.tmp/phase7-loop3-readiness.json`.

Benchmark chuẩn/frozen splits ở đường dẫn release vẫn thiếu. Cũng chưa có
policy quality/routing đạt chuẩn, capacity toàn service đạt chuẩn, grounding
LLM live hay staging/canary observations đầy đủ. Xác nhận review trực tiếp
của bạn và nhóm không được dùng để tạo tác giả, nhãn hoặc phép đo không có.
Những điều kiện này vẫn chặn M1–M12 và giữ score chính thức ở `null`.
