# Protocol review answer/citation của Phase 7

Trạng thái: **hướng dẫn triển khai; rubric thực tế cần người có role được khai báo duyệt trước freeze**.
Roadmap: [plan.md](../../plan.md#phase-7--reranker). Mục tiêu là S4/S5, không suy
answer quality từ retrieval Recall hoặc từ việc quote có xuất hiện trong PDF.

## Trước khi mở held-out

1. Chốt gold claims trên câu hỏi, context, scope và frozen evidence đã review.
   Mỗi claim có ID ổn định; số, đơn vị, course/program code, năm/phiên bản, điều kiện
   và từng hop cần thiết phải được thể hiện trong rubric. Không lấy model output
   làm gold và không sửa rubric sau khi thấy held-out errors.
2. Rubric JSON archived trong results directory có `status=approved`, reviewer thật
   và `gold_claim_ids` mapping toàn bộ primary qids sang danh sách IDs; negative là `[]`.
   Lưu mô tả từng claim và tiêu chí correctness/support/adjudication cùng mapping đó.
3. Khóa model LLM/config, prompt, context budget, thứ tự arms có seed và số lần lặp
   trước F3 bằng collector `--prepare-only`. Protocol mặc định đo một lần mỗi arm;
   không dùng nó để claim variance qua nhiều lần provider gọi.
4. Nếu đổi rubric/config/prompt/budget sau freeze, dùng cycle và held-out độc lập phù
   hợp. Không xóa lock hoặc đổi tên failed observations để chạy tuning tiếp.

## Thu và review outputs

Collector nhận cùng request/scope/history/selection ở hai arms, randomize thứ tự,
tắt answer/LLM caches và lưu từng arm ngay sau khi gọi. Provider lỗi dừng run và giữ
partial observations; một pair thiếu arm không đủ nghiệm thu. Token usage thiếu
được ghi `unknown`, cost không có số liệu là `null`, không quy thành chi phí 0.

Project owner theo policy hoặc reviewer độc lập khác tác giả question đánh giá đúng bytes output gắn `answer_sha256`;
`reviewed_at` có timezone và phải sau `observed_at`. Khi khả thi, người điều phối
ẩn arm identity khi giao outputs, khôi phục mapping sau review. Double-review sample
và mọi disagreement nếu có nhiều reviewer; owner self-review phải ghi role đó và
không được claim là độc lập. Lưu decisions/adjudication riêng trong raw archive.
Collector không tạo approval hoặc tự coi automatic judge là human review.

- Liệt kê **mọi** factual claim trong phần answer, kể cả claim không có trong structured
  `claims`; `all_factual_claims_enumerated=true` chỉ sau khi đã kiểm tra toàn output.
- Với mỗi claim, ghi `supported`, `requires_citation` và từng citation có `supports`.
  Citation đúng document/page/quote nhưng chứng minh số, đơn vị hay đối tượng khác là
  semantic support **false**. Citation cho premise chưa đủ kết luận cũng là false.
- Claim multi-hop chỉ `supported=true` khi **mọi hop** đủ; ghi
  `all_hops_supported=true` sau khi đối chiếu các source chunks và qualifiers.
- `rubric_satisfied` đánh giá correctness/completeness; `covered_gold_claim_ids` chỉ
  liệt kê những gold claims đã trả lời đúng và đủ. Không đánh dấu đủ chỉ vì lấy được
  ít nhất một gold chunk. False abstention của positive tính accuracy 0.
- Negative trả lời khẳng định không có căn cứ có `unsupported_affirmative_answer=true`.
  Provider lỗi không phải abstention thành công và không được dùng để chấm FPR tốt.

## Aggregation và nghiệm thu

`paired_answer_quality` lưu numerator/denominator của accuracy, answer FPR, citation
precision/recall, groundedness và gold claim coverage. Denominator 0 là `null` và
không được PASS. S4 chấm riêng human test và human holdout: citation precision và
groundedness ≥98%, precision không giảm; accuracy/citation recall giảm tối đa 0,5
điểm phần trăm; answer FPR ≤1%; gold claim coverage không giảm.

S5 tái tính all-gold@5 riêng overall, hard/multi-hop và các tag critical hiện có.
Report ranking có strata, connected-group bootstrap ≥10.000 lần, số groups và
sample size; báo insufficient power khi subgroup nhỏ. Zero negative errors chưa
chứng minh population FPR ≤1%; report ghi upper bound với số negative groups độc lập.

Release validator đối chiếu record/request/rubric/protocol hashes, labels, author,
tags, caches, raw live calls và physical citation evidence, rồi tính lại metrics.
Pending review, missing raw evidence hoặc sửa dữ liệu sau review đều chặn release.
