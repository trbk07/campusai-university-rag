# Phase 7 — Kế hoạch hoàn thành từng task với chuẩn đầu ra 10/10

Ngày lập: **04/10/2026**, múi giờ **Asia/Bangkok**. Đây là kế hoạch thực thi dựa trên repository tại thời điểm đọc, **không phải báo cáo nghiệm thu mới**. Không chạy benchmark, gọi LLM, sửa runtime hoặc freeze dữ liệu trong lần lập kế hoạch này.

Roadmap gốc: [`plan.md`](../../plan.md#phase-7--reranker). Kế hoạch này bổ sung trạng thái và thứ tự xử lý hiện tại cho [đặc tả P7-01–P7-20](phase7_task_spec.md); giữ nguyên các ID để đối chiếu backlog. Các ngưỡng thực thi lấy từ [validator M0–M12](../../evaluation/reranker/reranker_release_gates.py) và [validator S1–S6](../../evaluation/reranker/supplemental_gates.py). [Runbook](reranker_release_runbook.md) cung cấp CLI, nhưng phần mô tả cycle r10 trong runbook đã cũ: cycle hiện hành phải đọc từ [selector](../../configs/phase7_release_cycle.json).

## 1. Đích đến và trạng thái xuất phát

Phase 7 hoàn thành khi reranker cho truy vấn khó cải thiện retrieval và câu trả lời có citation, vận hành trong ngân sách đã đo, và quay về Phase 6 đúng contract khi lỗi. “Hoàn hảo” trong kế hoạch này nghĩa là **đủ toàn bộ tiêu chí nghiệm thu có bằng chứng**, không phải cam kết đúng mọi câu hỏi ngoài benchmark.

Điều kiện đóng phase đồng thời:

- **M0–M12 và S1–S6 đều PASS: 19/19 gate**; validator cuối trả `status=pass`, `score=10.0`, `all_release_gates_pass=true`.
- Cùng identity source/runtime/index/model/tokenizer/dataset/route/evidence policy/deployment trên các evidence cần liên kết; vật lý khớp manifest, working tree nghiệm thu sạch.
- Chất lượng có paired observations, review đúng nguồn gốc, CI theo connected groups; latency/resources/HTTP/canary có phép đo thật.
- Khôi phục được bundle và tái tính metric trong clean checkout; rollback đã đo qua hai process và shared cache.
- `plan.md` ở root tiếp tục được Git theo dõi; runtime được nghiệm thu ghi rõ local GPU hoặc public. Kết quả RTX 4060 local không tự nghiệm thu một public runtime khác.

### 1.1. Những gì hiện có và giới hạn kế thừa

| Hạng mục | Trạng thái đọc được | Hệ quả đối với kế hoạch |
|---|---|---|
| Active cycle | `phase7-release-20261004-r18`; results `evaluation/results/phase7-source-context-20261004-r18`; index selector `.tmp/hybrid-index` | Giữ làm lịch sử; không tự chuyển selector trong task lập plan |
| Gate r18 | **M0/M1/S1 PASS; M2 FAIL; 3/19**, `score=null` theo roadmap và evidence lưu | Các PASS là của cycle cũ, không tự chuyển sang successor |
| Lỗi M2 | Human-test hard all-gold coverage **26/28 = 92,86%**, cần ≥95% | Phải chứng minh coverage trên dev và đo successor hợp lệ |
| Exposure r18 | Test/holdout đã được dùng cho M2 | Không dùng lại làm held-out mới, không sửa gold để chữa kết quả |
| Index nguồn mở rộng | 14 documents, manifest hash `40a3e711298fdb66cdd906b19ad84ab9565dd43badfed7caed4eef81a671bec6`; archive khôi phục exact bytes | Đây là index nghiên cứu riêng; cần bảo đảm M0/baseline tương thích trước freeze release |
| Source batch b | 138 dòng môn học có mã; 47 connected proposals trong snapshot batch b; semantic history approval chưa hoàn tất | 47 proposals không đồng nghĩa 47 groups mới đủ điều kiện; phải screen lại với lịch sử cập nhật |
| Dev packet mới | **889 câu = 817 kế thừa + 72 mới**, 3 course families; row/review errors bằng 0; toàn bộ `dev_only` | Có thể dùng cho nghiên cứu sau khi kiểm tra bindings; không đủ điều kiện release do thiếu test/holdout |
| Subjects đã tiêu thụ cho dev | RBE2001, RBE3015, ELT6003, ELT6004, MAT6281, EMA6120 và aliases/families liên quan | Đưa vào exposure history; không chuyển các câu này hoặc biến thể phụ thuộc sang held-out |
| Feasibility cũ | 491 câu, cap 10: OOF hard recall 98,41%, easy rerank thừa 8,93%, Recall@5 98,10%, FPR 0,568%, p95 163,18 ms | `conditional`, index/source khác packet mới; chưa phải M4/M5/M7 PASS |
| Uplift dev cũ | MRR 0,915185 → 0,918360, khoảng **+0,35% tương đối**; nDCG 0,919116 → 0,921714, khoảng **+0,28%** | Chưa đủ bằng chứng hướng tới mục tiêu M6 +3%; cần study ranking/answer trên dev mới |
| Live LLM | Regression lịch sử có hai live tests bị skip; từng gặp quota 429 | Kiểm tra quota/uncached live path hiện tại; không suy quota hôm nay từ lỗi cũ |
| Working tree | Có nhiều sửa đổi và file chưa tracked trước lần lập kế hoạch | Lập inventory, review và commit đúng phạm vi trước F1; không dọn/xóa thay đổi để làm sạch tree |

Nguồn đối chiếu trạng thái: [r18 coverage](../../evaluation/results/phase7-source-context-20261004-r18/candidate_coverage.json), [joint dev study](../../evaluation/results/phase7-dev-feasibility-20261004/joint_dev_feasibility.json), [batch b summary](../../evaluation/results/phase7-successor-source-20261004b/task_summary_final.json), [dev packet preflight](../../evaluation/results/phase7-source-schema-dev-20261004/benchmark/preflight.json) và các cập nhật ngày 04/10 trong `plan.md`. Số đếm lịch sử khác nhau là snapshot khác nhau; không ghép thành một phép đo chung.

## 2. Quy tắc thực thi và chuẩn artifact chung

### 2.1. Trạng thái task và bằng chứng DONE

Luồng: `TODO → IN_PROGRESS → REVIEW → DONE`; `BLOCKED` phải ghi thiếu đầu vào nào, ai xử lý và điều kiện mở lại. Owner bên dưới là vai trò; khi nhận task phải điền người thực hiện thực tế.

Mỗi task chỉ DONE khi có đủ checklist, artifact, kết quả kiểm chứng và review. Với task acceptance, cần validator PASS đúng gate và cycle. Code/test có sẵn chỉ được kế thừa sau kiểm tra; report cũ khác identity không phải evidence mới.

Mẫu ledger cho từng task/subtask:

```text
Task / subtask: P7-xx / P7-xx.n
Owner / reviewer / review role:
Status / blocker / next task:
Cycle / source commit / source_sha256 / runtime_sha256:
Inputs + hashes / output paths + hashes:
Command / config / seed / start-end time / exit code:
Sample counts / independent groups / metrics / gate decision:
Review conclusion / unresolved issues / archive + restore command:
```

### 2.2. Nơi bàn giao

- Release successor: `data/benchmark/phase7_review_cycles/<successor-cycle>/` và `evaluation/results/<successor-results>/`.
- Dev research: thư mục study riêng dưới `evaluation/results/`; luôn ghi `release_eligible=false` cho exploratory evidence.
- Trong các task, `R/` là results directory của cycle đang thực hiện; `B/` là benchmark directory. Không mặc định dùng results root hoặc active selector r18.
- Tên report gate trong kế hoạch là tên validator hiện có. Các file như `completion_task_ledger.json`, `successor_gap_report.json`, `joint_dev_acceptance_plan.json` là **đầu ra đề xuất cần tạo**, không phải CLI đã có.
- Raw/archive lớn có locator bền vững, SHA-256 và hướng dẫn restore; `.tmp` không được là nơi lưu duy nhất.

Report ghi schema/task/cycle/status, UTC timestamps có timezone, command/config/seed, input/output hashes, numerator/denominator, groups/strata và raw references. Tỷ lệ dùng 0–1, thời gian ms, memory bytes; không NaN/Infinity, không điền 0 thay số chưa đo.

Bindings gồm source/runtime, physical index, Phase 6 calibration, model/tokenizer revisions/digests, inference options; từ M4 thêm route và từ M5 thêm cap/evidence calibration/dev split. Answer evidence thêm LLM/prompt/context budget/rubric/review protocol. Đọc đúng schema CLI hiện hành trước khi tạo report.

### 2.3. Các điểm freeze

| Điểm | Nội dung khóa | Điều kiện chuyển bước |
|---|---|---|
| F0 | History/exposure, connected groups, split proposal, dev eligibility | Đủ dev hợp lệ; test/holdout mới giữ kín khỏi tuning |
| F1 | Source/tests/validator, index/baseline, benchmark bytes, runtime/model, rubric/workload/SLO và protocol chọn cap | P7-01–09 đạt chuẩn; bắt đầu acceptance tuần tự |
| F2 | Route calibration, source/M3 bindings và lock trước M4 held-out | Dev fit + grouped OOF đạt ngưỡng; không dùng held-out chọn route |
| F3 | Cap/evidence/answer policy, protocol và tất cả bindings trước M6 quality held-out | M5 PASS; không tuning theo kết quả quality held-out |

M2/M4/M6 được đọc held-out đúng purpose nghiệm thu đã khóa; mỗi lần phải ghi exposure. Việc mở M2 không cấm các gate tiếp theo của cùng study đã đăng ký, nhưng cấm dùng lỗi per-qid của nó để tuning rồi gọi dữ liệu ấy là fresh. Nếu thay cấu hình sau exposure, lập successor có held-out độc lập phù hợp; giữ failed attempts và immutable locks.

## 3. Bảng chuẩn đầu ra bắt buộc

| Gate | Chuẩn nghiệm thu |
|---|---|
| M0 | Historical Phase 6 và hai rerun khớp; test Recall@5 ≥98%, holdout ≥95%, negative FPR=0; physical index/calibration/corpus/benchmark bindings đúng |
| M1 | ≥150 câu, ≥100 positive, ≥20 negative, ≥15 hard/multi-hop, ≥15 exact-code, ≥10 ambiguous; đủ review/scope/evidence/splits; owner/AI provenance khai báo đúng |
| M2 | Candidate cap 40: generated test ≥99%, generated holdout ≥97%; human dev/test/holdout ≥95%; hit và all-gold coverage đạt theo overall/strata; provenance/scope/duplicate errors=0 |
| M3 | Snapshot/tokenizer/runtime offline đúng digest; repeated-score delta ≤1e-5; provider contract PASS; singleton/warm/readiness đúng |
| M4 | Dev hard recall ≥95%, easy rerank thừa ≤20%; held-out hard ≥90%, easy thừa ≤25%; bypass exact/abstained và single-candidate đúng contract, zero prohibited rerank |
| M5 | Dev Recall@5 ≥95%, FPR ≤1%, invalid scores=0; đủ cap **8/10/12/16/20**; selected cap p95 ≤1.000 ms, timeout ≤0,5%, eligible requests>0; probability policy ba lớp hợp lệ |
| M6 | Generated/human test MRR và nDCG@5 cùng tăng ≥3% tương đối, Recall@5 không giảm; CI95% ΔMRR lower>0; holdout MRR/nDCG không giảm, Recall@5 drop ≤0,5 điểm %; FPR ≤1%, violations=0 |
| M7 | Hard p50 ≤500 ms, p95 ≤1.000 ms, p99 ≤2.000 ms; timeout ≤0,5%, timeout fallback ≤1%, error/queue-overflow failures=0; RSS ≤75% RAM; capacity + live HTTP/LLM đủ profiles |
| M8 | ≥50 adversarial cases, đủ 12 categories, toàn bộ PASS; FPR ≤1%; provenance/scope/invalid citation=0; required grounding tests không fail/skip |
| M9 | Đủ required faults và probes; fallback đúng Phase 6; permanent failure đóng provider, zero new inference; permits/resources không rò |
| M10 | Rollback ≤300 s qua hai PID và shared cache; zero new inference sau disable; Phase 6 outputs đúng; index không rebuild/thay bytes |
| M11 | Canary 0/1/5/10/25%, ba healthy windows mỗi bước, ≥100 requests/window: ≥15 windows/1.500 requests; đủ tám rollback exercises; telemetry tái tính và đạt budgets |
| M12 | Full suite/coverage ≥85%, required live tests chạy thật; checks/clean tree/archive/physical bindings hợp lệ; toàn bộ 19 gates PASS, score 10.0 |
| S1 | Lineage/canonical/splits/review/raw hashes nhất quán; held-out không có unresolved exposure/leakage; không giả review |
| S2 | Context/selection/scope/cache đúng; zero request-path model load; warm fail giữ Phase 6; lifecycle/permits đúng |
| S3 | Paired connected-group bootstrap ≥10.000 resamples, seed khóa; mỗi primary held-out split ≥10 independent groups theo validator; human-test CI95% ΔMRR lower>0; thiếu lực thống kê ghi thiếu evidence |
| S4 | Mỗi primary human-test/human-holdout: citation precision ≥98%, groundedness ≥98%; citation precision không giảm so Phase 6; accuracy/citation recall drop ≤0,5 điểm %; answer FPR ≤1% |
| S5 | All-gold@5 overall và hard/multi-hop không giảm trên primary held-out; mọi claim multi-hop được trả có đủ hop support |
| S6 | Raw stages/resources/successful throughput đầy đủ, deployment identity đúng; HTTP p95 budget khóa trước F1, mặc định 10 s, không vượt ceiling 20 s |

Phân biệt query hit Recall@k, all-gold query coverage và gold-chunk evidence recall. Báo positive ranking riêng negative FPR; retrieval FPR khác answer FPR; positive abstention vẫn là lỗi chất lượng. Không lấy câu trả lời rỗng để làm đẹp groundedness.

M1 là minimum, không ép thêm câu chỉ để tăng tổng số. Cần đủ independent groups và các strata thật trong từng split. FPR≤1% quan sát không chứng minh FPR quần thể≤1%; nếu bổ sung mục tiêu one-sided upper CI95%≤1% thì cần ít nhất 299 negative độc lập khi 0 lỗi. Stress set đó phải tách primary và không nhân mẫu bằng lặp câu.

## 4. Các task chuẩn bị — mở đường cho successor

### P7-01 — Chốt audit hiện trạng, baseline và ledger

**Ưu tiên P0 · Owner: release engineer · Phụ thuộc: không · Ước lượng: 0,5–1 ngày.** Có audit cũ; cần refresh với tree và artifacts hiện tại.

**Đầu vào:** `plan.md`, active selector, Git status, historical cycles/locks, Phase 6 manifests và index archives.

- [ ] P7-01.1 Ghi snapshot tree; phân loại tracked/untracked, code/data/docs/evidence và source của từng study.
- [ ] P7-01.2 Inventory toàn bộ 19 gates: cycle/source/runtime/index/model, report/raw/checksum, PASS lịch sử hay conditional.
- [ ] P7-01.3 Bảo toàn r18 failed M2, r15 M6, các route locks đã tiêu thụ và historical Phase 6. Xác minh archive/restore index gốc và index 14 documents riêng.
- [ ] P7-01.4 Tạo ledger 20 tasks, blocker list và dependency map; chốt target ban đầu local RTX 4060 nếu vẫn phù hợp evidence.

**Bàn giao:** `R/completion_task_ledger.json`, `R/completion_evidence_inventory.json`, `R/baseline_restore_audit.json`, snapshot status/raw và checksum manifest.

**Chuẩn đạt:** truy ngược được report về raw/identity; không gán lại PASS cũ cho cycle mới; baseline/index cũ giữ nguyên bytes; mọi blocker có next action. **Kiểm chứng:** kiểm tra hashes, restore thử vào directory riêng, validator M0 của cycle lịch sử với đầy đủ đường dẫn. **Khi fail:** phục hồi artifact hoặc ghi historical-unverified, chưa sử dụng làm release evidence.

### P7-02 — Hoàn thiện source schema và kiểm tra gói dev 889 câu

**P0 · Owner: data/retrieval engineer · Phụ thuộc: P7-01 · 1–2 ngày.** Schema/dev packet đã tồn tại; cần review, integration và đóng các lỗi trước F1.

**Đầu vào:** `source_course_generation.py`, generator/intake/freezer, packet 889 câu, index mở rộng và policy/authorization.

- [ ] P7-02.1 Đối chiếu course-code/name/credit với đúng column role, chunk/page/header; giữ wrapped/bilingual aliases và year metadata theo nguồn. Không suy cohort Mechanics từ năm URL 2019.
- [ ] P7-02.2 Recompute source facts/absence proof trên toàn bộ documents trong scope, bind physical index và source-bank hash; review nghĩa của negative, không suy absence toàn trường.
- [ ] P7-02.3 Verify từng qid, authorship, authorization, exported question bytes, group/review; không biến owner self-review thành independent review.
- [ ] P7-02.4 Replay 817 inherited rows + 72 source rows; giữ 889 câu `dev_only`; kiểm tra mọi attempted test/holdout reassignment bị reject.
- [ ] P7-02.5 Regenerate summary deterministic; tích hợp cùng contract vào intake/freezer/owner generation, giữ correction log nếu metadata đổi.

**Bàn giao:** reviewed dev packet, schema/integration report, source proof audit, deterministic summary và tests liên quan.

**Chuẩn đạt:** row/review errors=0; hash/identity khớp; source fields không bị đoán; dev-only không thể lọt vào held-out; không tự đổi `release_eligible=false`. **Kiểm chứng:** `test_source_course_generation.py`, dev inheritance/owner-generation/integrity tests và generator replay. **Khi fail:** giữ câu lỗi pending/quarantined kèm reason; sửa schema trước model study.

### P7-03 — Review exposure và tạo đủ nhóm mới cho successor

**P0 · Owner: data curator + reviewer thực tế · Phụ thuộc: P7-01/02 · 2–4 ngày, thêm thời gian tìm nguồn nếu thiếu groups.** Đây là blocker dữ liệu chính.

**Đầu vào:** mọi exposure inventories/history, 47 proposals lịch sử, dev packet mới, source facts/PDF previews, owner policy.

- [x] P7-03.1 Screen lại tất cả lịch sử hiện có, gồm 72 câu source-dev mới; normalize code/name/aliases và review semantic overlap, không chỉ regex.
- [x] P7-03.2 Gom connected families theo source question, paraphrase, template/evidence dependency thực tế; ghi rationale. Chung PDF không tự động cùng group, đổi ngôn ngữ/template không tự tạo group độc lập.
- [x] P7-03.3 Lập gap report cho dev/test/holdout: positive/negative, easy/hard, exact-code, ambiguous/contextual, table/multi-hop/scoped/year/semester khi corpus hỗ trợ.
- [x] P7-03.4 Giữ toàn bộ known-exposed/inherited groups ở dev/research; đánh dấu sáu subject codes đã dùng dev cùng families phụ thuộc. Chỉ tiếp nhận held-out mới có source/history proof và review thực tế.
- [x] P7-03.5 Bổ sung nguồn/nhóm khi quota hoặc ≥10 independent groups mỗi primary held-out chưa đủ; không nhân paraphrases để lấp cỡ mẫu.
- [x] P7-03.6 Chuẩn bị gold evidence sets, scoped negatives, review audit, labels/rubric; khóa F0 split proposal và dev eligibility. Tuning team không xem per-qid held-out outputs.

**Bàn giao:** `B/successor_exposure_registry.json`, `R/successor_gap_report.json`, reviewed canonical staging/review sidecar/group rationale và F0 manifest.

**Chuẩn đạt:** 0 cross-split connected groups; 0 unresolved held-out exposure; source/schema/review valid; strata/counts đủ M1/M2/M4/S3/S4. Không tuyên bố 47 proposals đều fresh. **Kiểm chứng:** history/exposure audit, split preflight, lineage/tamper tests, reviewer sign-off. **Khi fail:** thêm nhóm/nguồn thật hoặc giữ BLOCKED, không chuyển dev-only sang held-out.

P7-03 review update 2026-10-04: P7-03.1-.4 complete for the 53 source rows/42 connected groups. The owner-authorized review scanned all 31,513 history questions (0 exact code/name matches), examined pinned cross-encoder top candidates, kept 9 thesis/project/practice or adjacent project-family groups in dev/research, and proposed atomic assignments of 12 test/11 holdout/10 dev eligible groups. Codex is identified as analyst; no independent reviewer is claimed. The active r18 split/exposure bytes have now passed local registry validation and an M0/M1 revalidation, and are sealed for audit by `p7-03_active-r18_f0_freeze.json`; this historical r18 audit freeze is not the successor F0 deliverable and is not release-eligible. The 10/12/11 dev/test/holdout fresh-group assignment now has owner-authorized sign-off; all 41 bound source rows resolve against the independently restored source index hash `40a3e711298fdb66cdd906b19ad84ab9565dd43badfed7caed4eef81a671bec6`. This is group-allocation approval only: no successor question rows or row-level gold/review registry exist, and these rows do not support contextual/ambiguous or temporal strata. Pairing separate course groups for hard sums reduces independent groups; do not pad with paraphrases. P7-03.5-.6 and successor F0 therefore remain BLOCKED, with no threshold exception. See `evaluation/results/phase7-completion-20261004/p7-03_artifact_manifest-v9.json`, `p7-03_source_group_allocation_signoff.json`, `p7-03_successor_source_capacity.json`, and `p7-03_gap_report.json`.
P7-03 source expansion update 2026-10-05: the official UET QH-2025 Robotics curriculum supplies 55 coded credit rows and 28 prerequisite rows. All 55 rows match the captured HTML, including blank prerequisite cells and physical PDF pages 4–7. The corrected seven-page snapshot was visually inspected, the evidence archive restores exact source facts, and 88 ingestion/source tests pass. Screening all 31,513 historical occurrences as 2,182 distinct questions yields 26 exposed rows, 14 conservative dev/research rows, 11 rows connected to previously approved families, and four new subject groups. The source-only owner-authorized allocation is now 11 dev/13 test/13 holdout, at most 37 groups before question dependencies; recoded/versioned subjects add zero independent groups. This returns P7-03 to IN_PROGRESS for question/gold construction; neither question-level quotas nor successor F0 are complete. Preserve all release thresholds. Current artifact entry point: `evaluation/results/phase7-completion-20261004/p7-03_artifact_manifest-v10.json`; source capture and replay details: `data/corpus/phase7_source_expansion/20261005/source_manifest.json`.


P7-03 completion update 2026-10-05: successor F0 is now complete and owner-authorized. The source/question packet contains 93 new questions and 804 consumed r18 questions inherited strictly to dev (829/35/33 dev/test/holdout); both primary splits retain 13 connected groups, positive/negative and positive easy/hard cases. Production row, review-audit and exposure-registry validators return zero errors. All 30 contextual inputs preserve their real user topic and frozen source coordinates; each of three dev folds contains absence/partial/sufficient support. The index is real offline-cache BGE-M3 CUDA for the five added/recurated sources, with all original ten document artifacts unchanged. F0 binds questions/groups/dev eligibility only; it is not F1 or a new M0/M2/S3/S4 PASS. The old per-split 120/130/150 grounding minima belong to Phase 5, while Phase 7 human retrieval minima and >=10 primary groups pass unchanged. Archive and all hashes: `evaluation/results/phase7-completion-20261004/p7-03_artifact_manifest-v11.json`. P7-09 continues on the locked successor dev; expanded-index baseline and live measurements remain F1 dependencies.

### P7-04 — Khóa validator, lineage và protocol thống kê

**P0 · Owner: evaluation engineer · Phụ thuộc: P7-02/03 · 1–2 ngày.** S1–S6 đã có code; cần chứng minh tích hợp đầy đủ trên successor.

- [ ] P7-04.1 Đối chiếu ngưỡng giữa plan/spec/validator; bổ sung assertion thiếu trước F1, giữ các ngưỡng đã chốt.
- [ ] P7-04.2 Test sửa raw/hash/source/split/review/proof, cross-group leakage, path traversal, nonfinite/missing denominator: validator fail closed.
- [ ] P7-04.3 Bind summary/canonical/export/review/index/model/receipts; kiểm tra mixed human/owner-directed AI provenance đúng policy hiện có.
- [ ] P7-04.4 Khóa metric definitions, strata, connected-group bootstrap 10.000 lần, seed, minimum groups và insufficient-power behavior; khóa cách xử lý zero baseline/empty answers.

**Bàn giao:** validator gap matrix, protocol thống kê phiên bản hóa, regression XML và source patch nếu cần. **Chuẩn đạt:** 19 gate đều enforce bằng code/raw checks; tamper không PASS; synthetic smoke chỉ kiểm tra harness, không chứng minh quality. **Kiểm chứng:** benchmark/evidence/completion-contract tests và recompute từ fixtures có expected semantics. **Khi fail:** sửa validator/protocol trước F1.

### P7-05 — Kiểm chứng retrieval/context/scope/cache trên corpus mở rộng

**P0 · Owner: retrieval engineer · Phụ thuộc: P7-02; dùng dev hợp lệ của F0 · 1–2 ngày.** Trọng tâm code: `index_builder.py`, `hybrid.py`, `table_links.py` và query context.

- [ ] P7-05.1 Verify physical manifests, stable doc/chunk/page metadata và atomic index snapshot; index lỗi/thiếu/changed file bị phát hiện.
- [ ] P7-05.2 Đo candidate hit/all-gold trên dev 889 câu theo strata; linked table, semester, full course name và exact-code giữ provenance/scope; candidate pool≤40.
- [ ] P7-05.3 Test selected text/history/program/year/doc filters, bilingual/wrapped names, ambiguous exact-code; clarification đúng và không rò evidence ngoài scope.
- [ ] P7-05.4 Audit cache key gồm context/scope/index/route/model/evidence/answer identity; đổi document/version/config không tái dùng câu trả lời sai.
- [ ] P7-05.5 Nếu tối ưu candidate/ordering, dùng dev-only ablation; giữ failure buckets và source snapshots. Không dùng r18 held-out misses để tuning successor rồi tái nghiệm thu r18.

**Bàn giao:** `R/dev_candidate_coverage.json`, context/cache audit, raw per-qid dev outputs và regression evidence. **Chuẩn đạt:** dev candidate hit/all-gold≥95% theo strata, errors=0; contracts S2 đạt bằng tests/pilot; không biến pilot thành M2 chính thức. **Kiểm chứng:** dev candidate CLI, retrieval/index/context/selection tests. **Khi fail:** sửa retrieval/gold sai có proof trước F1, không làm đẹp aggregate bằng bỏ strata.

### P7-06 — Hoàn thiện rubric và pilot answer/citation với LLM thật

**P0 · Owner: grounding/evaluation engineer + semantic reviewer · Phụ thuộc: P7-03/04/05 · 1–2 ngày + review/quota.**

- [ ] P7-06.1 Khóa gold claims, evidence sets/hop support, citation coordinates và rubric từ source, trước xem outputs; phép cộng tín chỉ qua deterministic path.
- [ ] P7-06.2 Pilot paired Phase 6/7 trên dev, cùng LLM/prompt/context budget/provider params; cache tắt cho quality, lưu usage và token/cost có nguồn.
- [ ] P7-06.3 Semantic review từng factual claim/citation theo role thực tế; output pending không được tự thành reviewed/PASS.
- [ ] P7-06.4 Recompute accuracy, citation precision/recall, groundedness, answer FPR, false abstention, all-hop support; check answer rỗng không né denominator.
- [ ] P7-06.5 Kiểm tra hai live integration tests và quota hiện tại; khóa retry/provider-repeat/cost ceiling. Missing usage ghi unknown; quota failure giữ raw và blocker.

**Bàn giao:** dev rubric/protocol, `R/raw/dev_paired_answers.reviewed.json`, pilot quality/cost report. **Chuẩn đạt:** pilot đạt hướng S4/S5, metrics tái tính được; uncached live call có evidence, reviews traceable. **Kiểm chứng:** paired-answer/grounding tests + pilot thật. **Khi fail:** sửa prompt/context/evidence trên dev trước F1; quota không đủ thì chuẩn bị phần offline và chặn acceptance phụ thuộc live.

P7-06.2 instrumentation update 2026-10-04: the paired collector now archives the exact selected evidence context passed to each provider call, with UTF-8 SHA-256 for both context and full prompt. It records attempted/completed/failed calls and preserves an application-level failed-attempt artifact without exception text. Contract tests passed. A reproducible source-binding audit separately confirms all 315 active-r18 dev positives reference existing, matching physical-index chunks, while 135 rows have neither a separate expected answer nor expected claims. This is a binding check, not semantic approval. These offline improvements do not satisfy the live paired pilot, claim/gold review, usage/cost receipt, or P7-06 acceptance. See `evaluation/results/phase7-completion-20261004/p7-06_prompt_capture_validation.json`, `p7-06_artifact_manifest-v1.json`, `p7-06_dev_claim_input_audit.json`, and `p7-06_dev_claim_input_manifest-v1.json`.

### P7-07 — Startup readiness, singleton và lifecycle

**P0 · Owner: runtime engineer · Phụ thuộc: P7-01; đóng trước F1 · 0,5–1,5 ngày.**

- [ ] P7-07.1 Audit `disabled/loading/warming/ready/failed/closing`; admission Phase 7 chỉ sau warm thành công đúng identity.
- [ ] P7-07.2 Probe snapshot thật: load một lần/process, concurrent init không duplicate, first request không cold-load; startup timeout riêng request budget.
- [ ] P7-07.3 Warm failure/timeout/revision mismatch giữ Phase 6; shutdown/disable cancel queued work và quản lý in-flight native work.
- [ ] P7-07.4 Repeated start/stop, late completion, permanent disable không rò provider/permits/resources.

**Bàn giao:** lifecycle/startup raw probes, readiness report, runtime tests; patch nếu audit phát hiện lỗi. **Chuẩn đạt:** zero request-path load; singleton count đúng; warm fail không admission rerank; permits chỉ trả khi native work kết thúc. **Kiểm chứng:** lifecycle/runtime tests + GPU dev probe; formal identity ở M3. **Khi fail:** sửa lifecycle trước freeze, giữ Phase 6 phục vụ.

### P7-08 — Telemetry và deployment protocol có thể tái tính

**P1 bắt buộc · Owner: runtime/observability engineer · Phụ thuộc: P7-05/07 · 1–2 ngày.**

- [ ] P7-08.1 Trace route-selected/inference-attempted/completed/applied/policy-abstention/provider-fallback riêng; request ID và reason code chuẩn.
- [ ] P7-08.2 Ghi monotonic durations cho queue/retrieval/inference/LLM/grounding/serialization/transport; UTC timestamps, PID/children, scope và identities.
- [ ] P7-08.3 Thu RSS/CPU/VRAM allocated/reserved/peak/capacity/queue thật; khóa sampling interval, reset peak và cold/warm protocol.
- [ ] P7-08.4 Reconcile accepted/rejected/timeout/failed/completed/in-flight; throughput chỉ đếm successful completions.
- [ ] P7-08.5 Khóa target RAM/VRAM/OS/runtime/device/limits, concurrency workloads và HTTP p95 SLO; pilot không chứa key/secret.

**Bàn giao:** telemetry schema/protocol, raw pilot/resource observations, recompute report và deployment profile. **Chuẩn đạt:** counters khớp raw, duration≥0, resource đúng device/PID; đủ dữ liệu để S6 enforce. **Kiểm chứng:** sampler/measurement/HTTP/canary semantic tests. **Khi fail:** sửa collectors trước F1, không ghép số đo khác target.

### P7-09 — Joint dev feasibility và chứng minh triển vọng uplift

**P0 · Owner: retrieval/evaluation engineer · Phụ thuộc: P7-03–08 + F0 · 3–6 ngày/study.** Đây là checkpoint kỹ thuật chính trước tiêu thụ held-out mới.

- [ ] P7-09.1 Reproduce Phase 6 trên dev mới cùng physical index; báo distinct old-dev/new-source-dev và groups, không suy từ study 491 câu/index cũ.
- [x] P7-09.2 Ablation có kiểm soát: candidate/subset ordering, table window/truncation, route, model/input format, dtype/batching, cap và evidence policy; giữ raw/failures từng config.
  Evidence update 2026-10-04: completed dev-only candidate/subset and ordering replay plus the recorded table, route, model/input-format, dtype/batch, cap, and evidence-policy ablations. The named_curriculum_rows pool exactly reproduces all 889 old P7-09 candidate lists; existing_code_rows matches 569/889. Rescored both pools with the pinned CUDA body-input model (18,873 pairs each). At cap40/weight0.5, named curriculum: Recall@5 96.36%, MRR +10.65%, nDCG@5 +7.85%, all-gold@5 93.94%; existing-code: 91.11%, -13.76%, -10.37%, 88.69%. Both negative FPR 9.39%. This same-dev comparison is diagnostic, not independent confirmation. See `evaluation/results/phase7-completion-20261004/p7-09-named-curriculum-pool-ablation.json`, score gz files, and refreshed `p7-09_run_audit.json`. P7-09.3-.6 and the overall P7-09 remain blocked.
- [ ] P7-09.3 Fit route dev với grouped OOF; probability evidence đủ absence/partial/sufficient và đủ support từng fold; primary metrics tách auxiliary exploratory.
  Successor update 2026-10-05: the unchanged Phase 6 parameters have been measured on all 140 original dev inputs against the new 15-document index. Recall@5 is 109/126 (86.51%), negative FPR 0/14, and recall is 4.76 percentage points below historical dev. The within-index threshold applicability constraints pass without refitting, but this is not historical baseline retention or M0 PASS. Evidence: `evaluation/results/phase7-completion-20261004/p7-09_successor_phase6_qualification_audit.json`. The separate 829-row F0 dev baseline/candidate measurement is in progress; no successor test/holdout inference has run. New contextual scores must use the exact resolved retrieval query, and the old index/input scores cannot be transferred to this packet.
  Measured successor update 2026-10-05: the first 829-row dev measurement completed with Recall@5 98.31%, all-gold@5 96.41%, candidate all-gold@40 99.37%, zero provenance/scope/duplicate errors, and FPR 9/356 (2.53%, FAIL versus <=1%). New-source dev alone is 25 rows/11 groups, with Recall@5 13/14 and FPR 8/11; do not hide this behind the 804 consumed-parent dev rows. Real uncached body-input BGE reranker scores cover all 829 requests (479 nonempty inference calls plus one warmup, score-cache hits zero), CUDA FP32/batch8/512. Native-pool ranking-only trials degrade MRR. Baseline-priority ordering replay, with three connected-group outer folds and train-only selection, produces only +0.15% MRR/+0.18% nDCG and retains the failing FPR. This does not satisfy joint feasibility or the +3% checkpoint. Evidence: `p7-09_successor_dev_measurement_audit.json`, `p7-09_successor_candidate_ceiling_and_failures.json`, `p7-09_successor_body_ranking_report.json`, and `p7-09_successor_order_grouped_oof.json` under `evaluation/results/phase7-completion-20261004`. A source-guard regression was reproduced: QH-2025 was treated as a missing course code. Cohort classification and source-backed exam appointment checks are fixed with 118 passing regression tests; full dev remeasurement is in progress. Prior failed measurements remain immutable.
- [ ] P7-09.4 Với cùng config, đo Recall@5/all-gold/MRR/nDCG/FPR/latency/timeout/resources; không ghép quality cap20/FP32 với latency cap8/FP16.
- [ ] P7-09.5 Kiểm tra mục tiêu +3% trên dev OOF và nhóm mới, cùng CI/ceiling/failure analysis; study cũ +0,35%/+0,28% chưa đáp ứng checkpoint này.
- [ ] P7-09.6 Chọn ít nhất một config đồng thời đạt route 95%/20%, Recall@5≥95%, FPR≤1%, p95≤1 s, timeout≤0,5%, invalid/errors=0 và pilot S4/S5; khóa cap-selection protocol và shortlist trước F1.

**Bàn giao:** `R/joint_dev_feasibility.json`, `R/joint_dev_acceptance_plan.json`, ablation/failed-attempt archive, candidate config và decision record.

**Chuẩn đạt:** config jointly feasible trên dev; MRR/nDCG OOF đạt hướng +3% và evidence completeness không suy giảm, hoặc phân tích cụ thể lý do chưa đủ. Điều kiện uplift dev là checkpoint kế hoạch, không thay M6 held-out gate. **Kiểm chứng:** replay raw với groups/seeds/config identity; reviewer xác nhận không dùng held-out tuning. **Khi fail:** tiếp tục dev study/thu đúng gap, chưa F1 và chưa mở held-out mới.

## 5. Các task nghiệm thu — đúng cycle, đúng thứ tự gate

### P7-10 — Tạo và freeze successor, đóng M0/M1/S1

**P0 · Owner: release engineer + data reviewer · Phụ thuộc: P7-01–09 đạt chuẩn · 1–2 ngày.**

- [ ] P7-10.1 Chốt successor ID/paths mới, source commit sạch, runtime/dependencies/model snapshot và physical index; review mọi thay đổi hiện có trước commit.
- [ ] P7-10.2 Giải quyết tương thích M0 với index mở rộng: preserve historical RC3, reproduce hai rerun theo contract hiện hành. Nếu index mở rộng đổi baseline outputs, xử lý design/baseline protocol trước F1; không overwrite historical hay đổi floor để PASS.
- [ ] P7-10.3 Export canonical/splits/review/generation/inheritance/exposure theo F0; union/disjoint groups đúng, held-out eligibility rõ, generated primary profile khai báo đúng.
- [ ] P7-10.4 Freeze F1 gồm rubric/seed/SLO/cap-selection/workload; chạy baseline và human-freeze, build S1; archive raw/receipts.
- [ ] P7-10.5 Chỉ cập nhật active selector và roadmap khi successor đủ preflight; mọi lệnh trước đó truyền explicit paths.

**Bàn giao:** `R/retrieval_baseline_manifest.json`, `R/retrieval_baseline_comparison.json`, `R/human_benchmark_manifest.json`, `R/human_benchmark_review.json`, `R/reranker_lineage.json`, F1 manifests và benchmark bytes.

**Chuẩn đạt:** M0/M1/S1 PASS trên successor; source/index/raw bindings đúng; partial score vẫn null. **Kiểm chứng:** validator `--through M1` với successor paths. **Khi fail:** giữ successor chưa release; chữa input/protocol và refreeze hợp lệ trước exposure, không nhập report r18 thay báo cáo mới.

### P7-11 — Candidate coverage M2 và model/provider M3/S2

**P0 · Owner: retrieval/runtime reviewer · Phụ thuộc: M0/M1/S1 PASS · 1–2 ngày.**

- [ ] P7-11.1 Đo cap40 trên generated + primary human dev/test/holdout; lưu candidates per-qid và recompute hit/all-gold/evidence recall theo strata.
- [ ] P7-11.2 Ghi exposure M2, giữ khóa purpose; mọi scope/provenance/duplicate lỗi phải bằng 0, không chỉ aggregate coverage đẹp.
- [ ] P7-11.3 M2 PASS mới chạy model workflow chính thức: snapshot local pinned, offline CUDA/device/dtype/options thống nhất; score delta≤1e-5.
- [ ] P7-11.4 Provider-contract fault injections, real startup/singleton/warm probes; collect context/selection/cache/lifecycle raw đúng source/M3 identity.

**Bàn giao:** `R/candidate_coverage.json`, `R/model_snapshot_smoke.json`, `R/reranker_provider_contract.json`, `R/reranker_context_lifecycle.json`, raw và receipts.

**Chuẩn đạt:** M2/M3/S2 PASS theo bảng; không rebind metadata vào observation cũ để giả đo mới. **Kiểm chứng:** coverage recompute và validator `--through M3`. **Khi fail M2:** giữ failed report/exposure; quay dev research, successor held-out khác nếu sửa config. **Khi fail M3/S2:** phân biệt infrastructure retry cùng identity với thay source/model làm invalidation downstream.

### P7-12 — Fit và freeze hard routing, đóng M4

**P0 · Owner: routing reviewer · Phụ thuộc: M3/S2 PASS · 0,5–1 ngày.**

- [ ] P7-12.1 Fit dev-only trên runtime features shared với serving; qid/gold/difficulty/template/language labels không lọt vào features.
- [ ] P7-12.2 Grouped OOF chọn threshold, final refit đạt 95% hard recall/≤20% easy thừa; verify exact/abstained/single-candidate bypass theo runtime contract.
- [ ] P7-12.3 Freeze F2 trước route test/holdout, bind source/M3/benchmark/dev/groups; dùng lock mới, không reuse r17 lock.
- [ ] P7-12.4 Đo held-out một lần theo protocol; hard≥90%, easy thừa≤25%, coverage denominator đầy đủ; ghi exposure.

**Bàn giao:** `R/hard_query_route_calibration.json`, `R/hard_query_route_confusion.json`, `R/reranker_route_freeze.json`, raw OOF/refit/held-out.

**Chuẩn đạt:** M4 PASS, no feature leakage, immutable F2 bindings đúng. **Kiểm chứng:** serving/evaluation route parity và validator `--through M4`. **Khi fail:** không sửa consumed lock; giữ fail, về dev và successor theo exposure rules.

### P7-13 — Five-cap sweep và probability evidence, đóng M5

**P0 · Owner: calibration reviewer · Phụ thuộc: M4 PASS · 1–2 ngày.**

- [ ] P7-13.1 Đo đủ cap 8/10/12/16/20 cùng model/input/route/source identity trên dev; lưu scores/candidates/latency/timeouts/invalids từng trial.
- [ ] P7-13.2 Fit probability ba lớp absence/partial/sufficient, grouped OOF rồi final refit; verify đủ class/fold support và primary negative denominators.
- [ ] P7-13.3 Tách exploratory auxiliary metrics; không dùng combined FPR làm primary, không dùng score-only policy thay probability release.
- [ ] P7-13.4 Chọn trong configs feasible theo objective validator hiện tại: MRR, rồi Recall, latency thấp, cap nhỏ; archive selection/tie-break và rejected trials.
- [ ] P7-13.5 Kiểm tra serving/evaluation evidence decisions identical; partial/uncertain/provider faults fallback đúng contract.

**Bàn giao:** `R/reranker_cap_sensitivity.json`, `R/reranker_score_calibration.json`, năm trial reports/raw, selected policy identity.

**Chuẩn đạt:** M5 PASS: Recall≥95%, FPR≤1%, invalid=0, p95≤1 s, timeout≤0,5%, rerank requests>0; OOF/fitted/raw checks đúng schema. **Kiểm chứng:** sweep CLI + validator `--through M5`. **Khi fail:** không chọn riêng cap10 feasibility cũ làm PASS; giữ cycle fail và trở về dev theo locks/exposure.

### P7-14 — Paired held-out ranking và answer/citation, đóng M6/S3/S4/S5

**P0 · Owner: quality reviewer + semantic reviewer · Phụ thuộc: M5 PASS · 2–4 ngày + quota/review.**

- [ ] P7-14.1 Freeze F3 trước quality collection: selected cap/policy, Phase6/7 configs, rubric/protocol/LLM params/context budget/provider-repeat plan.
- [ ] P7-14.2 Paired ranking trên generated/human test/holdout cùng qids/golds/scopes; per-query deltas, strata/regressions và all-gold/false abstention.
- [ ] P7-14.3 Group bootstrap ≥10.000 lần với seed khóa, báo independent groups và CI; không tăng chất lượng sample count bằng load repetitions.
- [ ] P7-14.4 Collect Phase6/7 answers uncached với LLM thật; lưu outputs/usage/cost/latency/errors và pending review. Review claims/citations/blind phase identity khi khả thi, adjudicate theo role khai báo đúng.
- [ ] P7-14.5 Recompute S3/S4/S5 riêng từng primary split; giữ failed experiments/exposure, không điều chỉnh gold/rubric sau output.

**Bàn giao:** `R/retrieval_quality_comparison.json`, `R/reranker_group_statistics.json`, `R/reranker_answer_quality.json`, `R/reranker_complete_evidence.json`, F3 lock và reviewed raw answers/ranking.

**Chuẩn đạt:** M6 + S3–S5 đồng thời PASS theo bảng; +3% là tương đối cho cả MRR/nDCG test; thiếu semantic review/live evidence hoặc subgroup là thiếu evidence. **Kiểm chứng:** `quality-collect` → semantic review → `quality`; validator `--through M6`. **Khi fail:** chặn performance acceptance, lưu toàn bộ fail; cải tiến trên dev rồi mở successor đúng protocol.

### P7-15 — Capacity, resources và HTTP/LLM thật, đóng M7/S6

**P0 · Owner: deployment/runtime engineer · Phụ thuộc: M6/S3–S5 PASS · 1–2 ngày.**

- [ ] P7-15.1 Khóa measured deployment profile đúng F1; cold-start/warm, model singleton, queue/admission/timeout/circuit limits như config sẽ bàn giao.
- [ ] P7-15.2 Chạy required capacity profiles, cap diagnostics và selected release cap; concurrency 1/5/10/20. Không thay selected cap/policy sau quality freeze.
- [ ] P7-15.3 HTTP end-to-end thật có uncached live LLM, ≥100 requests/mức concurrency, đủ easy/hard/negative/scoped; HTTP budget mặc định 10 s theo F1.
- [ ] P7-15.4 Thu routing/retrieval/queue/inference/LLM/grounding/serialization/transport, all-attempt/success distributions, errors/fallback/timeout, RAM/VRAM/CPU/throughput.
- [ ] P7-15.5 Recompute raw, check headroom RSS≤75% RAM; target local ghi rõ local, không tự nhận public-free-tier PASS.

**Bàn giao:** `R/reranker_performance.json`, `R/reranker_capacity.json`, `R/reranker_resource_budget.json`, `R/reranker_http_end_to_end.json`, `R/reranker_observability.json`, load/resource/HTTP raw.

**Chuẩn đạt:** M7/S6 PASS, p50/p95/p99 và failure/resource budgets đạt ở required selected-cap profiles; live LLM identity hợp lệ. **Kiểm chứng:** performance workflow và validator `--through M7`. **Khi fail:** lưu bottleneck/quota/resource report; thay runtime/config cần đánh giá invalidated quality/bindings và đo lại phần chịu ảnh hưởng.

### P7-16 — Adversarial và grounding regression, đóng M8

**P1 bắt buộc · Owner: security/grounding reviewer · Phụ thuộc: M7/S6 PASS · 1 ngày.**

- [ ] P7-16.1 Chuẩn bị ≥50 unique cases đủ 12 `CATEGORIES` từ evaluator; expected behavior/source scope được review trước chạy.
- [ ] P7-16.2 Bao phủ injection trong query/document, forged citation/provenance, wrong doc/year/program/scope/context/cache và malformed evidence theo category contract.
- [ ] P7-16.3 Run evaluator qua runtime frozen; lưu outputs/raw, negative FPR và mọi violations.
- [x] P7-16.4 Chạy required grounding/citation regressions; XML/hashes đầy đủ, không skip required cases.

P7-16.4 offline regression check passed on the current worktree: 133 tests passed, 0 failures/errors/skips; rerun after the provider shutdown fix also passed with the same counts. Validation: `evaluation/results/phase7-completion-20261004/p7-16_4_validation-v2.json`; JUnit: `evaluation/results/phase7-completion-20261004/p7-16-19-offline-contract-tests-current-v2.xml`. This closes only the required offline grounding/citation regression subtask; P7-16.1-.3, frozen-successor security evidence, M8, and the overall P7-16 remain blocked.

**Bàn giao:** reviewed adversarial JSONL, `R/reranker_security.json`, `R/reranker_grounding_regression.json`, raw + required test XML.

**Chuẩn đạt:** M8 PASS, toàn bộ attacks đạt expected behavior, FPR≤1%, leakage/invalid citation=0. **Kiểm chứng:** security workflow + validator `--through M8`. **Khi fail:** sửa boundary, lưu exploit reproduction và kiểm tra lại bindings/evidence bị ảnh hưởng.

### P7-17 — Controlled faults và recovery, đóng M9

**P1 bắt buộc · Owner: runtime reviewer · Phụ thuộc: M8 PASS · 0,5–1 ngày.**

- [x] P7-17.1 Inject toàn bộ required `FAILURES`: model/calibration missing/hash mismatch, timeout/queue full/OOM/provider exception, invalid score/ID/doc/page, empty output, cache/revision mismatch.

P7-17.1 offline injection completed: the isolated fault harness exercised all 15 required `FAILURES` and every required check returned true. Evidence: `evaluation/results/phase7-completion-20261004/p7-17-1-current-fault-injection.json` (runner itself remains `conditional` in exploratory mode because prior gates are absent). This is synthetic only; P7-17.2-.4 and overall P7-17/M9 still need target-runtime/device evidence.
- [x] P7-17.2 Probe before/after + follow-up counters; bổ sung late native completion/concurrent faults để chứng minh permit contract.
- [x] P7-17.3 Compare fallback retrieval ordered outputs/coordinates/content/scores với Phase 6 theo contract; không yêu cầu live LLM stochastic output giống từng byte.
- [x] P7-17.4 Permanent failure đóng provider/admission, follow-up zero new inference; transient recovery đúng trạng thái, Phase 6 không hỏng.

**Bàn giao:** `R/reranker_failure_matrix.json`, actual injection/follow-up observations. **Chuẩn đạt:** M9 PASS, required faults đủ, no permit/resource leak sau native completion. **Kiểm chứng:** faults workflow + validator `--through M9`. **Khi fail:** sửa runtime boundary và revalidate impacted source evidence, không bỏ fault khó.

P7-17.2 completed as a local CUDA component subtask (2026-10-04): pinned CrossEncoder inference on RTX 4060 ran concurrently with a queued caller; a controlled CUDA kernel completed after provider close. Timeout/close canceled only queued work, admission remained closed, no new inference started, the running permit stayed held, and both permits returned after drain. Evidence: `p7-17-2_validation.json`, especially `p7-17-2-current-cuda-native-kernel-late.json`. The injected kernel models late native completion and does not emulate a naturally hung model kernel or device fault.
P7-17.3/.4 completed as local/dev subtasks (2026-10-04): exact Phase 6 output equality passed for 20 dev groups with 22 timeout injections; 11 permanent controlled faults stopped follow-up inference; transient retry recovered; and an actual pinned CUDA provider rollback after a controlled post-inference fault closed admission, preserved Phase 6, and started zero follow-up inference. Evidence: `p7-17-3_validation.json`, `p7-17-4_validation-v2.json`, and `p7-17_artifact_manifest.json`. Overall P7-17/M9 remains blocked pending frozen-release-chain and production target-profile acceptance.
### P7-18 — Rollback hai process và shared cache, đóng M10

**P1 bắt buộc · Owner: operations reviewer · Phụ thuộc: M9 PASS · 0,5–1 ngày.**

- [ ] P7-18.1 Prepopulate shared answer cache bằng Phase7 outputs; snapshot namespace/hash/index và baseline probes.
- [ ] P7-18.2 Trigger disable, close admission/cancel queue, đổi policy/cache namespace; đo trigger→Phase6-ready bằng monotonic timing.
- [ ] P7-18.3 Chạy probes PID A, restart PID B cùng shared cache; lưu model call counters và outputs của hai process.
- [ ] P7-18.4 Check zero new inference sau disable, không reuse Phase7 cache, không rebuild index; in-flight cleanup đúng contract.

**Bàn giao:** `R/reranker_rollback.json`, two-PID probes/timing/cache/index hashes. **Chuẩn đạt:** M10 PASS, rollback≤300 s và fallback Phase6 đúng ở cả hai PID. **Kiểm chứng:** rollback workflow + validator `--through M10`. **Khi fail:** giữ Phase6, sửa admission/cache/lifecycle và đo lại rollback với identity hợp lệ.

### P7-19 — Staging canary và auto-rollback, đóng M11

**P0 · Owner: staging/deployment owner · Phụ thuộc: M0–M10/S1–S6 PASS · 1–2 ngày.**

- [ ] P7-19.1 Khởi động staging cô lập đúng frozen source/runtime/limits; deterministic assignment và environment ID.
- [ ] P7-19.2 Chạy 0→1→5→10→25%; mỗi bước ba healthy windows≥100 requests, đủ eligible easy/hard trong selected cohort và negative/scoped.
- [ ] P7-19.3 Lưu ≥15 windows/1.500 requests với assignment/route/inference/applied rates riêng; resources/stages/latency/FPR/fallback/errors tái tính.
- [ ] P7-19.4 Thực đo tám rollback triggers: provenance, scope, citation, timeout, FPR, error regression, memory, latency ba windows liên tiếp; lưu fault + follow-up telemetry.
- [ ] P7-19.5 Auditor recompute decisions, provider shutdown/zero-new-inference/fallback Phase6; chỉ promote bước sau khi đủ healthy windows.

**Bàn giao:** `R/reranker_staging.json`, `R/canary_observations.json`, raw healthy/fault windows, deployment sign-off.

**Chuẩn đạt:** M11/S6 PASS; p95≤1 s/p99≤2 s, FPR/timeout≤1%, hard coverage≥90%, easy thừa≤25%, RSS≤75% RAM, scope/citation/provenance=0 và không error regression. **Kiểm chứng:** staging collect → staging audit → validator `--through M11`. **Khi fail:** auto-rollback, preserve telemetry; public runtime khác target phải có measured cycle/profile tương ứng.

### P7-20 — Release bundle, clean reproduction và bàn giao 10/10

**P0 · Owner: release owner + reviewer · Phụ thuộc: tất cả task/gate trước đạt chuẩn · 1–2 ngày.**

- [ ] P7-20.1 Archive source/runtime/dataset/splits/reviews/history/index/model/policies/locks/receipts/raw/failed attempts; manifest/checksums/locator + exact restore commands.
- [ ] P7-20.2 Sync `plan.md`, progress, task spec/release plan/runbook/README theo evidence mới; phân biệt history với current, giữ roadmap tracked ở root.
- [ ] P7-20.3 Chạy full suite coverage≥85%, compile/diff/secret/link checks phù hợp repo; hai live LLM integration tests thật và required gate tests không skip. Lưu XML/coverage/exit codes, không lưu credentials.
- [ ] P7-20.4 Commit source/evidence theo quy trình repo; restore trong clean checkout bằng pinned runtime/model/physical index; verify raw hashes và recompute metrics.
- [ ] P7-20.5 Recheck M0–M12/S1–S6 và physical model bằng validator/release workflow; output final readiness/manifest ở path được phép để không làm dirty tree hay overwrite raw evidence.
- [ ] P7-20.6 Handoff activation config, health/readiness/fallback/rollback commands, measured target scope, known limitations và owner/reviewer kết luận.

**Bàn giao:** `R/reranker_release_manifest.json`, clean-checkout verification/readiness, release archive/checksums, runbook và handoff note.

**Chuẩn đạt:** **19/19 PASS**, `status=pass`, `score=10.0`, `all_release_gates_pass=true`; clean tree, model/index bindings đúng; người khác restore/tái tính được từ bundle. Release manifest chỉ nghiệm thu đúng profile đã đo. **Kiểm chứng:** full checks + `release_workflow validate/release --model-dir <pinned-snapshot>` trong clean tree. **Khi fail:** giữ score null/chưa release, sửa artifact hoặc đo lại phần invalidated; không tự tuyên bố 10/10 từ checklist Markdown.

## 6. Thứ tự thực hiện và lịch dự kiến

| Chặng | Tasks | Đầu ra cho phép mở chặng kế | Thời gian định hướng |
|---|---|---|---|
| A — Audit/data | 01 → 02 → 03 → 04 | History cập nhật, dev hợp lệ, đủ fresh groups, F0/protocol | 4–8 ngày kỹ thuật + review/tìm nguồn |
| B — Dev readiness | 05 → 06/07/08 → 09 | Retrieval/context/runtime/harness đạt, joint dev config khả thi và triển vọng +3% | 5–9 ngày + quota/study lặp |
| C — Freeze/ranking/answers | 10 → 11 → 12 → 13 → 14 | M0–M6/S1–S5 PASS đúng F1/F2/F3 | 5–9 ngày + semantic review |
| D — Performance/reliability | 15 → 16 → 17 → 18 | M7–M10/S6 PASS đúng target | 3–5 ngày |
| E — Staging/package | 19 → 20 | M11/M12 và đủ 19 gate, bundle khôi phục được | 2–4 ngày |

Các khoảng là **ước lượng**, không phải deadline hay tổng công đã cam kết. Với một người thực hiện, nên dự trù khoảng **4–7 tuần**, tăng thêm nếu thiếu fresh independent groups, quota LLM hoặc cần mở successor sau gate FAIL. P7-07 có thể làm sớm khi dữ liệu đang review; task acceptance vẫn đi đúng gate order. P1 không được bỏ để rút lịch.

### 6.1. Backlog cần bắt đầu ngay

1. **P7-01:** refresh inventory/tree và cố định official status r18 3/19; phân loại packet mới chưa freeze.
2. **P7-02:** review/integrate schema + 889 dev packet trên đúng expanded index, bổ sung history cho sáu subjects đã dùng.
3. **P7-03:** rescreen proposals, xác định số independent groups thực sự còn đủ eligibility và gap cho hai held-out splits; thu thêm nguồn nếu cần.
4. **P7-05/P7-09:** chạy dev coverage → grouped route/evidence + ranking uplift study trên packet mới; chưa mở held-out.
5. **P7-06–08:** hoàn thiện live answer pilot/runtime/telemetry và khóa deployment/SLO; chỉ F1 khi cả data và joint dev readiness đạt.

### 6.2. Các rủi ro có hành động rõ ràng

| Rủi ro thực tế | Điểm phát hiện | Hành động / điều kiện thoát |
|---|---|---|
| Proposal đã exposed qua alias/template/source family | P7-03 | Đưa group về dev/research, thu nhóm độc lập; history reviewer ký kết luận |
| Dev có nhiều câu nhưng ít groups/classes/fold support | P7-03/09 | Báo counts theo group/class; bổ sung đúng gap, không thêm paraphrase để tăng n |
| MRR/nDCG uplift yếu dù route/FPR tốt | P7-09 | Dev ablation input/subset/model và ceiling analysis; chưa tiêu thụ fresh held-out |
| Index mở rộng làm M0/historical reruns mất tương thích | P7-10 preflight | Review baseline/index protocol trước F1; giữ historical immutable và đủ hai rerun theo contract |
| Source hoặc M3 đổi làm route freeze invalid | P7-10–14 | Đóng source trước acceptance; map invalidation; không sửa consumed F2 lock |
| Live LLM quota/uncached measurement không đủ | P7-06/14/15 | Probe quota, khóa workload/cost, lưu failure thật; offline tests không thay live acceptance |
| GPU local PASS nhưng public RAM/latency khác | P7-08/15/19 | Ghi measured scope local; nghiệm thu profile public riêng trước tuyên bố public PASS |
| Raw chỉ nằm `.tmp` hoặc CRLF/Git đổi provenance bytes | P7-01/20 | Exact-byte archive/checksums, serialization rules đúng phạm vi, restore verification |

## 7. Lệnh kiểm chứng và checklist đóng phase

Các CLI dưới đây đã có trong repo; trước chạy đo phải đọc `--help`, truyền explicit successor paths/model/device và theo preconditions của task. Phần này không tạo benchmark hay gọi LLM trong lần lập kế hoạch.

```powershell
# Đọc interface, không đo quality/held-out.
.venv/Scripts/python.exe -m scripts.phase7_release_pipeline --help
.venv/Scripts/python.exe -m evaluation.reranker.validate_reranker_release --help

# Preflight successor, điền paths thật đã chốt ở P7-03/P7-10.
.venv/Scripts/python.exe -m scripts.phase7_release_pipeline preflight --benchmark-dir <B> --results-dir <R> --index-dir <I>

# Research trên dev-only; đọc --help và truyền options cần thiết.
.tmp/phase7-gpu-runtime/Scripts/python.exe -m scripts.benchmarks.measure_phase7_dev_candidates --help
.venv/Scripts/python.exe -m scripts.benchmarks.refit_phase7_dev_route --help

# Acceptance checkpoint, thay M1 bằng milestone tương ứng khi prerequisites đạt.
.venv/Scripts/python.exe -m evaluation.reranker.validate_reranker_release --through M1 --benchmark-dir <B> --results-dir <R> --index-dir <I>

# Full regression ở P7-20; live tests phải cấu hình/gọi thật theo contract repo.
.venv/Scripts/python.exe -m pytest --cov=src/campusai --cov-report=term-missing --cov-report=json:<verification-dir>/coverage.json --junitxml=<verification-dir>/tests.xml
git diff --check
git ls-files --error-unmatch plan.md
git status --short
```

`<B>`, `<R>`, `<I>`, `<verification-dir>` là placeholders cần thay, không paste nguyên vào PowerShell. Interpreter GPU dùng cho model measurements; CPU test interpreter không được thay model identity đã freeze. CLI cấp thấp dùng defaults có thể trỏ r18/results root: luôn kiểm tra paths trước khi chạy. Không dùng `--exploratory` để tạo release PASS.

- [ ] M0–M12/S1–S6 đều PASS trong cùng release chain hợp lệ, không thiếu gate và không manual override.
- [ ] Test/human-holdout đủ fresh eligibility, reviews thật, origin rõ; exposure/locks/failures được giữ.
- [ ] M6 uplift/CI và S4/S5 đạt từng split; có uncached LLM evidence và semantic review.
- [ ] M7/M11 đạt target RAM/VRAM/latency/HTTP SLO; faults/rollback/canary raw tái tính được.
- [ ] Clean checkout restore được dataset/index/model/raw, metric summaries đúng hashes.
- [ ] Full checks/coverage≥85%, required live tests không skip; source/runtime/data/route/evidence/LLM bindings hợp lệ.
- [ ] Final validator `status=pass`, `score=10.0`, `all_release_gates_pass=true`; release bundle/runbook/handoff đầy đủ.
- [ ] `plan.md` vẫn ở repository root và tracked; roadmap/progress trỏ đúng successor evidence và ghi rõ measured deployment scope.

Nếu còn một mục chưa đạt, Phase 7 tiếp tục ở trạng thái chưa hoàn thành; ledger phải nêu gate/task còn thiếu và hành động cụ thể tiếp theo.
