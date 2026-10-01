# Kiểm chứng và release reranker

Validator duy nhất là `evaluation/validate_reranker_release.py`. Điểm 10.0 chỉ
được xuất khi M0–M12 đều PASS, hash khớp và working tree sạch. `--through M0`
có thể PASS nhưng `score` vẫn là `null`; đó chỉ là kiểm tra một phần.

Hiện chưa có dataset human-natural được review độc lập hoặc telemetry staging.
Giữ `RERANKER_ENABLED=false`. Các fixture trong tests và kiểm tra chèn lỗi
không phải bằng chứng quality, performance hoặc staging của deployment.

## Trình tự chạy

Chạy tại thư mục gốc repo bằng PowerShell. Hoàn tất review code trước khi đo
release: thay đổi source sau khi đo sẽ làm các binding mất hiệu lực. Các lệnh
đo kiểm tra gate trước đó và dừng nếu chưa PASS. Không sử dụng `--exploratory`
để tạo release artifact; chế độ này luôn ghi `conditional`.

```powershell
# M0: kiểm tra baseline RC3 đã freeze và các file index vật lý.
.venv/Scripts/python.exe -m evaluation.validate_reranker_release --through M0

# M1: nhập câu hỏi thật vào data/benchmark/human_retrieval.jsonl,
# hoàn thành review độc lập và mapping frozen PDF evidence trước lệnh này.
.venv/Scripts/python.exe -m evaluation.freeze_human_benchmark

# M2: candidate coverage riêng, không phải ranking hoặc answer quality.
.venv/Scripts/python.exe -m evaluation.evaluate_candidate_coverage

# M3: trỏ tới snapshot LOCAL có tên thư mục là revision đã pin.
$rerankerSnapshot = 'D:/Project/.tmp/models/REPLACE_WITH_REVISION'
.venv/Scripts/python.exe -m evaluation.check_model_snapshot --model-dir $rerankerSnapshot --device cpu
.venv/Scripts/python.exe -m evaluation.check_reranker_faults --gate M3

# M4: fit trên human dev; freeze trước khi mở test/holdout để kiểm tra route.
.venv/Scripts/python.exe -m evaluation.calibrate_hard_query_route

# M5: chạy đủ 8/10/12/16/20, chọn theo quality và latency trên dev.
.venv/Scripts/python.exe -m evaluation.sweep_reranker_caps --model-dir $rerankerSnapshot --device cpu
```

M0 có thể tạo lại bằng `evaluation.freeze_retrieval_baseline` với hai báo cáo
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
$env:RERANKER_MODEL_DIR = $rerankerSnapshot
$env:RERANKER_CALIBRATION = 'evaluation/results/reranker_score_calibration.json'
$env:RERANKER_TIMEOUT_MS = '1000'
$env:RERANKER_WARMUP = 'true'

# M6: paired quality, bootstrap 10000 lần, per-query delta và regressions.
.venv/Scripts/python.exe -m evaluation.compare_retrieval_quality

# M7: thay số RAM bằng limit thật của deployment. Ví dụ 16 GiB:
.venv/Scripts/python.exe -m evaluation.measure_reranker_capacity --deployment-ram-bytes 17179869184 --profile cpu-small

# M8: chuẩn bị >=50 case adversarial có expected behavior và đủ category.
.venv/Scripts/python.exe -m evaluation.evaluate_reranker_security --cases data/benchmark/reranker_adversarial.jsonl

# M9: failure matrix; M10: hai process độc lập, dùng chung answer cache.
.venv/Scripts/python.exe -m evaluation.check_reranker_faults --gate M9
.venv/Scripts/python.exe -m evaluation.verify_reranker_rollback

# M11: telemetry lấy từ staging thật, gồm cả các bài tập auto-rollback.
.venv/Scripts/python.exe -m evaluation.audit_canary_staging --observations .tmp/staging-windows.json --fault-observations .tmp/staging-faults.json

# M12: chạy sau khi working tree sạch; output dùng thư mục ignored.
.venv/Scripts/python.exe -m evaluation.validate_reranker_release --release-manifest .release/reranker/release_manifest.json
```

Production phải cấu hình `RERANKER_DEPLOYMENT=production` và
`RERANKER_RELEASE_MANIFEST=.release/reranker/release_manifest.json`. Activation
kiểm tra đủ gate, code runtime, model, device, index, calibration và cap. Sai
bất kỳ binding nào thì trả về Phase 6. Snapshot được xác minh trước activation;
warm-up có timeout startup riêng 60 giây, request giữ budget đã cấu hình.

## Human benchmark

Dùng schema mẫu tại `configs/human_benchmark_record.example.json`. Tổng ít
nhất 150 record: 100 answerable, 20 negative, 15 hard/multi-hop, 15 exact-code,
10 ambiguous/abstention; tag có thể overlap. Dev/test/holdout đều cần positive,
negative, easy và hard. Các paraphrase cùng `paraphrase_group` phải ở một split.

Mỗi record cần author human, reviewer độc lập, `review_status=approved`, đủ
`review_checks`, source URL và thời gian có timezone. Positive phải có
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

## Kiểm tra code

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp=.tmp/pytest-reranker-review
.venv/Scripts/python.exe -m evaluation.check_reranker_faults --exploratory --work-dir .tmp/reranker-fault-review
```

Lệnh exploratory trả exit code 1 vì artifact conditional, kể cả mọi fault
check pass. Hai live LLM integration tests cần cấu hình riêng; skip không
được xem là bằng chứng grounded answer production.
