# Kiểm chứng và release reranker

> **Phạm vi hiện hành 08/10/2026:** owner đã thay Phase 7 bằng sáu hạng mục chất lượng sản phẩm C7-01–C7-06 trong [plan.md](../../plan.md#phase-7--hoàn-thiện-chất-lượng-sản-phẩm-phạm-vi-tinh-gọn). Optional reranker giữ tắt; các task/19 gate trong tài liệu này là hợp đồng qualification được hoãn, vẫn phải đạt trước khi bật reranker production. Không dùng các checkpoint cũ bên dưới làm mục tiêu 20/20–19/19 hiện hành. Trạng thái mới nằm ở `active_tasks` của [ledger](../../evaluation/results/phase7-completion-20261004/completion_task_ledger.json).

Validator duy nhất là `evaluation/reranker/validate_reranker_release.py`. Điểm 10.0 chỉ
được xuất khi M0–M12 và S1–S6 đều PASS, hash khớp và working tree sạch. `--through M0`
có thể PASS nhưng `score` vẫn là `null`; đó chỉ là kiểm tra một phần.

Cycle được chọn bởi `configs/phase7_release_cycle.json`. Cycle đang dùng là
`phase7-dev-metadata-20261003-r10`, đã đo lại M0–M3/S1–S2 PASS. Cycle này sửa
context và 14 nhãn độ khó dev có source audit; giữ nguyên test/holdout và
lịch sử exposure của r8. Không tuyên bố heldout mới. M4 chưa có fit dev đạt
ngưỡng; các gate tiếp theo cần phép đo cùng source/runtime/model. Gemini gọi
mới đang báo quota 429; S2 cho phép cache, M6 answer quality phải chạy uncached.
Telemetry staging chưa hoàn tất.
Giữ `RERANKER_ENABLED=false`. Các fixture trong tests và kiểm tra chèn lỗi
không phải bằng chứng quality, performance hoặc staging của deployment.

Target của cycle hiện tại là **RTX 4060 local trước, public sau**. GPU interpreter
có sẵn là `.venv/Scripts/python.exe` (CUDA đã kiểm tra ngày 13/10/2026).
Môi trường `.tmp/phase7-gpu-runtime` cũ đã được dọn sau khi xác minh các file
Torch/functorch/torchgen trùng với `.venv`; xem [biên bản dọn](../../evaluation/results/storage-cleanup-20261013.json).
Giữ cùng GPU interpreter/device/dtype/inference options xuyên M3–M12. Các ví dụ CPU
bên dưới minh họa CLI; khi nghiệm thu RTX thay interpreter và `--device cuda:0
--dtype float16` nhất quán với F1. Không ghép latency của GPU với quality identity CPU.
Theo dõi phần đã làm và blockers ở [audit triển khai](phase7_audit_20261002.md).

## Trình tự chạy

Chạy tại thư mục gốc repo bằng PowerShell. Hoàn tất review code trước khi đo
release: thay đổi source sau khi đo sẽ làm các binding mất hiệu lực. Các lệnh
đo kiểm tra gate trước đó và dừng nếu chưa PASS. Không sử dụng `--exploratory`
để tạo release artifact; chế độ này luôn ghi `conditional`.

```powershell
# M0: kiểm tra baseline RC3 đã freeze và các file index vật lý.
.venv/Scripts/python.exe -m evaluation.reranker.validate_reranker_release --through M0

# Preflight: lỗi từng qid, negative scope và coverage của split an toàn.
.venv/Scripts/python.exe -m scripts.phase7_release_pipeline preflight

# Nạp key local đã ignore vào process environment, không in hoặc commit key.
# M3 workflow đo snapshot/provider, thu S2 context/cache/lifecycle và validate.
.venv/Scripts/python.exe -m scripts.operations.with_gemini_key evaluation.reranker.release_workflow model --model-dir .tmp/models/1427fd652930e4ba29e8149678df786c240d8825 --device cuda:0 --dtype float16
# M1/S1: dataset và audit phải được human_benchmark_intake export từ các packet
# đã duyệt. Exposure registry phải hoàn tất và bind đúng pool/lineage/index.
# Workflow đọc owner policy, kiểm tra audit trước freeze, rồi build S1 và validate M1.
.venv/Scripts/python.exe -m scripts.phase7_release_pipeline human-freeze --assign-splits --review-audit data/benchmark/human_retrieval_review_audit.jsonl

# M2: candidate coverage riêng, không phải ranking hoặc answer quality.
.venv/Scripts/python.exe -m evaluation.retrieval.evaluate_candidate_coverage

# M3: trỏ tới snapshot LOCAL có tên thư mục là revision đã pin.
$rerankerSnapshot = 'D:/Project/.tmp/models/REPLACE_WITH_REVISION'
.venv/Scripts/python.exe -m evaluation.reranker.check_model_snapshot --model-dir $rerankerSnapshot --device cpu
.venv/Scripts/python.exe -m evaluation.reranker.check_reranker_faults --gate M3
# S2: context/cache cases và lifecycle counters từ đúng runtime/index/snapshot M3.
.venv/Scripts/python.exe -m evaluation.reranker.build_supplemental_report --gate S2 --observations evaluation/results/raw/context_lifecycle_observations.json

# M4: fit trên human dev; freeze trước khi mở test/holdout để kiểm tra route.
.venv/Scripts/python.exe -m evaluation.reranker.calibrate_hard_query_route

# M5: chạy đủ 8/10/12/16/20, chọn theo quality và latency trên dev.
.venv/Scripts/python.exe -m evaluation.reranker.sweep_reranker_caps --model-dir $rerankerSnapshot --device cpu
```

M0 có thể tạo lại bằng `evaluation.retrieval.freeze_retrieval_baseline` với hai báo cáo
rerun độc lập từ clean worktree (`--rerun-a`, `--rerun-b`, `--model-dir`,
`--source-tree`). Historical RC3 giữ nguyên. Không thay baseline để làm gate PASS.

Sau M5, cấu hình activation experimental để chạy các phép đo sau. Đây là
activation phục vụ đo lường; production cần manifest đạt đủ M0–M12.

```powershell
$smoke = Get-Content evaluation/results/model_snapshot_smoke.json -Raw | ConvertFrom-Json
$env:RERANKER_ENABLED = 'true'
$env:RERANKER_DEPLOYMENT = 'experimental'
$env:RERANKER_MODE = 'hard_only'
$env:RERANKER_MODEL = $smoke.model_identity.model_name
$env:RERANKER_MODEL_REVISION = $smoke.model_identity.model_revision
$env:RERANKER_MODEL_SHA256 = $smoke.model_identity.model_sha256
$env:RERANKER_TOKENIZER_REVISION = $smoke.model_identity.tokenizer_revision
$env:RERANKER_DEVICE = $smoke.model_identity.device
$env:RERANKER_DTYPE = $smoke.model_identity.dtype
$env:RERANKER_BATCH_SIZE = [string]$smoke.model_identity.batch_size
$env:RERANKER_MAX_LENGTH = [string]$smoke.model_identity.max_length
$env:RERANKER_BATCH_WINDOW_MS = [string]$smoke.model_identity.batch_window_ms
$env:RERANKER_MAX_BATCH_PAIRS = [string]$smoke.model_identity.max_batch_pairs
$env:RERANKER_SCORE_CACHE_SIZE = '0'
$env:RERANKER_QUEUE_LIMIT = '19'
$env:RERANKER_MODEL_DIR = $rerankerSnapshot
$env:RERANKER_CALIBRATION = 'evaluation/results/reranker_score_calibration.json'
$env:RERANKER_TIMEOUT_MS = '1000'
$env:RERANKER_WARMUP = 'true'

# Freeze protocol answer/rubric trước khi ranking đọc held-out.
# Rubric đã duyệt nằm trong results/raw và có gold_claim_ids cho primary qids.
.venv/Scripts/python.exe -m evaluation.reranker.collect_paired_answers --prepare-only --llm-config configs/default.yaml --rubric evaluation/results/raw/answer_rubric.json --output evaluation/results/raw/paired_answers.json

# M6: paired quality, bootstrap 10000 lần, per-query delta và regressions.
.venv/Scripts/python.exe -m evaluation.retrieval.compare_retrieval_quality
.venv/Scripts/python.exe -m evaluation.reranker.build_supplemental_report --gate S3
.venv/Scripts/python.exe -m evaluation.reranker.build_supplemental_report --gate S5
.venv/Scripts/python.exe -m evaluation.reranker.collect_paired_answers --llm-config configs/default.yaml --rubric evaluation/results/raw/answer_rubric.json --output evaluation/results/raw/paired_answers.json
# Review outputs theo protocol bằng role project_owner hoặc independent_reviewer;
# collector để pending và semantic decisions không được tự sinh.
# --bindings dùng frozen smoke identity; protocol bổ sung LLM/prompt/context/rubric.
.venv/Scripts/python.exe -m evaluation.reranker.paired_answer_quality --observations evaluation/results/raw/paired_answers.reviewed.json --rubric evaluation/results/raw/answer_rubric.json --bindings evaluation/results/model_snapshot_smoke.json

# M7: thay số RAM bằng limit thật của deployment. Ví dụ 16 GiB:
.venv/Scripts/python.exe -m evaluation.reranker.measure_reranker_capacity --deployment-ram-bytes 17179869184 --profile cpu-small
.venv/Scripts/python.exe -m evaluation.reranker.measure_reranker_http --model-dir $rerankerSnapshot --llm-config configs/default.yaml --deployment-ram-bytes 17179869184
.venv/Scripts/python.exe -m evaluation.reranker.build_supplemental_report --gate S6 --observations evaluation/results/raw/observability_observations.json

# M8: chuẩn bị >=50 case adversarial có expected behavior và đủ category.
.venv/Scripts/python.exe -m evaluation.reranker.evaluate_reranker_security --cases data/benchmark/reranker_adversarial.jsonl

# M9: failure matrix; M10: hai process độc lập, dùng chung answer cache.
.venv/Scripts/python.exe -m evaluation.reranker.check_reranker_faults --gate M9
.venv/Scripts/python.exe -m evaluation.reranker.verify_reranker_rollback

# M11: telemetry lấy từ staging thật, gồm cả các bài tập auto-rollback.
.venv/Scripts/python.exe -m evaluation.reranker.audit_canary_staging --observations .tmp/staging-windows.json --fault-observations .tmp/staging-faults.json

# M12: chạy sau khi working tree sạch; output dùng thư mục ignored.
.venv/Scripts/python.exe -m evaluation.reranker.release_workflow release --model-dir $rerankerSnapshot
```

Production phải cấu hình `RERANKER_DEPLOYMENT=production` và
`RERANKER_RELEASE_MANIFEST=evaluation/results/reranker_release_manifest.json`. Activation
kiểm tra đủ gate, code runtime, model, device, index, calibration và cap. Sai
bất kỳ binding nào thì trả về Phase 6. Snapshot được xác minh trước activation;
warm-up có timeout startup riêng 60 giây, request giữ budget đã cấu hình.

Precision/batching khác mặc định cần truyền cùng `--dtype`, `--batch-size`,
`--max-length`, `--input-format`, `--batch-window-ms` và `--max-batch-pairs` cho M3/M5. M5 từ
chối identity khác M3. Khi dùng `phase7_release performance`, queue mặc định
là 19 (20 admission slots), có thể đổi bằng `--queue-limit` trước phép đo.

M5 release dùng mô hình xác suất ba lớp (không có bằng chứng, chưa đủ, đủ), fit
trên dev với cross-validation theo `paraphrase_group`. Ngưỡng chấp nhận và từ
chối được chọn bằng kết quả out-of-fold, kiểm tra lại trên model cuối và tính
lại từ raw observations ở release validator. Trạng thái chưa chắc chắn và lỗi
provider trả Phase 6. `--evidence-policy score` và `--low-score-action` chỉ còn
dùng để khảo sát; chúng không đạt M5 release. Phép đo trên câu hỏi tự nhiên cho
thấy threshold fit trên 57 câu formal chưa chuyển tốt; xem
[báo cáo vòng 3](abstention_optimization_report.md) trước khi chọn abstain.
M4 release dùng xác suất hard-query từ hai đặc trưng dùng chung với serving:
thao tác cần xử lý (`operation_required`) và câu hỏi dài (`long_request`).
Topic từ history cung cấp chủ đề, không thêm thao tác. QID, gold, language,
template và difficulty không đi vào feature runtime. Fit theo các nhóm
paraphrase/source/template trên dev. Ngưỡng
chọn bằng dự đoán out-of-fold và được kiểm tra lại trên model cuối; test và
holdout chỉ được mở sau khi route artifact đã đóng băng. Query ngoài vùng đo
được xử lý theo Phase 6. `--route-policy threshold` chỉ dành cho khảo sát.
M7 lưu `reranker_http_end_to_end.json`: HTTP thật với LLM thật, cache tắt,
100 request mỗi mức đồng thời 1/5/10/20, cả easy/hard/negative/scoped. Báo cáo
giữ từng request và thời gian routing, retrieval, queue, inference, LLM,
grounding, serialization, transport. Thiếu cấu hình hoặc khóa LLM sẽ chặn M7.
M2 lưu độ phủ từng `difficulty`, `category`, `tag` và nhóm multi-hop,
multi-document, table, year, semester, numeric, scoped. Validator yêu cầu đủ
tất cả gold chunk cho từng nhóm có câu trả lời, rồi tính lại từ raw candidates.
Manifest production ràng buộc queue, timeout, circuit limit và score cache
đã đo; đổi các giới hạn này sau đó sẽ bị activation từ chối.

`phase7_release quality-collect --rubric <file> --observations <file-mới>`
đóng băng protocol trước ranking, đo paired retrieval, xây S3/S5 rồi gọi LLM
thật với cache tắt. Kết quả dừng ở `pending_semantic_review`; đánh giá từng
câu trả lời/citation theo rubric và lưu nguồn gốc đánh giá trước khi chạy
`phase7_release quality --rubric <file> --observations <file-đã-review>` để
xây S4 và validate M6. Dùng quyền owner self-review đã được chủ dự án cho phép;
không tuyên bố review độc lập khi người đánh giá là assistant theo ủy quyền.

`phase7_release performance` đo capacity, HTTP và S6 cùng budget đã khai báo.
Capacity chọn hard workload bằng route runtime thực tế; tag `exact_code`
không tự loại câu hỏi nhiều mã môn cần hybrid/rerank. Resource checkpoints
đo RSS/PID/thời gian thật và VRAM của đúng device, lưu tại
`raw/reranker_observability_observations.json` và bản có digest. Không điền
resource samples giả để xây S6.

Mỗi subprocess đo qua workflow có receipt riêng trong
`raw/measurement_receipts/`: cycle, command tái chạy được, thời gian UTC thật,
source/runtime trước và sau, input hash và hash các output thay đổi. Lỗi chạy
vẫn được giữ; source đổi trong lúc đo làm lần chạy bị từ chối. Receipt không
tự chứng minh quality gate PASS. Validator M12 bind byte các receipt hiện có;
validation/packaging không tạo receipt mới sau khi đóng manifest.

## Human benchmark

Current handoff: the frozen owner-approved benchmark is
`data/benchmark/phase7_review_cycles/phase7-dev-metadata-20261003-r10`.
The owner's standing bulk approval is recorded by a hash-bound confirmation;
exported record decisions and source audits are generated from that authorization.
No additional owner confirmation is required for the already approved inputs.
AI-created questions remain explicitly identified as commissioned AI data.

The historical draft cycle is
[phase7-release-20261003-r3](../benchmarks/phase7_review_cycles/phase7-release-20261003-r3/phase7_review_questions.draft.md).
It contains 180 question/context/evidence records and 45 pending negative-scope
proposals. The older group-review dossier is historical.
Verify the generated templates before review:

```powershell
.venv/Scripts/python.exe -m scripts.benchmarks.prepare_phase7_review --verify --output-data-dir data/benchmark/phase7_review_cycles/phase7-release-20261003-r3 --output-docs-dir docs/benchmarks/phase7_review_cycles/phase7-release-20261003-r3
```

Keep per-record decisions in a separate copy; the generator refuses to overwrite existing
drafts. Preparation has no model calls or split assignment. After actual review,
correct affected records, bind the corrected question/index hashes and submit
the real author/reviewer packets below. A guide approval alone is not a packet.

Dùng schema mẫu tại `configs/human_benchmark_record.example.json`. Tổng ít
nhất 150 record: 100 answerable, 20 negative, 15 hard/multi-hop, 15 exact-code,
10 ambiguous/abstention; tag có thể overlap. Dev/test/holdout đều cần positive,
negative, easy và hard. Các paraphrase cùng `paraphrase_group` phải ở một split.

Mỗi record cần author human, reviewer role `project_owner` hoặc `independent_reviewer`, `review_status=approved`, đủ
`review_checks`. Câu hỏi từ website cần source URL và thời gian có timezone;
`question_source=direct_author` dùng nguồn gốc tác giả thật, không cần URL FAQ giả.
`freeze_human_benchmark` tự đọc policy cạnh dataset; owner self-review không cần
reviewer thứ hai. Với phê duyệt bulk đã có trong phiên làm việc, owner confirmation
bind tập record được duyệt và exporter tạo audit từng record; không yêu cầu
chủ dự án gửi lại quyết định riêng cho các record đã duyệt.
Review packet vẫn phải bind question/index/hash và thời điểm ghi nhận có timezone. Positive phải có
`doc_id/chunk_id/page` khớp index đã freeze. `evidence_source=frozen_pdf` bắt
buộc; câu trả lời từ website hiện tại không được làm gold evidence. Validator
kiểm tra lại nội dung dataset, split hash, duplicate và paraphrase gần nhau.

Freeze sinh `human_retrieval_dev/test/holdout.jsonl`, review report và manifest.
Threshold không được chỉnh sau khi xem test/holdout. Nếu held-out fail, báo cáo
phải giữ FAIL/conditional; bắt đầu vòng nghiên cứu mới với dữ liệu review mới
thay vì tuning trên held-out đã xem.

## Adversarial và grounding

Case có `id`, `category`, `question`, `expected`, tùy chọn `doc_ids`, `filters`,
`gold_evidence` và `attack`. `expected` là `abstain`, `phase6_fallback` hoặc
`valid_evidence`; loại cuối cần gold evidence từ index. Coverage bắt buộc:
out_of_corpus, similar_wrong_document, conflicting_documents, exact_code_trap,
year_mismatch, entity_mismatch, chunk_prompt_injection, malformed_metadata,
duplicate_chunks, scope_restriction, empty_result, fake_citation.

`attack` hỗ trợ chèn prompt vào nội dung gửi cross-encoder, fake citation,
wrong_doc_scope, duplicate_output và malformed_score. Bộ kiểm tra so sánh output
với frozen evidence và Phase 6, rồi chạy các test grounding Phase 4/5 riêng.
Ranking quality và grounded answer quality được báo cáo riêng; số Recall của
retrieval không được dùng để claim chất lượng câu trả lời LLM thật.

## Canary và rollback

Gắn `CanaryController` vào `CampusAIQueryService`, truyền `request_id` ổn định
vào `ask`/`retrieve`. Traffic đi theo 0→1→5→10→25%, mỗi bước cần ba cửa sổ khỏe.
Cả explicit `mode=phase7` cũng phải qua cohort. Feed số liệu thực tế vào
`service.observe_canary_window(window)`; khi lỗi, service tắt reranker, đóng
provider và invalidate retrieval cache. Answer cache dùng namespace khác
Phase 6, nên rollback không tái dùng answer reranked.

Window cần ít nhất 100 request, thời gian bắt đầu/kết thúc có timezone,
traffic_percent, p50/p95/p99, timeout/FPR/error/baseline-error/fallback/selection
rates, easy unnecessary rate, hard coverage, RSS/RAM limit, queue depth và
provenance/scope/citation counts. Không điền `0` khi chưa đo; thiếu metric sẽ
bị reject. Ba cửa sổ p95 >1000ms, timeout >1%, FPR >1%, tăng error rate, RSS
>75% RAM hoặc bất kỳ lỗi citation/scope/provenance sẽ trigger rollback.

Telemetry JSON cần environment=staging, environment_id, collector và bindings
`source_sha256`, `runtime_sha256`, `index_sha256`, `phase6_calibration_sha256`,
`calibration_sha256`, `model_identity_sha256`. Fault telemetry có `exercises`:
mỗi bài tập chứa expected_reason, windows, service_phase7_enabled_after=false
và new_reranker_calls_after=0. Phải đo đủ tám trigger trong `ROLLBACK_REASONS`.

Telemetry sau calibration còn bind `route_calibration_sha256`,
`training_split_sha256`, `human_benchmark_sha256`. Grounding XML được lưu tại
`evaluation/results/grounding_test_reports/`; validator kiểm tra hash và các
count test/errors/failures/skipped, không dùng file chỉ còn trong `.tmp`.

`doc_ids` của benchmark human phải khai báo scope hợp lệ; gold không được vượt
scope/filter. Review cần `no_paraphrase_leakage=true`, `expected_behavior=true`.
Lệnh fit bị khóa sau khi mở held-out tương ứng, kể cả khi gate fail.
Xem [workflow đầy đủ](release_plan.md) để chạy các target `reranker-*`.

## Kiểm tra code

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp=.tmp/pytest-reranker-review
.venv/Scripts/python.exe -m evaluation.reranker.check_reranker_faults --exploratory --work-dir .tmp/reranker-fault-review
```

Lệnh exploratory trả exit code 1 vì artifact conditional, kể cả mọi fault
check pass. Hai live LLM integration tests cần cấu hình riêng; skip không
được xem là bằng chứng grounded answer production.
