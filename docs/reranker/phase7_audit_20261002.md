# Phase 7 — audit và bàn giao thay đổi ngày 02/10/2026

Roadmap gốc: [plan.md](../../plan.md#phase-7--reranker).
Task spec: [phase7_task_spec.md](phase7_task_spec.md).

M0 đã được chạy trên index vật lý và PASS. Baseline Phase 6, historical RC3 và
hai frozen reruns không được thay thế. Các sửa đổi roadmap/release plan có sẵn
trước phiên này được giữ lại; file câu hỏi gốc cũng giữ nguyên bytes.

## Kết quả triển khai

- Candidate staging, summary và lineage tái sinh deterministic bằng
  `python -m scripts.benchmarks.prepare_human_candidates`; `--verify` kiểm tra lại
  hash, counts và toàn bộ output. Direct-authored questions không cần URL FAQ giả.
- Connected family được gom theo liên kết bắc cầu và paraphrase; không gom chỉ vì
  cùng PDF. Split freeze ghi hash canonical **sau** assignment, giữ exact split union,
  khóa publisher đồng thời và từ chối thay frozen bytes. JSON bytes có newline ổn định
  trên Windows; failed attempts không đè manifest đã freeze.
- Runtime nhận history/selected text, giới hạn ngân sách, làm rõ khi thiếu ngữ cảnh,
  chỉ dùng user topic để resolve. Selected text không được coi là evidence; citation
  vẫn phải kiểm chứng vào tài liệu. Scope rỗng khác default scope; authorization từ
  server được giữ xuyên retrieval/cache. Benchmark adapters dùng cùng contract.
- Activation bắt buộc warm-up; warm lỗi trả Phase 6. Readiness và HTTP 503 phản ánh
  model chưa ready. Model lease giữ singleton trong process và giải phóng sau provider
  cuối cùng cùng inference đang chạy; request không load model sau activation.
- Trace tách routing, inference thực sự bắt đầu, áp dụng ranking, fallback và abstention.
  Capacity lưu wall-clock duration và successful throughput, loại fast-fail khỏi numerator.
- Quality bổ sung all-gold/evidence recall và paired bootstrap theo connected groups.
  Negative FPR có numerator/denominator; upper bound zero-error dùng số group độc lập.
  Group definitions giống nhau ở OOF calibration, split freeze, exposure và CI;
  subgroup có counts/power, positive/negative denominators và metrics riêng.
  Bootstrap cache dùng immutable inputs và copy kết quả; raw observations thay đổi
  vẫn được tái tính, không reuse verdict cũ.
- S1–S6 bắt buộc tại M1/M3/M6/M7 và bind trong release manifest/activation.
  Validator tái tính packet review, raw paths/hashes, group statistics, semantic
  answer/citation assessment, đủ hop và observation/resource/throughput.
- Live paired answer collector dùng cùng inputs ở hai arms, randomize thứ tự có seed,
  tắt answer/LLM caches, lưu partial observations và để semantic review **pending**.
  LLM/prompt/context/rubric protocol phải freeze trước khi mở held-out ranking/answers.
  Mỗi arm được lưu ngay; provider failures không tính thành quality success, usage/cost
  thiếu được ghi unknown. Protocol review tại [paired_answer_review_protocol.md](paired_answer_review_protocol.md).

## Verification đã chạy

- Full suite: **413 passed, 2 live-LLM tests skipped**, **89,07% coverage** (yêu cầu 85%).
  Raw JUnit/coverage ở `.tmp/phase7-verified-tests.xml` và `.tmp/phase7-verified-coverage.json`.
  Summary/source/hash bền vững: [phase7_code_verification.json](../../evaluation/results/phase7_code_verification.json).
  Summary/source/hash bền vững: [phase7_code_verification.json](../../evaluation/results/phase7_code_verification.json).
- Compile, diff check, secret scan tracked/untracked: PASS.
- Candidate regeneration và `--verify`: PASS; 180 raw records/59 groups/155 overlaps.
- [Verified RTX 4060 probe](../../evaluation/results/phase7_startup_lifecycle_verified.json):
  BGE FP16 offline, startup 14,31s, cold request bị chặn trước load, hai providers chia sẻ
  một model, repeated score delta 0, last close không giữ reranker model. Timing này là
  startup/dev diagnostic, không phải request SLO hoặc M7 capacity.
- Validator M12 tại `.tmp/phase7-verified-readiness.json`: conditional, `score=null`,
  M0 PASS; M1–M12/S1–S6 BLOCKED. Không xuất manifest 10/10 hoặc bật production.

## Dữ liệu và giới hạn thực tế

180 câu được tiếp nhận theo xác nhận tác giả của chủ dự án. Review được mô tả là
nhóm cùng soạn và đồng thuận, chưa có hồ sơ reviewer riêng. Chủ dự án **Trương Bảo Kiên**
đã duyệt bản xác nhận qua chat ngày 02/10/2026:
[human_review_confirmation.draft.md](../benchmarks/human_review_confirmation.draft.md).

Audit tìm 155 câu trùng văn bản với dataset khác và xác minh 89 câu từng được đo
trên dev bằng raw study có dataset hash khớp. 91 câu chưa được xác minh đủ lịch sử;
không tự coi chúng là held-out độc lập. Còn 45 negative thiếu explicit document scope.
Không freeze hoặc tạo approval giả để vượt M1.

Target do chủ dự án chọn là **RTX 4060 local trước, public sau**. GPU runtime có sẵn
tại `.tmp/phase7-gpu-runtime`; tên `reranker-gpu-runtime` trong báo cáo cũ là historical.
API key Gemini không có trong environment lúc kiểm tra. Hai live tests, paired LLM
quality và HTTP với LLM vì vậy chưa có evidence mới. Các study dev cũ thất bại vẫn
được giữ; không hạ ngưỡng quality hoặc đổi tên chúng thành release evidence.

Inventory có hashes/source/runtime/status tại
[phase7_evidence_inventory.json](../../evaluation/results/phase7_evidence_inventory.json).
Exposure registry tại [phase7_exposure_registry.json](../../data/benchmark/phase7_exposure_registry.json).
Mỗi task có trạng thái thực tế tại [phase7_task_ledger.json](../../evaluation/results/phase7_task_ledger.json).

## Quy trình tiếp tục

1. Bản xác nhận nhóm đã duyệt; bổ sung review/scope/exposure còn thiếu, giữ nhóm đã exposure
   ở dev/research. Chỉ thu thêm những nhóm độc lập còn thiếu để nghiệm thu.
2. Chốt F0/dev eligibility và tìm joint configuration đạt route/quality/FPR/latency.
3. Freeze source/runtime/data, chạy M1–M5 tuần tự; tạo S1/S2 từ đúng packet/probe.
4. Freeze answer protocol trước M6; đo ranking và paired live answers, review semantic
   outputs, tái tính S3–S5. Sau đó capacity/HTTP/security/fault/rollback/canary trên local.
5. Package từ clean checkout khi tất cả M0–M12 và S1–S6 PASS. Public deployment cần
   measurements/bindings riêng sau local acceptance.
