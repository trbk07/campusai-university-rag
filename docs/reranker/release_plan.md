# Kế hoạch đưa Phase 7 lên 10/10

Ngày lập: **02/10/2026**, timezone Asia/Bangkok. Roadmap gốc là
[`plan.md`](../../plan.md#phase-7--reranker); không di chuyển hoặc loại file đó khỏi Git.
Tài liệu này triển khai backlog **P7-01–P7-20** trong roadmap.
Checklist thực thi từng task, subtasks, file/module cần sửa, artifact contracts,
chuẩn metric và freeze protocol được mở rộng tại
[`phase7_task_spec.md`](phase7_task_spec.md). Dùng tài liệu đó khi nhận task;
tài liệu này giữ mục tiêu release, ngưỡng hiện hành và CLI workflow.

Trạng thái: **M0/M1/M2/S1 PASS; acceptance các gate còn lại đang đo**.
Cycle được chọn bởi `configs/phase7_release_cycle.json`; benchmark owner r8 giữ
nguyên, candidate r9 đạt Recall@40 và all-gold recall 1,0 trên test và holdout.
M3/S2 đã PASS trên GPU cùng source/runtime/model; đang chuyển sang M4 dev-only route fit.
Full offline verification gần nhất: **548 passed, 2 skipped, coverage 89,29%**;
hai integration Gemini thật PASS riêng. Hai full live attempts có lỗi provider
HTTP 503 được giữ lại. Chưa có validator score 10/10.
BGE FP16 real startup probe trên RTX 4060
PASS; target do chủ dự án chọn là local trước, public sau. Review/scope/exposure,
joint dev feasibility và các measurements freeze còn thiếu. Xem
[audit triển khai](phase7_audit_20261002.md), [current verification](../../evaluation/results/phase7_code_verification_20261003_r5.json),
[readiness report](../../evaluation/results/phase7_readiness_20261003_r5.json) và [task ledger](../../evaluation/results/phase7_task_ledger.json).
Điểm 5,5/10 và 385 tests/88,85% trước phiên này chỉ là historical audit.

## 1. Mục tiêu và nguyên tắc nghiệm thu

Phase 7 hoàn thành khi ranking và câu trả lời có citation cải thiện trên dữ liệu
độc lập, đạt ngân sách tài nguyên và chịu được lỗi vận hành. Candidate pool giữ 40;
rerank cap release chỉ thuộc **8/10/12/16/20**. Không mở rộng sang KG, temporal engine,
framework RAG mới hoặc UI mới. Sửa context/scope contract khi benchmark cần là trong scope.

- **Gate hiện hành:** validator M0–M12, hashes/bindings và clean working tree cùng pass.
- **Gate bổ sung đã tích hợp:** S1–S6 kiểm chứng lineage/leakage, context/readiness,
  group statistics, semantic answer/citation, complete evidence và deployment observations;
  validator/manifest/production activation chặn khi thiếu hoặc sai raw evidence.
- Production giữ `RERANKER_ENABLED=false` khi còn thiếu gate. Experimental activation
  chỉ phục vụ đo trên identity đầy đủ. Provider lỗi giữ chính xác output Phase 6;
  abstention vì thiếu bằng chứng phải là quyết định policy đã calibration riêng.
- Không thay threshold để hợp thức hóa cấu hình fail, không tạo approval hoặc telemetry
  giả. Code tests, model studies và deployment evidence có vai trò khác nhau.

## 2. Đầu vào và các điểm chặn đã xác minh

Audit local: `.tmp/phase7-audit-readiness-20261002.json` và
`.tmp/phase7-audit-human-pool-20261002.json`. P7-01 lưu bản có thể theo dõi lâu dài;
file `.tmp` không phải release evidence bền vững.

**Cập nhật từ chủ dự án ngày 02/10/2026:** chủ dự án xác nhận các query trong candidate
pool do mình tự viết theo cách hỏi human-natural và đã kiểm chứng. Kế hoạch tiếp nhận
bộ hiện có, không yêu cầu viết lại toàn bộ. Đây là xác nhận tác giả/kiểm chứng của chủ
dự án; không tự suy ra danh tính reviewer độc lập hoặc timestamp chưa được cung cấp.

Candidate pool: 180 câu, 135 positive, 45 negative, 83 paraphrase groups; 159 gold
references đúng tọa độ frozen index. Những điểm chặn:

- 180 record thiếu `qid`, chưa chia split, timestamp nguồn không hợp lệ; review status
  và evidence source chưa khớp schema. 160 record có unsupported tags.
- 45 negative có scope rỗng, 95 record thiếu URL; 15 câu có context.
- 155 câu trùng nguyên văn bộ `student_natural_queries.jsonl`, nơi metadata đang ghi AI:
  89 ở split dev, 31 test, 35 holdout. Trùng nội dung không xác định chiều sao chép hay
  tác giả gốc. Đối chiếu lineage với xác nhận của chủ dự án và sửa metadata sai ở đúng
  dataset; riêng exposure/tuning history vẫn phải kiểm tra trước khi chọn held-out.
- Summary hash không khớp JSONL; `release_eligible=true` chưa được chứng minh.
- Studies chưa có cấu hình cùng đạt routing/recall/FPR/tải. Natural-dev recall từng
  giảm 70% → 28,33% với abstention; BGE cap 20 từng lỗi 98/100 ở concurrency 5,
  100/100 ở concurrency 20. Đây là số đo research, không phải final acceptance.
- Startup warm-up còn tùy chọn. Citation đúng coordinates chưa chứng minh hỗ trợ claim.

## 3. Data contract, split và freeze

1. Giữ raw question; history/selection lấy từ input đã ghi nhận. Không đưa normalized
   query, gold, qid, difficulty, expected answer/route vào inference features.
2. Project owner hoặc independent reviewer kiểm tra naturalness, answerability, đủ
   evidence, temporal scope, difficulty, leakage và expected behavior; khai báo role
   cùng identity thật. Owner self-review phải ghi riêng, không gọi là độc lập. Không
   điền source URL/timestamp/approval khi không có nguồn gốc kiểm chứng.
3. Ghi provenance theo nguồn gốc thực tế và xác nhận của tác giả; metadata cũ có thể
   cần sửa với correction record. Dữ liệu thực sự AI/generated/human-reviewed-AI giữ
   riêng. Không chia lại dữ liệu đã dùng nghiên cứu để tạo held-out mới, bất kể tác giả.
4. Split theo connected groups của intent/paraphrase/source-question/template. Hai record chung
   một family không bị tách chỉ vì giá trị các field khác nhau. Audit exact/near-duplicate
   giữa split và mọi benchmark/study đã dùng; ghi known-exposure registry.
   Chung PDF không tự động là cùng family; giữ document như stratum và ghi rationale
   grouping. Chốt group/split proposal và dev eligibility trước P7-09.
5. Target human primary benchmark: **240–300 câu**, gần 60/20/20 theo group. Minimum M1:
   150 total, 100 positive, 20 negative, 15 hard/multi-hop, 15 exact-code, 10 ambiguous;
   quotas overlap được. Mỗi split có positive/negative/easy/hard.
6. Dev folds phải có đủ ba lớp evidence: absence/incomplete/complete. Thu thêm intent
   đúng khi thiếu lớp; không thay nhãn chỉ để fitter chạy được.
7. Freeze canonical dataset bytes sau phân nhóm/chia split. Kiểm tra `--assign-splits`
   không hash file nguồn chưa chia split rồi xuất nội dung khác; dataset/splits/review/
   manifest phải cùng lineage. Freeze idempotent hoặc reject overwrite có thay đổi.
8. M4 khóa route trước held-out route; M6 khóa policy trước held-out quality. FAIL cũng
   tiêu thụ study. Không xóa lock để tune lại; thay route/model/policy sau held-out cần
   cycle/results directory và dữ liệu review mới phù hợp.
9. Chốt source/tests/dependencies/runtime/validator/rubric trước final evidence.
   Source/runtime/model thay đổi sau freeze cần đo lại phần bị invalidated; không chỉ
   thay hash trong report cũ. Giữ failed attempts và baseline Phase 6 nguyên vẹn.

## 4. Backlog trước final acceptance

### P7-01 — Baseline và evidence inventory (P0)

**Owner:** retrieval engineer + reviewer. **Phụ thuộc:** không có.

- Lưu audit versioned tại `docs/reranker/phase7_audit_20261002.md` và JSON audit riêng
  dưới `evaluation/results`; không đè gate artifacts M0.
- Inventory reports/index/calibration/corpus/model hashes, studies, dữ liệu đã xem,
  locks và kết quả partial M0. Bảo toàn historical RC3 và hai rerun độc lập.

**Đầu ra:** audit, inventory, partial readiness. **Nghiệm thu:** M0 PASS trên index vật lý;
evidence code/research/release được phân biệt; không thay baseline để tạo PASS.

### P7-02 — Candidate schema và summary (P0)

**Owner:** data engineer. **Phụ thuộc:** P7-01.

- Viết summary generator từ JSONL: counts/tags/groups/hashes/schema/evidence validity.
- Chuẩn hóa `qid`, supported tags, scope và version; challenge category giữ field riêng
  nếu không thuộc supported tags. Không làm mất raw data/provenance.
- Đối chiếu lineage của 155 câu trùng bộ mang nhãn AI với xác nhận tác giả; sửa metadata
  sai có correction record, không suy luận tác giả từ trùng câu. Missing fields giữ pending/unknown.
  Review status chỉ cập nhật từ review thật, không từ script conversion.

**Đầu ra:** builder/validator, candidate metadata, schema report.
**Nghiệm thu:** hash khớp JSONL, regeneration deterministic, tamper bị reject; summary
không tuyên bố release-ready khi schema/review/lineage còn thiếu.

### P7-03 — Tiếp nhận bộ human đã kiểm chứng và chuẩn bị freeze (P0)

**Owner:** chủ dự án/tác giả + data engineer; reviewer thực tế khi đối chiếu review.
**Phụ thuộc:** P7-01/P7-02. Đã nhận xác nhận tác giả và kiểm chứng từ chủ dự án.

- Dùng candidate pool hiện có làm đầu vào; giữ nguyên cách hỏi và ghi nhận xác nhận
  tác giả/kiểm chứng. Đối chiếu gold, scope và thông tin review đã có; chỉ bổ sung câu
  nếu thiếu quota/coverage hoặc cần held-out mới vì dữ liệu đã exposed/tuned.
- Nguồn là tác giả trực tiếp thì dùng provenance schema phù hợp, không bịa URL FAQ,
  timestamp thu thập hoặc yêu cầu nguồn web cho câu do người dùng tự viết.
- Review gold trên PDF/chunk: đủ answer, đúng version/program/scope, đủ các hop;
  negative cũng khai báo tài liệu được hỏi, ambiguous có expected clarification.
- Dùng question/review packets qua `human_benchmark_intake`, hoặc record với nguồn gốc
  thật đã được review; giữ record/index hashes, timestamps và audit sidecar.

**Đầu ra:** owner- or independent-reviewed packets, canonical dataset, evidence/review audit.
**Nghiệm thu:** quota M1 đủ, record/schema/gold/scope/review khớp; xác nhận kiểm chứng
đã nhận không bị bỏ qua. Owner self-review cần policy/packet khai báo rõ, đúng owner
identity và đủ bảy review checks; không tự tạo quyết định hoặc yêu cầu viết lại toàn
bộ vì metadata cũ.

### P7-04 — Validator, leakage và thống kê (P0)

**Owner:** evaluation engineer. **Phụ thuộc:** P7-01/P7-02; kiểm chứng bằng P7-03.

- Validate provenance chain/source/review/index; bind review audit và summary hashes;
  reject placeholder identity, changed record/context/index, incomplete approval.
- Leakage audit bao gồm AI natural, generated, previous studies/exposure registry;
  dùng connected-group splits/OOF và group bootstrap, báo số group độc lập.
- Sửa freeze/assign-splits/canonical hashes; test duplicates, leakage, scope/filter,
  thiếu strata, tampered review và nội dung split khác manifest.
- FPR có observed rate và CI95% theo independent negatives. Muốn claim upper bound
  one-sided 95% ≤1% khi 0 lỗi cần ≥299 negative độc lập (target stress set ≥300);
  two-sided 95% cần ≥368. Minimum 20 negative
  không đủ claim thống kê này. Không tăng sample bằng lặp lại cùng câu.

**Đầu ra:** validators/statistics/splitter, regression tests, exposure registry.
**Nghiệm thu:** dữ liệu hợp lệ pass; tamper/leakage fail closed; ngưỡng gate không bị hạ.

### P7-05 — Context, selection, scope và cache contract (P0)

**Owner:** RAG engineer. **Phụ thuộc:** P7-03 xác định contextual requirements.

- Bổ sung history/selected-text contract nếu hỗ trợ; resolution chỉ từ input cho phép,
  giữ raw/resolved query trong trace. Scope kiểm tra xuyên request/retrieval/citation.
- Cache key bind context/selection/scope; thiếu context cần thiết trả clarification.
- Nếu contextual ngoài scope MVP, chốt exclusion trước split/freeze và thu câu thay
  thế đủ quota; không loại câu fail sau khi chấm điểm.

**Đầu ra:** contract, adapters/harness và contextual/scope/cache tests.
**Nghiệm thu:** mỗi câu chấm điểm có input tương thích; không âm thầm bỏ context hoặc dùng gold.

### P7-06 — Live answer/citation acceptance (P0, gate bổ sung)

**Owner:** evaluation engineer + grounding reviewer. **Phụ thuộc:** P7-03/P7-05.

- Paired LLM harness Phase 6/7 cùng provider/model/prompt/context budget, caches tắt;
  lưu answer/claims/citations/abstention/latency/token usage.
- Freeze rubric accuracy, citation precision/recall, groundedness, abstention và đủ
  evidence từng hop. Independent review chấm semantic support; automated judge nếu
  dùng phải bind identity/prompt và được đối chiếu human-reviewed sample.
- Mục tiêu mới: **citation precision và groundedness ≥98%**, citation precision không
  giảm; answer accuracy và citation recall giảm tối đa **0,5 điểm %** so với Phase 6;
  answer FPR ≤1%. Báo paired/group CI
  và các subgroup. Không gọi answer grounded chỉ vì citation coordinates tồn tại.
  Khóa denominator/empty-answer/rubric; all-gold@5 và hard/multi-hop all-gold@5
  trên primary held-out không giảm, mọi claim multi-hop được trả phải đủ hop support.

**Đầu ra dự kiến:** `reranker_answer_quality.json`, raw answers/reviews, rubric hash.
**Nghiệm thu:** validator tính lại metric từ observations, FAIL khi không đạt; artifact
mới tham gia release binding. CLI/report này cần triển khai, chưa giả định đã tồn tại.

### P7-07 — Mandatory warm-up/readiness/lifecycle (P0)

**Owner:** runtime engineer. **Phụ thuộc:** không cần đợi human benchmark.

- Production warm thành công trước Phase 7 admission; flag mặc định false không được
  bỏ qua readiness. Startup timeout tách request timeout; warm fail giữ Phase 6.
- Test singleton loader một lần/process, request đầu không cold-load, concurrent
  startup, provider cleanup, shutdown/rollback và hủy queued work.

**Đầu ra:** runtime/readiness patch và tests. **Nghiệm thu:** không load trong callback;
failed startup không bật reranker hoặc làm hỏng Phase 6, không rò admission/resources.

### P7-08 — Trace và resource measurement (P1)

**Owner:** runtime/evaluation engineer. **Phụ thuộc:** P7-05/P7-07.

- Phân biệt route-selected/inference-attempted/completed/rerank-applied/fallback/abstain;
  định nghĩa `reranker_used` nhất quán. Ghi stages, request ID, model/policy/cap/limits.
- Đo RSS/VRAM/queue thật; successful throughput không tính circuit fast-fail.
  Timeout giữ permit cho đến khi native work kết thúc; không log secret/path tùy ý.

**Đầu ra:** trace/sampler và tests. **Nghiệm thu:** summaries tái tính từ raw samples;
timeout/error không che actual throughput, resource use hoặc thành công/thất bại.

### P7-09 — Dev feasibility trước held-out (P0)

**Owner:** retrieval/runtime engineer. **Phụ thuộc:** P7-03–08 đủ input/harness.

- Studies chỉ dev: input transforms, caps 8–20, precision, batch/window, route
  probability và evidence policy ba lớp. Mọi attempt/raw scores/hashes được giữ.
- Chẩn đoán false abstention, gold thiếu trong subset, exact-code, multi-hop và
  out-of-domain trước thay model. So sánh models trên cùng workload/quality contract.
- Shortlist một cấu hình đồng thời: hard-route recall ≥95%, easy rerank thừa ≤20%,
  positive hit Recall@5 ≥95%, FPR ≤1%, cap ≤20, hard p95 ≤1s, timeout ≤0,5%, errors =0;
  báo all-gold/evidence recall riêng, không coi query hit là đủ mọi hop.
- Tối ưu batching/queue theo successful throughput và latency; model nhanh nhưng
  chất lượng fail không được chọn. Candidate generation vẫn 40, rerank cap 40 chỉ research.

**Đầu ra:** dev comparison + configuration candidate. **Nghiệm thu:** joint feasibility
trên cùng cấu hình; chưa có thì tiếp tục dev/giữ Phase 6, không mở held-out để chọn.
Group/split proposal và dev eligibility phải được kiểm chứng trước studies. Chốt
protocol chọn cap/tie-break trước source freeze; cap sweep M5 không dùng lỗi theo qid
từ candidate/route held-out M2/M4 để điều chỉnh cấu hình.

## 5. Backlog acceptance sau freeze

Mỗi bước chỉ bắt đầu khi bước trước PASS. Thay code/runtime sau final freeze làm
affected evidence mất hiệu lực; áp dụng freeze rules khi phải mở cycle mới.

### P7-10 — Freeze source/runtime/data, M0/M1 (P0)

**Owner:** release engineer + data reviewer. **Phụ thuộc:** P7-01–09.

Review/chốt source/tests/evaluation/config/dependencies/contract/rubric/model/deployment
profile; commit source trước final measurement. Canonical dataset bytes có reviewed
groups/splits, gần 60/20/20; không tách group để đạt tỷ lệ đẹp. Revalidate M0 rồi freeze M1.

**Đầu ra:** source/runtime identity, baseline/review/manifest/splits.
**Nghiệm thu:** M0/M1 PASS, canonical/split content/hash cùng lineage, đầy đủ quota/strata.

### P7-11 — Coverage và model contract, M2/M3 (P0)

**Owner:** retrieval/runtime reviewer. **Phụ thuộc:** M1 PASS.

Đo coverage trước rerank, all-gold theo difficulty/category/tag và multi-hop/document/
table/year/semester/numeric/scoped. Pin offline snapshot/tokenizer/files/runtime/device/
dtype/batching/input format; smoke determinism và controlled provider contract.

**Đầu ra:** `candidate_coverage.json`, `model_snapshot_smoke.json`, provider contract.
**Nghiệm thu:** Recall@40 generated test ≥99%, holdout ≥97%, human splits ≥95%; stratified
coverage pass; scope/provenance/duplicate =0. Physical snapshot đúng hash, repeated score
delta ≤1e-5; singleton/warmup/queue/private scores/candidate preservation pass.

### P7-12 — Routing fit/freeze, M4 (P0)

**Owner:** routing reviewer. **Phụ thuộc:** M3 PASS.

Fit grouped OOF trên human dev theo allowlist; khóa route trước held-out route;
lưu raw samples/bypass/confusion/domain diagnostics và split hashes.

**Đầu ra:** route calibration/confusion/freeze.
**Nghiệm thu:** dev hard recall ≥95%, easy rerank thừa ≤20%; test/holdout ≥90% và ≤25%;
exact-code/abstention rerank rate =0, deterministic và không feature leakage. Fail dừng cycle.

### P7-13 — Evidence calibration và cap sweep, M5 (P0)

**Owner:** calibration reviewer. **Phụ thuộc:** M4 PASS.

Đo đủ 8/10/12/16/20 trên dev với identity M3/route M4; grouped OOF ba lớp; giữ baseline/
proposals/raw scores/refit/diagnostics/trials và fallback/timeout/invalid-score rates.
Legacy score threshold chỉ research; chọn cap bằng quality và latency cùng configuration.

**Đầu ra:** score calibration, cap sensitivity và five-cap raw artifacts.
**Nghiệm thu:** recall ≥95%, FPR ≤1%, invalid scores =0; selected cap p95 ≤1s,
timeout ≤0,5%, eligible requests >0; validator refit/recompute được, hashes khớp.

### P7-14 — Held-out ranking và answer, M6 + bổ sung (P0)

**Owner:** quality/grounding reviewer. **Phụ thuộc:** M5 PASS.

Freeze policy trước held-out quality. Paired generated test/holdout + human test/holdout;
báo all-gold/hard subgroup, win/tie/loss, ≥10.000 bootstrap resamples, group CI, regression
qids; chạy live answer/citation harness P7-06 cùng configuration.

**Đầu ra:** quality JSON/Markdown, regression JSONL, policy freeze, live answer report.
**Nghiệm thu hiện hành:** test MRR/nDCG@5 tăng ≥3% tương đối, Recall@5 không giảm,
cận dưới CI95% ΔMRR >0; holdout MRR/nDCG không giảm, Recall@5 giảm tối đa 0,5 điểm %.
Mọi split FPR ≤1%, scope/provenance/invalid citation/duplicates =0.
**Bổ sung:** P7-06 pass và group statistics hỗ trợ kết luận cải thiện trên test;
báo multi-hop completeness riêng và đạt S3–S5 trong task spec. Recall@k ranking hiện
là hit ít nhất một gold; không thay cho all-gold@k. Fail giữ conditional, không tune
lại trên held-out đó.

### P7-15 — Capacity và live HTTP, M7 (P0)

**Owner:** deployment/runtime reviewer. **Phụ thuộc:** M6 + answer gates PASS.

- Limits đo: timeout 1.000 ms, failure limit 3, score cache 0, queue chốt trước đo.
  Performance ≥100 requests, ≥30 hard và ≥30 hard rerank requests.
- Matrix (cap/concurrency): 8/1, 10/1, 20/1, 10/5, 10/20; CUDA thêm 20/5.
  Selected cap có profiles 1/5/10/20, ≥100 requests/profile.
- HTTP thật + LLM thật, caches tắt, ≥100 request mỗi concurrency 1/5/10/20;
  easy/hard/negative/scoped mỗi cohort ≥5, ≥30 LLM calls/grounded responses mỗi profile.
- Chốt HTTP p95 SLO trước đo: target mặc định 10s, validator ceiling 20s; không tăng
  SLO sau xem kết quả. Lưu cold/warm/stage/request timings và CPU/RSS/VRAM/queue.
- Khuyến nghị soak ≥30 phút, ≥1.000 requests/profile bổ sung cho p99/capacity stability.

**Đầu ra:** performance/capacity/resource budget/HTTP reports và raw samples.
**Nghiệm thu:** hard p50 ≤500ms, p95 ≤1s, p99 ≤2s; timeout ≤0,5%, timeout fallback ≤1%,
errors/queue-overflow failures =0; RSS ≤75% RAM. HTTP đạt SLO, no hidden LLM errors,
negative grounding FPR ≤1%, citation/scope/provenance đúng và resources thật.

### P7-16 — Security và grounding regression, M8 (P1)

**Owner:** security/grounding reviewer. **Phụ thuộc:** M7 PASS.

≥50 adversarial case, đủ 12 nhóm: out_of_corpus, similar_wrong_document,
conflicting_documents, exact_code_trap, year_mismatch, entity_mismatch,
chunk_prompt_injection, malformed_metadata, duplicate_chunks, scope_restriction,
empty_result, fake_citation. Attack thực sự chạy; audit against frozen evidence/Phase 6.
Chạy required grounding/adversarial/reranker integration tests, archive XML/hash.

**Đầu ra:** security/grounding reports, raw cases/XML.
**Nghiệm thu:** all cases pass, FPR ≤1%, scope/provenance/invalid citation =0;
required XML không error/failure/skip, có tests thực sự chạy.

### P7-17 — Controlled faults, M9 (P1)

**Owner:** runtime reviewer. **Phụ thuộc:** M8 PASS.

Inject missing/mismatched model/calibration, timeout, queue_full, OOM/exception,
non-finite/malformed score/output, wrong candidate/doc/page/rank, empty output,
cache/revision mismatch. Giữ observations; permanent fault đóng provider, tắt Phase 7
và follow-up không tăng inference; timeout/queue/circuit không rò permits.

**Đầu ra:** failure matrix + observations.
**Nghiệm thu:** required cases pass, fallback chính xác Phase 6, permanent fault
follow-up có zero new inference; không chỉ boolean tự khai.

### P7-18 — Rollback qua process/cache, M10 (P1)

**Owner:** operations reviewer. **Phụ thuộc:** M9 PASS.

Rollback/restart qua hai PID riêng với shared cache đã có reranked answers; đóng
admission/hủy queued work/đổi namespace và kiểm tra Phase 6 outputs/index.

**Đầu ra:** rollback report/raw probes/timings.
**Nghiệm thu:** ≤300s, new inference =0, Phase 6 đúng cả hai process; không reuse
reranked cache, không rebuild index, model/provider resources đóng theo contract.

### P7-19 — Staging canary, M11 (P0)

**Owner:** staging/deployment owner. **Phụ thuộc:** M0–M10 + bổ sung PASS.

- 0→1→5→10→25%, mỗi bước ba healthy windows, ≥100 request/window: tối thiểu
  15 windows/1.500 requests chưa tính faults. Final 25% cũng phải đạt budget.
- Raw telemetry có environment/runtime bindings, request IDs/cohorts/scope/outputs,
  timezone-aware timestamps, latency/errors/FPR/fallback/selection/hard coverage/
  easy rerank thừa, RSS/RAM, queue, scope/provenance/citation errors.
- Đủ tám trigger rollback: provenance, scope, citation, timeout, FPR, error regression,
  memory và latency vi phạm ba windows; follow-up kiểm tra provider đóng/zero new calls.

**Đầu ra:** staging/canary reports + raw healthy/fault telemetry.
**Nghiệm thu:** p95 ≤1s/p99 ≤2s, hard coverage ≥90%/easy rerank thừa ≤25% khi có Phase 7;
FPR/timeout ≤1%, không error regression, RSS ≤75% RAM, scope/citation/provenance =0;
tất cả rollback exercises pass, summaries được auditor tính lại.

### P7-20 — Release bundle và M12 (P0)

**Owner:** release owner. **Phụ thuộc:** toàn bộ task trước.

- Archive/commit dataset, evidence, sidecars, XML, bổ sung metrics, review packets và
  runtime/model/index manifests; raw `.release` files được archive lâu dài riêng.
- Đồng bộ `plan.md`, progress/runbook/README/summary với evidence mới. Không giữ số
  tests audit cũ như verification của source đã đổi; không commit tự động trong task lập plan.
- Full suite/coverage ≥85%, compile, secret scan, diff/links và hai live-LLM tests với
  credentials environment thật. Không lưu API key vào repo.
- Sau source/evidence commit và clean tree, M12 + physical model check + manifest;
  readiness/final manifest không đè gate evidence hoặc làm working tree dirty.

**Nghiệm thu:** M0–M12 PASS, score=10.0, all_release_gates_pass=true; gate bổ sung cùng
pass, bindings đúng, bundle tái kiểm chứng được từ clean checkout.

## 6. Deployment, mốc thực hiện và failure handling

Deployment owner chốt environment/limits trước freeze. Local RTX 4060 evidence chỉ
nghiệm thu runtime local tương ứng; khác public runtime phải có measurements/bindings
M3–M11 riêng. Theo [GPU deployment decision](../operations/gpu_hosting.md), giữ yêu cầu
GPU thuê bằng 0; không tự chuyển paid hardware để đạt gate. Kiểm tra official docs/quota
ở thời điểm triển khai; kế hoạch này không xác nhận lại các quota hosting.
Public allocation/queue latency phải tính vào trải nghiệm người dùng. Free target
không đạt budget giữ demo/conditional + Phase 6; local score 10 không approve public target.

Ước lượng là ngày làm việc của nhóm, có thể overlap, không phải deadline hay bảo đảm
đạt quality trong một vòng nghiên cứu. Thời gian review/hạ tầng phụ thuộc đầu vào thật.

| Mốc | Tasks | Ước lượng | Điều kiện chuyển mốc |
|---|---|---|---|
| A — Dữ liệu đáng tin | P7-01–04 | 3–6 ngày kỹ thuật; author/review bổ sung chỉ khi còn thiếu | Schema/provenance/groups đúng, quota đủ |
| B — Code và dev feasibility | P7-05–09 | 6–12 ngày kỹ thuật, có thể cùng A | Contract/readiness/harness đủ, joint dev feasibility |
| C — Freeze/ranking | P7-10–14 | 3–6 ngày đo/review | M0–M6 + answer/statistics gates PASS |
| D — Capacity/reliability | P7-15–18 | 3–5 ngày đo/review | M7–M10 PASS đúng profile |
| E — Staging/package | P7-19–20 | 2–4 ngày, phụ thuộc quota/environment | M11/M12 và bổ sung PASS |

Việc đầu tiên: **P7-01/P7-02/P7-07**, đồng thời chuẩn hóa bộ đã nhận trong P7-03.
Không cần viết lại bộ human hoặc chờ review lại toàn bộ để sửa summary/warm-up;
thông tin reviewer/approval còn thiếu được đối chiếu riêng với review thực tế.

| Khi fail | Hành động | Evidence phải giữ |
|---|---|---|
| Thiếu human data/review | Làm code/dev độc lập, giữ M1 blocked | Pending packets và thiếu quota/fields |
| Thiếu ba lớp dev folds | Thu/review thêm intent đúng, kiểm tra grouping | Class/group counts và fitter error |
| Candidate recall fail | Sửa retrieval/index/scope trên dev | Missing gold và affected strata |
| Route/calibration infeasible | Chẩn đoán dev; cycle mới nếu held-out đã mở | Attempts/locks/input hashes |
| Held-out quality fail | Không tune trên split đó; cycle/data độc lập mới | Regressions/raw outputs/group CI |
| Capacity fail | Tối ưu dev hoặc model candidate khác, đo lại identity | Successful throughput/errors/RSS/VRAM |
| Contextual fail | Sửa contract trước freeze, không bỏ history ngầm | Raw context/resolution trace |
| Staging quota/lease fail | Giữ demo/Phase 6, không mua GPU hoặc hạ gate tự động | Allocation/queue/fault telemetry |
| Source/runtime/hash đổi | Invalidate affected gates, đo lại theo freeze rules | Old/new identity và rerun rationale |

## 7. Checklist đóng phase

- [ ] P7-01–20 có owner, trạng thái và evidence path trong roadmap.
- [ ] Human provenance/review/scope/evidence/splits đầy đủ; không AI relabel/leakage.
- [ ] Context/cache, readiness, singleton và trace có tests phù hợp.
- [ ] Joint routing/evidence/latency configuration khả thi trên dev.
- [ ] Held-out ranking/group statistics/live answer/citation đạt mục tiêu freeze.
- [ ] Capacity/HTTP/security/fault/rollback/staging pass trên runtime mục tiêu.
- [ ] Failed attempts/locks giữ nguyên; không overwrite hoặc hạ threshold tạo PASS.
- [ ] Code/coverage/compile/secret scan/diff/live-LLM checks đã xác minh.
- [ ] Clean checkout tái kiểm chứng M0–M12 + bổ sung; bundle/manifest được archive.
- [ ] `plan.md`, progress/runbook/summary khớp evidence, score release 10.0.
- [ ] [Task spec](phase7_task_spec.md) có checklist/owner/artifacts/DoD của từng task;
  S1–S6 được validator/manifest kiểm tra, không chỉ ghi mục tiêu trong tài liệu.

## 8. Lệnh và quy trình hiện có

The authority is `python -m evaluation.reranker.validate_reranker_release --through M12`.
Only `status=pass`, `score=10.0`, and all M0–M12 `PASS` permit release.
The source baseline is preserved. A passing unit test is code evidence;
model benchmarks are evaluation evidence; staging observations are deployment
evidence. They are not interchangeable.

Canonical documents are the [root roadmap](../../plan.md), this detailed plan,
[the runbook](reranker_release_runbook.md),
[human benchmark guidance](../benchmarks/human_benchmark_sources.md), and
[current evidence status](reranker_progress.md). Existing names remain stable.

### Workflow

Run commands from the repository root. `python` below means the project
virtualenv interpreter (`.venv/Scripts/python.exe` on Windows).

| Command | Required external input | Gate |
|---|---|---|
| `python -m evaluation.reranker.release_workflow baseline` | Existing frozen Phase 6 artifacts/index | M0 |
| `python -m evaluation.reranker.release_workflow human-freeze` | Reviewed `data/benchmark/human_retrieval.jsonl` | M1 |
| `python -m evaluation.reranker.release_workflow candidate` | Frozen human splits | M2 |
| `python -m evaluation.reranker.release_workflow model --model-dir SNAPSHOT` | Offline model directory named by immutable commit | M3 |
| `python -m evaluation.reranker.release_workflow route` | Human dev with difficulty review and grouped route calibration | M4 |
| `python -m evaluation.reranker.release_workflow calibration --model-dir SNAPSHOT` | Dev-only cap sweep | M5 |
| `python -m evaluation.reranker.release_workflow quality --model-dir SNAPSHOT` | Held-out paired observations | M6 |
| `python -m evaluation.reranker.release_workflow performance --model-dir SNAPSHOT --deployment-ram-bytes LIMIT --llm-config CONFIG` | Real RAM limit and configured live LLM | M7 |
| `python -m evaluation.reranker.release_workflow security --model-dir SNAPSHOT --cases CASES` | >=50 adversarial cases covering all 12 categories | M8 |
| `python -m evaluation.reranker.release_workflow faults` | Controlled runtime injection | M9 |
| `python -m evaluation.reranker.release_workflow rollback --model-dir SNAPSHOT` | Live model and shared cache probes | M10 |
| `python -m evaluation.reranker.release_workflow staging --observations WINDOWS --fault-observations FAULTS` | Actual staging telemetry | M11 |
| `python -m evaluation.reranker.release_workflow staging-collect --model-dir SNAPSHOT` | Frozen M0-M10 evidence; local measured deployment | Collect and audit M11 |
| `python -m evaluation.reranker.release_workflow validate` | All artifacts; clean source tree | M12 |
| `python -m evaluation.reranker.release_workflow release --model-dir SNAPSHOT` | Recomputed physical model snapshot | Final manifest |

Each command has an equivalent `make reranker-STAGE RERANKER_ARGS="..."`.
The workflow configures experimental measurement activation from the M3
identity; provide `--device` and `--model-name` if they differ from the CPU/BGE
defaults. It never enables production automatically.

Use `--results-dir`, `--index-dir`, and `--benchmark-dir` for isolated studies.
The standard evidence directory is `evaluation/results`; official artifacts,
cap trials, and grounding XML reports stay there. Readiness output goes to
`.release/reranker/readiness.json` so validation does not dirty the tree.
The generated final manifest at `evaluation/results/reranker_release_manifest.json`
is ignored; archive it with the committed evidence. Never use it to substitute
for measured reports.

### Freeze and rerun rules

M4 writes `reranker_route_freeze.json` **before** opening held-out route data.
M6 writes `reranker_policy_freeze.json` **before** opening held-out quality data.
A failed run also consumes the study. Fitting tools reject another fit after
the applicable lock; identical quality reruns may reuse the lock, but changed
model, route, calibration, benchmark or cap evidence is rejected. Never remove
locks to tune on held-out results. A failed study requires a new research cycle
with fresh reviewed data and its own results directory.

Reports M3 onward bind source/runtime/index/Phase 6 calibration/model identity.
Reports after calibration also bind route calibration, training split, and
human benchmark. The source digest includes tests and build/dependency files.
Any source change requires affected measurements to be rerun on the release
source. Finish code review and commit source before collecting final evidence.

### External evidence still required

The repository has a 180-record candidate pool, but no valid per-record approved
release dataset/frozen splits or complete release staging telemetry. The current
owner-review dossier and process policy are at
`docs/benchmarks/phase7_review_cycles/phase7-release-20261003-r3/`; all decisions
remain pending. Owner self-review is allowed for this personal project when the
packet declares `project_owner`, matches the configured identity, binds exact
evidence and passes all checks. Human authorship, per-record decisions and exposure
history cannot be created by evaluation scripts.

Staging needs 0/1/5/10/25% in order, three healthy windows at **each** step,
100 requests per window, complete metrics, and all eight rollback exercises.
Every window must meet the budgets; the final step is checked too. Both p95
and p99 violations count toward the three-window latency rollback trigger.

`staging-collect` starts an isolated local service process, runs the real model,
collects three windows at all five steps, executes all eight controlled rollback
exercises, and audits the resulting telemetry. It requires M0-M10 first. The
default outputs are `.release/reranker/staging_observations.json` and
`.release/reranker/staging_fault_observations.json`; use new paths for a new run.
`--staging-requests` defaults to 100 and `--staging-concurrency` to 1. Every
workload cycle retains reviewed easy, hard and negative cohorts. Scope exercises
also need restricted-scope rows from all three cohorts.

The collector retains request IDs, evaluator labels, scope, outputs, measured
latency, and process RSS/queue gauges sampled every 10 ms. The auditor recomputes
window summaries and checks output provenance against the frozen index; scalar
summaries cannot substitute for raw observations. Faults resume the measured
25% configuration, inject at named service/model boundaries, and verify provider
closure plus unchanged Phase 6 outputs and zero new inference in follow-up
requests. The memory exercise lowers the configured alert budget while retaining
the actual measured RSS. The latency exercise executes three slow windows and
therefore takes at least five minutes at the default sequential load.

`python -m evaluation.reranker.diagnose_reranker_cpu --model-dir SNAPSHOT --device cpu`
probes real chunks from three hard dev questions at caps 8/10/20. Use
`--device cuda:0` for a separately installed GPU runtime. This is exploratory
diagnostic data, always `release_eligible=false`; it never satisfies M7 or reads
test/holdout. Measurement activation runs Hugging Face/Transformers offline.

For a Windows host with an NVIDIA GPU, `powershell -File scripts/dev/setup_reranker_gpu.ps1`
creates a separate `.tmp/reranker-gpu-runtime`. It installs the pinned PyTorch CUDA
wheel from [the official PyTorch repository](https://download.pytorch.org/whl/cu126/torch/)
and shares existing project dependencies without replacing the CPU `.venv`.
Run GPU commands with `.tmp/reranker-gpu-runtime/Scripts/python.exe` and
`--device cuda:0`; model smoke/calibration and later measurements must use that
same runtime. Device/runtime changes invalidate their earlier evidence bindings.

The future public website must have zero GPU rental cost. Its selected target
and quota/lease constraints are recorded in [the free GPU deployment decision](../operations/gpu_hosting.md).

Commit the actual dataset and evaluation evidence after measurement. Only
after that clean checkout passes M12 should the manifest be generated and
`RERANKER_DEPLOYMENT=production` be configured.
