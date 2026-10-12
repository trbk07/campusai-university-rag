# Phase 7 — Đặc tả thực thi và chuẩn bàn giao từng task

> **Phạm vi hiện hành 08/10/2026:** owner đã thay Phase 7 bằng sáu hạng mục chất lượng sản phẩm C7-01–C7-06 trong [plan.md](../../plan.md#phase-7--hoàn-thiện-chất-lượng-sản-phẩm-phạm-vi-tinh-gọn). Optional reranker giữ tắt; các task/19 gate trong tài liệu này là hợp đồng qualification được hoãn, vẫn phải đạt trước khi bật reranker production. Không dùng các checkpoint cũ bên dưới làm mục tiêu 20/20–19/19 hiện hành. Trạng thái mới nằm ở `active_tasks` của [ledger](../../evaluation/results/phase7-completion-20261004/completion_task_ledger.json).

Ngày cập nhật: **02/10/2026**, Asia/Bangkok. Đây là **kế hoạch thực hiện**, không phải
báo cáo PASS. Roadmap gốc: [`plan.md`](../../plan.md#phase-7--reranker).
Phạm vi, ngưỡng gate hiện hành và CLI: [release plan](release_plan.md) và
[runbook](reranker_release_runbook.md). Trạng thái thực đo:
[reranker_progress.md](reranker_progress.md).

## 1. Kết quả phải đạt để gọi Phase 7 là 10/10

Phase 7 bàn giao một reranker tùy chọn, giúp truy vấn khó tìm đúng và đủ bằng chứng,
tạo câu trả lời có citation được kiểm chứng, chạy trong ngân sách runtime mục tiêu,
và quay về Phase 6 khi lỗi. Candidate generation tối đa **40**; rerank subset thuộc
**8/10/12/16/20**. Query easy/exact-code và request không đủ điều kiện không gọi model.

**10/10 là kết quả nghiệm thu**, không phải tổng điểm tự chấm các task. Phải đồng thời:

- M0–M12 PASS, validator trả `status=pass`, `score=10.0`,
  `all_release_gates_pass=true`, đúng hashes và clean checkout.
- Các chuẩn bổ sung ở mục 3 được triển khai thành kiểm tra bắt buộc và đưa vào
  release manifest; không chỉ viết mục tiêu trong Markdown.
- Report chứng minh đúng dataset, source, model, runtime và deployment được bàn giao.
  Evidence local không nghiệm thu thay public runtime có phần cứng khác.
- Handoff có raw observations, script tái tính metric, runbook và rollback đã thực đo.

Giữ production disabled đến khi đủ điều kiện. Các task P1 vẫn bắt buộc để đóng phase;
P0/P1 biểu thị thứ tự ưu tiên triển khai, không cho phép bỏ gate.

## 2. Quy ước thực thi chung

### 2.1. Trạng thái, owner và Definition of Done

Mỗi task đi qua `TODO → IN_PROGRESS → REVIEW → DONE`; dùng `BLOCKED` kèm lý do,
đầu vào cần bổ sung và người phụ trách. Owner trong tài liệu là **vai trò dự kiến**;
người thực hiện ghi tên thực tế khi nhận task. Người viết code có thể kiêm nhiều vai trò.
Benchmark review phải khai báo một người review thực tế: `project_owner` theo policy
owner self-review hoặc `independent_reviewer` khác tác giả. Owner review không được
gọi là review độc lập.

Task chỉ DONE khi có đủ: checklist hoàn tất, artifacts tồn tại, kiểm tra đạt chuẩn,
evidence binding hợp lệ và review đã ghi nhận. `Đã có script` không đồng nghĩa `đã có
evidence PASS`. `Không đo được`, denominator bằng 0 hoặc missing subgroup là thiếu
evidence; không tự chuyển thành PASS.

Template cập nhật task trong roadmap/progress:

```text
Task: P7-xx | Owner: <người thực hiện> | Status: <trạng thái>
Inputs: <dataset/source/runtime/model/index identities>
Outputs: <đường dẫn artifacts và SHA-256>
Validation: <lệnh, thời điểm có timezone, exit code, kết quả gate>
Review: <người review, nhận xét, lỗi còn mở>
Next: <task được mở hoặc nguyên nhân blocked>
```

### 2.2. Chuẩn artifact

Đường dẫn report M0–M11 bên dưới là tên **hiện có** trong validator. Đường dẫn cho
summary builder, audit, rubric, answer quality, task ledger và supplemental reports
là **đề xuất cần tạo**; không mặc định repo đã có CLI/schema tương ứng.

Mọi report mới phải có version, task/cycle ID, status, lý do fail, thời điểm có timezone,
command/config/seed, input hashes, observations hoặc đường dẫn raw + hash, metric
definitions, sample/group counts và người review thực tế khi cần. JSON không chứa
NaN/Infinity; đơn vị thời gian ms, memory bytes; tỷ lệ dạng 0–1 và ghi denominator.

Artifacts mô hình/quality/runtime bind `source_sha256`, `runtime_sha256`, index vật lý,
Phase 6 calibration, model/tokenizer revision và files digest. Sau M4 thêm route;
sau M5 thêm evidence calibration, cap, benchmark/dev split và policy identity.
Identity LLM/prompt/context budget/rubric/review cũng bind vào answer report.
Artifact không có model/LLM thì đánh dấu không áp dụng, không điền identity giả.

Raw lớn có thể lưu ngoài Git, nhưng phải có archive bền vững, checksum và hướng dẫn
restore. `.tmp`/`.release` chỉ là nơi chạy, không là kho lưu duy nhất. Report tham chiếu
relative path an toàn; validator reject path traversal, missing raw hoặc changed raw.

### 2.3. Freeze và bảo vệ held-out

| Điểm freeze | Khóa gì | Sau đó được làm gì |
|---|---|---|
| F0 — trước P7-09 | Group/split proposal, exposure registry, dev eligibility | Dùng phần dev hợp lệ để nghiên cứu; không mở held-out để chọn cấu hình |
| F1 — P7-10 | Source/tests/validator, rubric, model/runtime profile, dataset bytes/splits, protocol chọn cap | Chạy acceptance tuần tự; không sửa implementation rồi dùng report cũ |
| F2 — P7-12 | Route fitted trên dev, lock trước route test/holdout | P7-13 chạy dev cap sweep theo protocol đã chốt; không dùng lỗi route held-out để đổi policy |
| F3 — P7-14 | Cap/evidence/answer policy, toàn bộ bindings, lock trước quality held-out | Đo quality/load/security/staging của đúng cấu hình đã khóa |

P7-09 cần group assignment trước khi chọn dev; P7-10 mới freeze dataset chính thức.
M2/M4 có đọc held-out cho nghiệm thu riêng: ghi vào exposure registry, chỉ dùng để
PASS/FAIL gate. Người fit M5 không dùng kết quả theo qid của held-out để chọn cap,
transform, model hoặc threshold. CLI và access protocol cần bảo đảm điều này.

FAIL cũng tiêu thụ study. Rerun cùng identity để xác minh lỗi hạ tầng được giữ lịch sử;
thay cấu hình sau held-out phải mở cycle mới với phần held-out độc lập phù hợp.
Không xóa freeze lock, chia lại câu đã tune hay thay hash vào report cũ.

## 3. Chuẩn đo và bảng ngưỡng nghiệm thu

### 3.1. Định nghĩa cần khóa trước khi đo

- `Recall@k` trong harness ranking hiện tại là **query hit rate**: tỷ lệ positive có
  ít nhất một gold trong top k. Giữ tên compatibility và ghi rõ định nghĩa.
- `all_gold_recall@k`: tỷ lệ positive có đủ mọi gold chunk bắt buộc trong top k.
  `evidence_recall@k`: tổng gold chunk tìm được / tổng gold chunk. Báo cả ba metric.
  Nếu có nhiều evidence set thay thế hợp lệ, phải khai báo/review trước freeze và
  dùng cùng quy tắc cho Phase 6/7; không thay gold sau khi xem output.
- MRR/nDCG chấm trên positive; negatives chấm riêng. Báo overall/hard/multi-hop/
  exact-code/contextual/table/temporal/scoped và số query/group từng nhóm.
- Relative improvement = `(Phase7 − Phase6) / Phase6`; 0,60 → 0,618 là **+3% tương đối**.
  Drop 0,005 là **0,5 điểm %**. Baseline bằng 0 cần quy tắc chấm đã khóa, không chia 0.
- Routing hard recall = hard được route hard / hard đủ điều kiện; easy unnecessary
  rate = easy bị route hard / easy đủ điều kiện. Báo bypass và denominator riêng.
- Retrieval FPR = negatives trả evidence / negatives; answer FPR = negatives nhận
  câu trả lời khẳng định thiếu căn cứ / negatives. Báo riêng provider fallback,
  insufficient-evidence abstention và clarification; không dùng chúng thay thế nhau.
  Abstention precision = negative bị abstain / mọi abstained queries; abstention
  recall = negative bị abstain / mọi negatives. Clarification có label riêng;
  positive bị abstain vẫn tính false abstention, không loại khỏi accuracy denominator.
- Answer accuracy: tỷ lệ positive đáp ứng đủ rubric của câu; abstention sai tính sai.
  Citation precision: cặp claim–citation được evidence hỗ trợ / mọi cặp được phát ra.
  Citation recall: claim cần citation có citation hỗ trợ / mọi claim cần citation.
  Groundedness: claim factual được context hỗ trợ / mọi claim factual phát ra.
  Đồng thời báo độ bao phủ gold claims để tránh câu trả lời rỗng được điểm đẹp.
- CI/paired bootstrap sampling theo connected groups, ≥10.000 resamples, seed cố định.
  Báo cả query count và independent group count; các lần lặp load không tăng cỡ mẫu
  chất lượng. Khi insufficient power, ghi rõ và giữ conditional theo gate liên quan.
- p50/p95/p99 phải ghi endpoint đo: rerank inference, queue + rerank, retrieval service,
  hoặc HTTP end-to-end gồm LLM. Ghi success và all-attempt distributions cùng counts;
  throughput = successful completed requests / thời gian chạy, không tính fast-fail.

### 3.2. Gate hiện có và chuẩn bổ sung

| Gate | Chuẩn đầu ra bắt buộc | Task |
|---|---|---|
| M0 | Frozen Phase 6 artifacts và index vật lý hợp lệ, historical baseline giữ nguyên | 01, 10 |
| M1 | ≥150 câu; ≥100 positive, ≥20 negative, ≥15 hard/multi-hop, ≥15 exact-code, ≥10 ambiguous; review/scope/evidence/splits hợp lệ | 02–04, 10 |
| M2 | Candidate/all-gold coverage theo overall và strata: generated test ≥99%, holdout ≥97%; human dev/test/holdout ≥95%; không lỗi scope/provenance/duplicate | 11 |
| M3 | Offline model/tokenizer/runtime đúng hash; repeated score delta ≤1e-5; provider contract PASS | 07–08, 11 |
| M4 | Hard route recall dev ≥95%, held-out ≥90%; easy rerank thừa dev ≤20%, held-out ≤25%; exact-code/abstention rerank =0 | 12 |
| M5 | Dev positive hit Recall@5 ≥95%, FPR ≤1%, invalid score =0; đủ năm cap; cap chọn p95 ≤1s, timeout ≤0,5%, eligible requests >0 | 13 |
| M6 | Generated/human test: MRR và nDCG@5 cùng tăng ≥3% tương đối, Recall@5 không giảm, CI95% ΔMRR lower >0; holdout MRR/nDCG không giảm, Recall@5 drop ≤0,5 điểm %; FPR ≤1%, violations =0 | 14 |
| M7 | Hard p50 ≤500ms, p95 ≤1s, p99 ≤2s; timeout ≤0,5%, timeout fallback ≤1%, error/queue-overflow failures =0; RSS ≤75% RAM; đủ capacity/HTTP profiles và live LLM | 15 |
| M8 | ≥50 adversarial cases đủ 12 nhóm, tất cả PASS; FPR ≤1%, provenance/scope/invalid citation =0; required grounding tests không skip/fail | 16 |
| M9 | Required faults PASS, fallback đúng Phase 6; permanent failure đóng provider và không gọi inference mới | 17 |
| M10 | Rollback ≤300s qua hai process/cache; zero new inference, Phase 6 outputs đúng, không rebuild index | 18 |
| M11 | 0/1/5/10/25%, ba healthy windows/bước, ≥100 requests/window; đủ tám rollback exercises; telemetry tái tính được và đạt budget | 19 |
| M12 | Full suite/coverage ≥85%, checks + physical bindings/clean tree/archive hợp lệ; M0–M12 PASS, score 10.0 | 20 |

Các chuẩn sau là **bổ sung của kế hoạch 10/10**. P7-04/P7-06/P7-08 phải thêm vào
validator/manifest trước F1; validator hiện tại chưa chứng minh toàn bộ bảng này.

| Chuẩn bổ sung | Ngưỡng / invariant đề xuất phải khóa trước F1 | Task |
|---|---|---|
| S1 — Dữ liệu và lineage | Không thiếu/giả review; leakage/exposure unresolved =0 cho held-out; summary/canonical/splits/review/raw hashes cùng lineage | 02–04 |
| S2 — Context và lifecycle | Context/scope/cache đúng; không load model trong request; warm fail giữ Phase 6; không rò permits/resources | 05, 07 |
| S3 — Thống kê | Group bootstrap tái tính được; human test CI95% ΔMRR lower >0; cohort nhỏ báo insufficient evidence, không tự PASS | 04, 14 |
| S4 — Answer/citation | Từng primary held-out split: citation precision ≥98%, groundedness ≥98%; precision không thấp hơn Phase 6; accuracy và citation recall drop ≤0,5 điểm %; answer FPR ≤1% | 06, 14 |
| S5 — Evidence đầy đủ | All-gold@5 và hard/multi-hop all-gold@5 trên primary held-out không giảm so với Phase 6; mọi claim multi-hop được trả phải có đủ hop support | 06, 14 |
| S6 — Quan sát và deployment | Stages/resources/throughput có raw thật; target identity đúng; HTTP p95 budget khóa trước đo, mặc định 10s và không vượt ceiling validator 20s | 08, 15, 19 |

Target primary human benchmark **240–300** câu để tăng coverage; **180 câu hiện có
được tiếp nhận**, không buộc viết lại hay bổ sung chỉ để đạt target đẹp. Minimum M1
vẫn là 150. Chỉ thu thêm khi thiếu independent held-out, quota, folds hoặc lực thống kê.
Strata có thể overlap; tỷ lệ 60/20/20 là định hướng, không tách group để ép tỷ lệ.
Không ép mỗi intent khác nhau trên cùng PDF thành một group; chung tài liệu chỉ là
stratum. Group chỉ gom family thực sự phụ thuộc: paraphrase/intent/template/source
question hoặc evidence pattern có khả năng leakage, kèm rationale có thể kiểm tra.

FPR ≤1% quan sát không chứng minh FPR quần thể ≤1%. Muốn upper bound **one-sided
95%** ≤1% khi 0 lỗi cần ≥299 negative **độc lập** (`1 − 0,05^(1/n)`); nếu dùng
two-sided 95% cần ≥368. Có thể đặt stress set riêng ≥300 cho one-sided protocol,
không trộn vào primary ranking hay nhân mẫu bằng cách lặp câu.

## 4. P7-01–P7-09 — Chuẩn bị dữ liệu, code và cấu hình khả thi

<a id="p7-01"></a>

### P7-01 — Audit và bảo toàn baseline

**Owner:** retrieval/release engineer. **Ưu tiên:** P0. **Phụ thuộc:** không.
**Ước lượng:** 0,5–1 ngày kỹ thuật.

**Đầu vào:** `plan.md`, progress, gate validator, Phase 6 manifests/index, studies/locks.

- [ ] P7-01.1 Snapshot Git status, baseline source/runtime, artifacts, index files và các cycle đã chạy; phân loại code/research/release evidence.
- [ ] P7-01.2 Kiểm tra M0 trên index vật lý; giữ historical RC3 và hai rerun, không tạo baseline mới để làm đẹp số.
- [ ] P7-01.3 Lập exposure registry: dataset/split/group đã xem hoặc tune, tool/cycle, purpose, thời điểm và mức độ xác định.
- [ ] P7-01.4 Archive audit `.tmp` còn tồn tại; dữ kiện chỉ có trong báo cáo cũ ghi historical/unverified, không coi là vừa đo lại.
- [ ] P7-01.5 Tạo ledger 20 tasks và issue list theo blocker/code/data/runtime; chỉ định owner thực tế khi nhận việc.

**Bàn giao:** đề xuất `docs/reranker/phase7_audit_20261002.md`,
`evaluation/results/phase7_evidence_inventory.json`,
`data/benchmark/phase7_exposure_registry.json`; audit raw + checksums.
**Nghiệm thu:** inventory truy ra được từng artifact; M0 PASS hoặc blocker cụ thể;
baseline bytes không đổi. Chạy `release_workflow baseline` và archive output.
**Khi fail:** phục hồi/đối chiếu missing index từ manifest; dữ liệu không rõ exposure
không được dùng làm held-out mới. Mở P7-02/P7-07 độc lập nếu đầu vào đủ.

<a id="p7-02"></a>

### P7-02 — Chuẩn hóa candidate/schema/summary

**Owner:** data engineer. **Ưu tiên:** P0. **Phụ thuộc:** P7-01. **Ước lượng:** 1–2 ngày.

**Đầu vào:** candidate JSONL/summary, record example, intake/freezer/schema, corpus manifest.

- [ ] P7-02.1 Bảo toàn raw candidate bytes; tạo mapping `candidate_id/source_record_id → qid` ổn định, không đổi ID khi sort/filter.
- [ ] P7-02.2 Chốt schema phân biệt nguồn câu hỏi do tác giả viết trực tiếp với nguồn PDF của evidence; direct author không bắt buộc URL FAQ không tồn tại.
- [ ] P7-02.3 Mapping tags/category/evidence source có schema version; giữ raw tags và correction log. Không chuyển `independently_reviewed → approved` khi chưa có review audit tương ứng.
- [ ] P7-02.4 Đối chiếu identity/review/scope/context/evidence. Generic reviewer label cần audit danh tính thực tế; không tự invent reviewer/timestamp.
- [ ] P7-02.5 Tạo summary generator từ JSONL: actual hash, counts, groups, strata, missing fields, review readiness, release eligibility theo validation.
- [ ] P7-02.6 Sửa `configs/human_benchmark_record.example.json` theo contract mới, vẫn pending; validate freeze và intake dùng cùng schema.

**Vị trí:** `evaluation/benchmarks/{human_benchmark_intake,freeze_human_benchmark}.py`,
schema liên quan; builder summary mới dưới `scripts/benchmarks/`.
**Bàn giao:** canonical candidate staging, qid mapping/correction log,
`human_candidate_pool.summary.json` tái sinh, schema report/version/example cập nhật.
**Nghiệm thu:** 180 raw câu không bị rewrite ngầm; hash khớp bytes, regen deterministic;
summary reject changed raw; direct-authored valid/pending/missing reviewer phân biệt đúng.
**Khi fail:** giữ pending từng field/câu, output reason codes; summary không tự nhận release-ready.

<a id="p7-03"></a>

### P7-03 — Review dữ liệu và chốt group/split proposal

**Owner:** chủ dự án + data engineer. **Ưu tiên:** P0.
**Phụ thuộc:** P7-01/P7-02. **Ước lượng:** 1–3 ngày kỹ thuật; review tùy đầu vào.

- [ ] P7-03.1 Tiếp nhận xác nhận của chủ dự án đã ghi trong roadmap; dùng câu hiện có, đối chiếu review records thay vì yêu cầu viết lại.
- [ ] P7-03.2 Check từng positive trên PDF/index: exact doc/chunk/page/source hash, đúng program/version/filter; table giữ row/header/unit và đủ mọi hop.
- [ ] P7-03.3 Negative cũng phải có explicit document scope; ghi no-evidence/ambiguous/conflict/clarification expected behavior trong scope đó.
- [ ] P7-03.4 Review 15 contextual inputs cùng history/selection thực tế; khóa cách xử lý với P7-05 trước group/split proposal.
- [ ] P7-03.5 Audit overlaps với datasets/studies đã dùng, phân biệt authorship với exposure; sửa metadata sai có correction record, không suy tác giả từ trùng câu.
- [ ] P7-03.6 Gom connected families, đề xuất dev/test/holdout có positive/negative và positive easy/hard ở từng split; dev folds có absence/incomplete/complete.
- [ ] P7-03.7 Lập gap report; chỉ thu/review thêm đúng strata/groups còn thiếu. Freeze F0 proposal và dev eligibility trước P7-09.

**Bàn giao:** reviewed question/review packets, audit sidecar,
`data/benchmark/human_retrieval.jsonl` bản chuẩn bị freeze, group/split proposal và gap report.
**Nghiệm thu:** qid duy nhất; mỗi nhãn có reviewer role/evidence justification; quotas M1 đủ;
held-out groups độc lập với tuning history. Export bằng intake sau review thật.
**Khi fail:** câu thiếu approval vẫn pending; chuyển known-exposed groups sang dev/research;
thu nhóm độc lập thay phần held-out thiếu, không viết lại toàn bộ bộ dữ liệu.

<a id="p7-04"></a>

### P7-04 — Validator, leakage, freeze và group statistics

**Owner:** evaluation engineer. **Ưu tiên:** P0. **Phụ thuộc:** P7-02, kiểm chứng P7-03.
**Ước lượng:** 2–3 ngày.

- [ ] P7-04.1 Bind author/reviewer packets, record/context/index hashes, schema và summary; reject false approval, changed evidence hoặc generic identity không audit được.
- [ ] P7-04.2 Audit exact/near duplicates và connected family across split + mọi registered study; review near-match borderline thay vì tự suy authorship.
- [ ] P7-04.3 Sửa assign-splits/canonical export: hash nội dung sau assignment; union splits bằng canonical, không thiếu/lặp qid; seed/group allocation lưu trong manifest. Chỉ connected group có exposure history hoàn chỉnh chứng minh chưa dùng mới được vào test/holdout; known/unknown exposure ép dev.
- [ ] P7-04.4 Freeze idempotent với cùng bytes hoặc reject overwrite; parallel invocation không overwrite lock. Bảo đảm dev studies chỉ nhận dev eligibility F0.
- [ ] P7-04.5 Thêm group bootstrap, all-gold metrics, FPR numerator/denominator/CI và subgroup sample adequacy; không thay metric compatibility âm thầm.
- [ ] P7-04.6 Thêm supplemental gate schema/aggregation vào validator + final manifest, stage prerequisites tương ứng; báo BLOCKED khi thiếu observations.
- [ ] P7-04.7 Test valid direct-authored data, fake review, tampered context/index/split/hash, transitive leakage, exposed held-out, zero denominator và mismatched metric.

**Vị trí:** freezer/intake, `evaluation/common/release_artifacts.py`,
`evaluation/retrieval/compare_retrieval_quality.py`, reranker gates/manifest, tests tương ứng.
**Bàn giao:** validators/splitter/statistics, proposed leakage/group-statistics reports,
schema migration note và negative regression evidence.
**Nghiệm thu:** hợp lệ PASS, vi phạm fail closed; validator tái tính từ raw;
existing M0–M12 thresholds giữ nguyên; FPR claim đúng loại CI/cỡ mẫu.
**Khi fail:** sửa validator trước F1, không manual override để freeze dữ liệu sai.

<a id="p7-05"></a>

### P7-05 — Context, selection, scope và cache contract

**Owner:** RAG engineer. **Ưu tiên:** P0. **Phụ thuộc:** P7-03. **Ước lượng:** 1–2 ngày.

- [ ] P7-05.1 Chốt request schema: raw question, history, selected text, authorized doc IDs, filters; phân biệt missing scope với explicit empty scope.
- [ ] P7-05.2 Resolve contextual query chỉ từ input cho phép; raw/resolved text trace được kiểm tra. Không dùng gold/qid/difficulty/expected answer để resolve.
- [ ] P7-05.3 Scope xuyên retriever/reranker/evidence/citation; selection là input, không là trusted evidence nếu chưa xác minh vào source.
- [ ] P7-05.4 Cache bind history/selection/scope/filters/index/model/policy; cùng câu nhưng khác context/scope không reuse câu trả lời.
- [ ] P7-05.5 Thiếu history bắt buộc trả clarification. Nếu loại contextual khỏi MVP, quyết định trước F0, giữ exclusion log và bù quotas; không loại sau khi thấy fail.
- [ ] P7-05.6 Cập nhật benchmark, paired answer/HTTP/staging adapters cùng contract; test cross-context/cache và scope từ request đến citation.

**Vị trí:** `src/campusai/rag/{schemas,service,cache}.py`, retrieval contracts,
evaluation adapters và contextual tests.
**Bàn giao:** contract document/schema, adapter implementation, contextual/scope/cache report.
**Nghiệm thu:** mọi scored input tương thích runtime; cùng authorized scope ở hai arms;
không leakage, không bỏ context ngầm, clarification đúng cases.
**Khi fail:** giữ dataset pending hoặc sửa contract trước F1; không chấm raw question thiếu history.

<a id="p7-06"></a>

### P7-06 — Harness và rubric answer/citation

**Owner:** evaluation engineer + grounding reviewer. **Ưu tiên:** P0.
**Phụ thuộc:** P7-03/P7-05. **Ước lượng:** 2–3 ngày cộng review.

- [ ] P7-06.1 Xây paired Phase 6/7 harness: cùng raw input/scope, LLM provider/model/prompt, generation parameters và context budget; chỉ khác retrieval policy.
- [ ] P7-06.2 Tắt answer/LLM caches cho quality run; lưu request identities, selected context, answers, atomic claims, citations, abstention, timing và token usage.
- [ ] P7-06.3 Rubric correctness/qualifiers/code/number/unit/version và support claim–citation; table/multi-hop phải đủ header/hops. Abstention sai tính vào accuracy.
- [ ] P7-06.4 Project owner hoặc independent reviewer review semantic support trên exact output; khai báo role, blind arm identity khi khả thi. Double-review/adjudication nếu có nhiều reviewer; owner self-review không được gọi là độc lập. Judge tự động chỉ dùng khi audit với human sample.
- [ ] P7-06.5 Khóa S4/S5, aggregation, empty-answer behavior, subgroup definitions, provider-repeat protocol và cost ceiling trước F1. Missing usage báo unknown, không ghi cost 0 giả.
- [ ] P7-06.6 Validate/recompute report từ raw reviews; test valid coordinates nhưng wrong semantic support, wrong number/unit, missing hop và câu trả lời rỗng.

**Vị trí:** reuse `evaluation/grounding/` metrics/rubric; module paired reranker-answer mới;
`rag/grounding.py` chỉ sửa nếu dev test phát hiện lỗi trong scope.
**Bàn giao:** proposed `reranker_answer_quality.json`, `reranker_answer_observations.jsonl`,
claim review audit và rubric/config hashes. **Đây là harness/report cần triển khai.**
**Nghiệm thu task:** harness/rubric/validator pass dev fixtures + reviewed pilot;
chưa tuyên bố held-out quality PASS. S4/S5 nghiệm thu chính thức ở P7-14.
**Khi fail:** sửa metric/rubric/answer contract trước F1; giữ provider errors và labels.

<a id="p7-07"></a>

### P7-07 — Startup warm-up, readiness và lifecycle

**Owner:** runtime engineer. **Ưu tiên:** P0. **Phụ thuộc:** không chờ human benchmark.
**Ước lượng:** 1–2 ngày.

- [ ] P7-07.1 Chốt trạng thái disabled/loading/warming/ready/failed/closing; Phase 7 chỉ admission khi warm thành công trên identity đúng.
- [ ] P7-07.2 Tách startup timeout khỏi request budget; production không bypass warm/readiness do optional flag. Warm fail vẫn phục vụ Phase 6.
- [ ] P7-07.3 Singleton loader một lần/process; concurrent startup không tạo nhiều model; warm-up input hợp lệ và không cache nhầm vào user query.
- [ ] P7-07.4 Shutdown/rollback đóng admission, cancel queued work, quản lý in-flight native work và release provider resources theo contract.
- [ ] P7-07.5 Test first request không cold-load, warm timeout/exception, repeated start/stop, concurrent initialization và readiness recovery.

**Vị trí:** `retrieval/{model_runtime,reranker,reranker_activation}.py` và service startup.
**Bàn giao:** runtime patch + lifecycle/readiness report và regression tests.
**Nghiệm thu:** zero model load trong request path; warm fail không bật Phase 7;
không loader duplicate/rò resources/permit. Smoke model thật ở M3 bổ sung unit evidence.
**Khi fail:** runtime giữ Phase 6, sửa lifecycle trước F1.

<a id="p7-08"></a>

### P7-08 — Trace, resource sampling và đo lỗi thật

**Owner:** runtime/evaluation engineer. **Ưu tiên:** P1.
**Phụ thuộc:** P7-05/P7-07. **Ước lượng:** 1–2 ngày.

- [ ] P7-08.1 Trace event riêng: route selected, inference attempted/completed, rerank applied, policy abstention, provider fallback; định nghĩa `reranker_used` và reason code.
- [ ] P7-08.2 Request ID từ server; timestamps UTC có timezone, monotonic duration; queue/retrieval/inference/grounding/LLM/serialization/end-to-end timings.
- [ ] P7-08.3 Ghi candidate cap/count, selected subset, route/model/policy/runtime identities, cache status, scope và resource limits.
- [ ] P7-08.4 Sample process/children RSS, CPU, queue và CUDA allocated/reserved/peak/device capacity theo protocol; reset peak giữa profiles, ghi interval và cold/warm.
- [ ] P7-08.5 Giữ semaphore cho tới native work kết thúc dù request timeout; đếm accepted/rejected/timed-out/failed/completed/in-flight, successful throughput riêng.
- [ ] P7-08.6 Test recompute summaries, circuit fast-fail không tính success, timeout không hồi permit sớm, tracing không chứa secret hoặc arbitrary exception path.

**Bàn giao:** trace/resource schema + sampler, raw pilot observations và summary tests;
update capacity/HTTP/canary collectors dùng cùng semantics.
**Nghiệm thu:** counters reconcile, duration không âm, samples bind đúng request/PID;
summary khớp raw, không hidden error/CPU-only GPU report giả.
**Khi fail:** sửa instrumentation trước F1; chưa dùng report pilot làm M7/M11.

<a id="p7-09"></a>

### P7-09 — Joint dev feasibility và shortlist cấu hình

**Owner:** retrieval/runtime engineer. **Ưu tiên:** P0.
**Phụ thuộc:** P7-03–08, F0/dev eligibility. **Ước lượng:** 2–5 ngày mỗi research cycle.

- [ ] P7-09.1 Tạo isolated study/cycle; register allowed dev/groups; reproduce Phase 6 dev baseline và failure buckets trước tối ưu.
- [ ] P7-09.2 Ablation lần lượt route, input/truncation, model, dtype, batching/window, cap, evidence policy; giữ config/raw scores/failed attempts cho từng lần.
- [ ] P7-09.3 Chẩn đoán false abstention, thiếu gold trong candidate/subset, exact-code, wrong program/year, table và multi-hop; không dùng cap 40 rerank làm release candidate.
- [ ] P7-09.4 So sánh chất lượng và tải trên cùng configuration identity; không ghép quality của FP32/cap20 với latency FP16/cap8.
- [ ] P7-09.5 Chọn shortlist đáp ứng đồng thời dev route hard ≥95%, easy unnecessary ≤20%, positive hit Recall@5 ≥95%, FPR ≤1%, cap ≤20, p95 ≤1s, timeout ≤0,5%, errors =0; báo all-gold/evidence recall riêng.
- [ ] P7-09.6 Chốt deployment profile, cap-selection objective/tie-break, HTTP SLO, workload và public-cost constraints trước F1; viết decision record cả lựa chọn bị loại.

**Bàn giao:** proposed `reranker_dev_feasibility.json`, comparison Markdown, raw study
archive và config candidate với full identities; tất cả ghi research-only.
**Nghiệm thu:** ít nhất một cấu hình jointly feasible và harness/readiness đủ;
đánh giá dev answer pilot đạt hướng S4/S5 trước tiêu thụ held-out.
**Khi fail:** tiếp tục dev cycle hoặc giữ Phase 6/conditional; không mở test để chọn model.

## 5. P7-10–P7-20 — Acceptance của cấu hình đã freeze

<a id="p7-10"></a>

### P7-10 — Freeze source/runtime/dataset, đóng M0/M1

**Owner:** release engineer + data reviewer. **Ưu tiên:** P0.
**Phụ thuộc:** P7-01–09 DONE. **Ước lượng:** 0,5–1 ngày.

- [ ] P7-10.1 Review checklist F1: code/tests/validator/supplemental gates, schema/rubric/harness, selected model/runtime/dependencies, scope/context, workload/SLO.
- [ ] P7-10.2 Source freeze commit theo quy trình dự án; giữ `plan.md` tracked. Lập release cycle ID/source digest và runtime/deployment manifests.
- [ ] P7-10.3 Export canonical bytes với final groups/splits; hashes raw/canonical/review/index/splits khớp. Kiểm tra union splits và strata quotas.
- [ ] P7-10.4 Revalidate M0 trên physical index; chạy `release_workflow human-freeze`; archive outputs + review/manifest.
- [ ] P7-10.5 Kiểm tra F0 dev đã dùng nằm đúng final dev, không đổi nhóm thành test/holdout; khóa data và exposure snapshot.

**Bàn giao hiện có:** `human_benchmark_review.json`, `human_benchmark_manifest.json`,
`human_retrieval_{dev,test,holdout}.jsonl`; thêm F1 identity/protocol record.
**Nghiệm thu:** validator `--through M1` M0/M1 PASS, score vẫn null; S1 đầy đủ.
**Khi fail:** sửa input trước nghiệm thu sau; source changes cần F1 mới, giữ failed attempt.

<a id="p7-11"></a>

### P7-11 — Candidate coverage và model/provider contract, M2/M3

**Owner:** retrieval/runtime reviewer. **Ưu tiên:** P0. **Phụ thuộc:** M1 PASS.
**Ước lượng:** 0,5–1,5 ngày.

- [ ] P7-11.1 Chạy candidate generation cap40 không rerank; lưu candidates/gold misses trên generated test/holdout và human dev/test/holdout.
- [ ] P7-11.2 Recompute hit/all-gold/evidence recall overall và strata; check table/multi-hop/program/year/scoped coverage và zero duplicate/provenance/scope.
- [ ] P7-11.3 Pin physical snapshot/tokenizer/files revision, device/dtype/batch/max length/window và installed runtime; smoke offline/determinism.
- [ ] P7-11.4 Đo model load/warm, singleton + startup readiness thật; chạy provider contract injections của M3.
- [ ] P7-11.5 Ghi held-out exposure của M2; results chỉ đóng gate, không dùng per-qid misses để tune trong cycle này.

**Lệnh:** `release_workflow candidate`; `release_workflow model --model-dir SNAPSHOT`
với device/dtype/inference options đúng F1.
**Bàn giao:** `candidate_coverage.json`, `model_snapshot_smoke.json`,
`reranker_provider_contract.json`, raw coverage/smoke observations.
**Nghiệm thu:** M2/M3 PASS đúng bảng mục 3, all-gold strata không bị che bởi hit rate.
**Khi fail:** diagnose trên dev; đổi retrieval/model cần cycle/freeze/evidence phù hợp,
không sửa gold/loại strata lỗi sau khi thấy kết quả.

<a id="p7-12"></a>

### P7-12 — Fit và freeze routing, M4

**Owner:** routing reviewer. **Ưu tiên:** P0. **Phụ thuộc:** M3 PASS.
**Ước lượng:** 0,5–1 ngày nếu dev feasibility đã đủ.

- [ ] P7-12.1 Fit grouped OOF trên human dev, features runtime allowlist, cùng retrieval plan top5; audit không qid/difficulty/gold/template leakage.
- [ ] P7-12.2 Validate probability/feature policy, bypass exact-code/abstention, deterministic behavior và coverage samples + bypass bằng dataset count.
- [ ] P7-12.3 Ghi route lock **trước** test/holdout route; lưu samples, confusion, probabilities/thresholds/folds/seed và hashes.
- [ ] P7-12.4 Chạy route test/holdout một policy frozen; báo hard recall/easy unnecessary theo nhóm và denominator; update exposure registry.

**Lệnh:** `release_workflow route` theo protocol F1.
**Bàn giao:** `hard_query_route_calibration.json`, `hard_query_route_confusion.json`,
`reranker_route_freeze.json`, diagnostics/raw samples.
**Nghiệm thu:** M4 PASS (dev 95%/20%, held-out 90%/25%, bypass 0 rerank);
held-out route outputs không trở thành training signals cho P7-13.
**Khi fail:** dừng cycle, giữ lock; route mới dùng dev nghiên cứu và held-out độc lập.

<a id="p7-13"></a>

### P7-13 — Cap sweep và evidence calibration, M5

**Owner:** calibration reviewer. **Ưu tiên:** P0. **Phụ thuộc:** M4 PASS.
**Ước lượng:** 0,5–1,5 ngày.

- [ ] P7-13.1 Giữ route/model/input/dtype/runtime identity; chạy đủ cap8/10/12/16/20 trên human dev, grouped OOF với absence/incomplete/complete.
- [ ] P7-13.2 Lưu raw candidate scores/probabilities, proposals/refit/folds/class counts; chấm all-gold/false abstention/FPR và policy actions.
- [ ] P7-13.3 Chọn cap theo objective và tie-break đã khóa F1, đồng thời quality + latency; legacy raw-score threshold không tự coi là calibrated probability.
- [ ] P7-13.4 Đo eligibility/inference/applied/fallback, p95/timeout/invalid score; refit/recompute validator từ raw, không tự khai boolean pass.

**Lệnh:** `release_workflow calibration --model-dir SNAPSHOT` cùng options F1;
chỉ human dev, không test/holdout.
**Bàn giao:** `reranker_score_calibration.json`, `reranker_cap_sensitivity.json`,
five-cap trial JSON/raw files và config được chọn.
**Nghiệm thu:** M5 PASS: recall ≥95%, FPR ≤1%, invalid=0, selected p95 ≤1s,
timeout ≤0,5%, eligible >0; đủ three-class folds và identity xuyên trials.
Field `recall` hiện là positive hit Recall@5; báo thêm all-gold/evidence recall,
không đổi nghĩa field đó để tuyên bố đã lấy đủ các hop.
**Khi fail:** giữ failed attempts; không dùng route held-out errors để điều chỉnh.
Đổi shortlist/protocol sau F2 cần cycle/evidence theo freeze rules.

<a id="p7-14"></a>

### P7-14 — Paired held-out ranking và answer/citation, M6 + S3–S5

**Owner:** quality engineer + grounding reviewer. **Ưu tiên:** P0.
**Phụ thuộc:** M5 PASS. **Ước lượng:** 1–3 ngày cộng review.

- [ ] P7-14.1 Khóa F3 policy/model/route/cap/calibration/data/source/rubric **trước** quality held-out; giữ Phase 6 baseline nguyên vẹn.
- [ ] P7-14.2 Chạy paired generated test/holdout + human test/holdout, đúng cùng qid/scope/context; lưu ranked evidence trước/sau, không subset cherry-pick.
- [ ] P7-14.3 Tái tính MRR/nDCG/hit/all-gold/evidence recall, hard/subgroups, win/tie/loss, regression qids và ≥10.000 group bootstrap resamples.
- [ ] P7-14.4 Chạy paired live answer harness P7-06 trên primary human test/holdout; nếu generated thiếu answer rubric thì chỉ claim ranking của bộ đó.
- [ ] P7-14.5 Blind review/adjudicate claims/citations, compute S4/S5, false abstention/answer FPR/citation recall, token usage/cost và uncertainty.
- [ ] P7-14.6 Validator recompute và bind raw/reviews/rubric; archive mọi regression với reason và mức ảnh hưởng, không sửa cấu hình để chạy lại trên test đó.

**Lệnh ranking:** `release_workflow quality --model-dir SNAPSHOT`.
CLI answer bổ sung được tạo ở P7-06, chưa có sẵn trong workflow hiện tại.
**Bàn giao:** `retrieval_quality_comparison.json`/Markdown,
`reranker_policy_freeze.json`, regression cases, answer-quality/raw/review reports.
**Nghiệm thu:** M6 và S3–S5 cùng PASS; từng split được chấm riêng, không gộp để che fail;
multi-hop đủ bằng chứng, quality improvement vượt CI, không vi phạm scope/provenance.
**Khi fail:** giữ conditional; lỗi hạ tầng rerun cùng identity có history, đổi policy
phải nghiên cứu dev và dùng held-out độc lập cho cycle mới.

<a id="p7-15"></a>

### P7-15 — Capacity, resources và live HTTP, M7

**Owner:** runtime/deployment reviewer. **Ưu tiên:** P0.
**Phụ thuộc:** M6 + S3–S5 PASS. **Ước lượng:** 1–2 ngày; tùy quota live LLM.

- [ ] P7-15.1 Xác nhận deployment RAM limit thật, CPU/GPU/device capacity/runtime; request timeout1000ms, failure limit3, cache0, queue đã chốt 0–99.
- [ ] P7-15.2 Matrix cap/concurrency: 8/1, 10/1, 20/1, 10/5, 10/20; CUDA thêm 20/5; selected cap phải có 1/5/10/20. ≥100 requests/profile.
- [ ] P7-15.3 Performance cohort ≥30 hard và ≥30 hard-rerank requests; collect cold/warm, queue, inference/service p50/p95/p99, successful throughput và all failures.
- [ ] P7-15.4 HTTP thật + LLM thật với cache tắt tại concurrency1/5/10/20; ≥100/profile, ≥5 easy/hard/negative/scoped mỗi cohort, ≥30 LLM calls và grounded responses/profile.
- [ ] P7-15.5 HTTP p95 budget khóa F1 (mặc định10s); tách allocation/queue/provider/serialization, token usage/cost; provider errors không coi là abstention thành công.
- [ ] P7-15.6 Audit sampled RSS/children/VRAM, leak/circuit/timeout permits; recommended soak ≥30 phút và ≥1.000 requests/profile nếu cần claim stability/p99 chắc hơn.

**Lệnh:** `release_workflow performance --model-dir SNAPSHOT`
với `--deployment-ram-bytes LIMIT --llm-config CONFIG` và profile/SLO đúng freeze.
**Bàn giao:** `reranker_{performance,capacity,resource_budget,http_end_to_end}.json`,
raw requests/resources, environment report và soak report nếu chạy.
**Nghiệm thu:** M7 và S6 PASS, thresholds mục 3; mọi selected-cap profile đạt,
timeout/circuit không che overload; RSS ≤75% limit và GPU usage được đo thật.
**Khi fail:** không tăng timeout/SLO hoặc đổi limit giả; sửa dev/target rồi tạo
evidence mới phù hợp. Thiếu credentials/quota là thiếu evidence, không giả LLM responses.

<a id="p7-16"></a>

### P7-16 — Security, adversarial và grounding regression, M8

**Owner:** security/grounding reviewer. **Ưu tiên:** P1. **Phụ thuộc:** M7 PASS.
**Ước lượng:** 0,5–1 ngày với case set chuẩn bị trước F1.

- [ ] P7-16.1 Freeze ≥50 cases với expected behavior, đủ 12 nhóm: out_of_corpus, similar_wrong_document, conflicting_documents, exact_code_trap, year_mismatch, entity_mismatch, chunk_prompt_injection, malformed_metadata, duplicate_chunks, scope_restriction, empty_result, fake_citation.
- [ ] P7-16.2 Run attacks trên pipeline thật với frozen model/index/policy; evidence mutations có controlled boundary và log before/after.
- [ ] P7-16.3 Audit outputs với frozen evidence + Phase 6: context injection không thành instruction, wrong year/document/scope/citation bị chặn.
- [ ] P7-16.4 Run required grounding/adversarial/reranker integration tests, archive JUnit XML + source hashes; skip required case không được PASS.

**Lệnh:** `release_workflow security --model-dir SNAPSHOT --cases CASES`.
**Bàn giao:** `reranker_security.json`, `reranker_grounding_regression.json`,
raw attack cases/output và XML đúng schema validator.
**Nghiệm thu:** M8 PASS; tất cả attacks đạt expected behavior, FPR ≤1%,
zero scope/provenance/invalid citation; required tests thực sự chạy và không skip/fail.
**Khi fail:** preserve attack, sửa dev source rồi invalidate/rerun affected gates;
không đổi expected behavior để biến unsafe output thành PASS.

<a id="p7-17"></a>

### P7-17 — Controlled faults và recovery, M9

**Owner:** runtime reviewer. **Ưu tiên:** P1. **Phụ thuộc:** M8 PASS.
**Ước lượng:** 0,5–1 ngày.

- [ ] P7-17.1 Inject đủ required model/calibration missing/hash mismatch, timeout, queue_full, OOM/exception, invalid/non-finite score, wrong candidate/doc/page, empty output, cache/revision mismatch.
- [ ] P7-17.2 Bổ sung malformed output/rank, concurrent failures và late native completion; lưu actual before/after calls/provider/circuit/permits.
- [ ] P7-17.3 Check fallback bằng Phase 6 ordered outputs/coordinates/content/scores theo contract; retrieval output đúng không tự chứng minh live LLM answer giống từng byte.
- [ ] P7-17.4 Permanent failure đóng provider/disable Phase 7; follow-up probes zero new inference. Transient fault không rò resources hoặc làm hỏng Phase 6.

**Lệnh:** `release_workflow faults`; các cases mở rộng cần collector/tests bổ sung.
**Bàn giao:** `reranker_failure_matrix.json`, raw injection observations/follow-up probes.
**Nghiệm thu:** M9 PASS, đủ required cases; zero permits leak sau native work kết thúc,
zero new inference sau permanent disable; không chỉ status boolean tự khai.
**Khi fail:** fix lifecycle/provider boundary và revalidate identity; không bỏ case OOM/timeout.

<a id="p7-18"></a>

### P7-18 — Rollback hai process và shared cache, M10

**Owner:** operations reviewer. **Ưu tiên:** P1. **Phụ thuộc:** M9 PASS.
**Ước lượng:** 0,5–1 ngày.

- [ ] P7-18.1 Prepopulate shared answer cache với Phase 7 outputs; lưu namespace/hash và baseline probes.
- [ ] P7-18.2 Trigger rollback: close admission, cancel queued work, disable model calls, change policy/cache namespace; đo từ trigger đến Phase 6 ready.
- [ ] P7-18.3 Restart sang PID thứ hai với cùng shared cache; chạy probes qua cả hai process, model call counts trước/sau và index digest.
- [ ] P7-18.4 Verify không reuse reranked cached answer, không rebuild index, cleanup provider/in-flight behavior đúng contract; record cold restart timing riêng.

**Lệnh:** `release_workflow rollback --model-dir SNAPSHOT`.
**Bàn giao:** `reranker_rollback.json`, two-PID probes, cache/index hashes và timing raw.
**Nghiệm thu:** M10 PASS, rollback ≤300s, zero new inference, Phase 6 outputs đúng
cả hai process, không cache contamination/index mutation.
**Khi fail:** sửa admission/cache namespace/lifecycle; giữ observations và đo lại affected evidence.

<a id="p7-19"></a>

### P7-19 — Staging canary và auto-rollback, M11

**Owner:** staging/deployment owner. **Ưu tiên:** P0.
**Phụ thuộc:** M0–M10 + supplemental gates PASS. **Ước lượng:** 1–2 ngày tùy runtime/quota.

- [ ] P7-19.1 Khởi động isolated staging process đúng runtime/environment identity, same frozen policy/limits; local staging ghi local scope, không tự nhận là public deployment.
- [ ] P7-19.2 Chạy 0→1→5→10→25%, mỗi step ba healthy windows ≥100 requests/window; giữ cohort dễ/khó/negative/scoped và deterministic assignment.
- [ ] P7-19.3 Đảm bảo eligible hard/easy **trong selected cohort** có observations; báo assigned/route-selected/inference/applied rates riêng, không so toàn bộ traffic với tỷ lệ canary.
- [ ] P7-19.4 Collect ≥15 windows/1.500 requests cùng raw IDs/timestamps/outputs/scope, stages/resources/queue, FPR/fallback/errors/selection/route metrics.
- [ ] P7-19.5 Đủ tám rollback triggers: provenance, scope, citation, timeout, FPR, error regression, memory, latency ba windows liên tiếp; faults giữ telemetry thật + follow-up.
- [ ] P7-19.6 Auditor recompute decisions; sau rollback provider đóng, zero new inference, Phase 6 outputs đúng. Final25% cũng phải đạt budgets.

**Lệnh:** `release_workflow staging-collect --model-dir SNAPSHOT` cho local measured
staging; `staging --observations WINDOWS --fault-observations FAULTS` để audit telemetry.
**Bàn giao:** `reranker_staging.json`, `canary_observations.json`, archived raw healthy/fault
telemetry, allocation/lease/queue constraints và signed-off deployment identity.
**Nghiệm thu:** M11 + S6 PASS; p95≤1s/p99≤2s, FPR/timeout≤1%, hard route coverage≥90%,
easy rerank thừa≤25% trong eligible selected cohort, RSS≤75% RAM,
zero scope/citation/provenance và đủ tám exercises. Không errors regression.
**Khi fail:** rollback về Phase 6, preserve telemetry; không promote step sau.
Target public khác runtime cần separate cycle/profile evidence, giữ GPU thuê bằng0.

<a id="p7-20"></a>

### P7-20 — Release bundle, reproducibility và handoff, M12

**Owner:** release owner + reviewer. **Ưu tiên:** P0. **Phụ thuộc:** mọi task trước DONE.
**Ước lượng:** 1 ngày cộng rerun nếu reproducibility fail.

- [ ] P7-20.1 Build archive manifest: dataset/splits/review/index/model/runtime, all gates + supplementals, raw observations/failed attempts/locks, checksums và restore commands.
- [ ] P7-20.2 Sync `plan.md`, release plan/spec/progress/runbook/README với evidence hiện tại; cập nhật counts/status từ checks mới, không copy verification cũ.
- [ ] P7-20.3 Full suite với coverage≥85%, compile, secret/diff/link checks và hai live-LLM integration tests thật; lưu commands/results/XML, không lưu credentials.
- [ ] P7-20.4 Evidence/source commits theo quy trình repo; restore/verify trong clean checkout bằng pinned runtime/model và physical index, không fallback download revision khác.
- [ ] P7-20.5 Validate M12 + supplemental gates; build final manifest với physical model recheck. Readiness/manifest output ignored, không overwrite gate evidence/dirty tree.
- [ ] P7-20.6 Bàn giao activation config, health/readiness/fallback/rollback runbook, runtime scope và limitations; production activation là bước riêng theo authorization thực tế.

**Lệnh:** `release_workflow validate`,
`release_workflow release --model-dir SNAPSHOT` sau evidence commit/clean tree.
**Bàn giao:** release bundle + checksums/archive locator, final
`reranker_release_manifest.json`, clean-checkout readiness, verification report,
updated roadmap và handoff note.
**Nghiệm thu:** M0–M12 PASS + S1–S6 PASS, score10.0/all gates true, bindings đúng;
người khác restore và tái tính được report từ raw, model/index khớp vật lý.
**Khi fail:** bundle chưa release; xác định missing/tampered/changed dependency và
rerun phần invalidated. Không bật production chỉ vì có file manifest.

## 6. Thứ tự triển khai và điều kiện chuyển task

| Đợt | Tasks | Điều kiện mở đợt kế tiếp |
|---|---|---|
| A — Audit/dữ liệu | 01 → 02 → 03/04; 07 có thể làm độc lập | Canonical staging/review/groups/dev eligibility có kiểm chứng |
| B — Contract/harness/runtime | 05/06 và 07/08, sau đó 09 | Code/gates/harness hoàn chỉnh, joint dev feasible, F0 không leakage |
| C — Freeze/ranking/answer | 10 → 11 → 12 → 13 → 14 | M0–M6 + answer/group/evidence gates PASS đúng F1/F3 |
| D — Capacity/reliability | 15 → 16 → 17 → 18 | M7–M10 PASS trên đúng target profile |
| E — Staging/package | 19 → 20 | M11/M12, S1–S6 và reproducibility PASS |

Đây là khả năng làm độc lập giữa **workstreams**, không bắt buộc dùng nhiều agent.
Case sets, reviewer rubric, runtime setup và archive design có thể chuẩn bị sớm;
official acceptance vẫn theo prerequisites. Ước lượng từng task là effort kỹ thuật,
không là lịch bảo đảm; human review, research cycles, LLM/GPU quota quyết định elapsed time.

**Handoff cuối phase gồm:** source/runtime config, canonical human benchmark và review,
M0–M12/supplemental/raw evidence bundle, measured deployment profile, activation và
rollback runbook, reproduction instructions, updated `plan.md` và known limitations.

## 7. Việc bắt đầu ngay và các quyết định cần chốt bằng evidence

1. **P7-01/P7-02:** kiểm kê, sửa summary/schema theo bytes thật; không chờ thu thêm toàn bộ dataset.
2. **P7-07:** sửa warm-up/readiness độc lập với human freeze.
3. **P7-03/P7-04:** đối chiếu reviewer/scope/lineage, group/exposure; chỉ bổ sung đúng gaps.
4. **P7-05/P7-06/P7-08:** làm input/answer/trace contracts để dev feasibility đo đúng mục tiêu.
5. **P7-09:** chỉ freeze acceptance khi một cấu hình cùng đạt quality + resource targets.

Recheck local candidate ngày lập spec: **180 records**, **135 positive**, **45 negative**,
**83 groups**, **180 thiếu qid/split**, **45 negative scope rỗng**, **15 có context**;
summary hash không khớp JSONL. Đây là lỗi contract/readiness cần xử lý, không phủ nhận
xác nhận authorship của chủ dự án. Historical studies/tests trong progress không được
đổi nhãn thành verification mới của source sau khi implementation thay đổi.

Các quyết định owner phải ghi vào protocol: reviewer identity/audit thực tế, contextual
scope, held-out eligibility, target runtime/limit/cost, cap-selection objective,
HTTP SLO, rubric/CI convention và policy activation. Có đủ evidence thì thực hiện;
thiếu đầu vào ngoại sinh thì chỉ block task phụ thuộc và tiếp tục việc độc lập.
