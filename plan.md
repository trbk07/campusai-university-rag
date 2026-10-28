# CampusAI — Roadmap toàn dự án và local release

Cập nhật: **28/10/2026 · Asia/Bangkok**
Repository: [trbk07/campusai-university-rag](https://github.com/trbk07/campusai-university-rag)

## 1. Quyết định hiện hành và cách đọc

**Đích phát hành: bản local, chạy trên máy người dùng, một người dùng trên mỗi
instance.** Quyết định của chủ dự án ngày 28/10/2026 thay thế mục tiêu triển khai
cloud trước đây. Phase 13 chuẩn bị bản local có thể cài đặt/tái tạo; Phase 14
nghiệm thu và phát hành bản đó. Oracle, VM, ARM64, domain, HTTPS công khai,
Tailscale và hạ tầng đa người dùng không còn là điều kiện hoàn thành dự án.

**Local không có nghĩa là AI hoàn toàn offline.** UI, PDF, index, OCR và state
chạy/lưu trên máy. Profile Gemini hiện có vẫn cần Internet và credential của
người dùng; câu hỏi, lịch sử và đoạn nguồn theo payload thực tế có thể được gửi
đến provider. Không có credential/provider khả dụng thì chỉ công bố đúng các
chức năng local đã kiểm chứng, không hứa vẫn sinh được đáp án AI.

Các phase 0–12 được khôi phục dưới đây để thấy đủ quá trình đã làm. **DONE theo
phạm vi từng phase không đồng nghĩa đã nghiệm thu bản release cuối.** Không mở
lại phase đã đóng chỉ để tạo báo cáo mới. Riêng Phase 0/3 đã có implementation;
hồ sơ cũ chưa xác nhận mọi điều kiện nghiệm thu độc lập, nên giữ rõ giới hạn đó.

- `[x]` / **DONE**: đã hoàn tất trong phạm vi ghi kèm.
- `[ ]`: còn thiếu công việc hoặc bằng chứng; có code không tự trở thành DONE.
- Số đo lịch sử chỉ áp dụng source/config/data/máy đã ghi, không tự chứng nhận RC mới.

Đi đến: [Tổng quan](#cac-phase) · [Phase 0–12](#phase-da-lam) ·
[Việc QA còn lại](#viec-con-lai) · [Phase 13](#phase-13) ·
[Phase 14](#phase-14) · [Quy tắc cập nhật](#quy-tac-cap-nhat).

<a id="cac-phase"></a>
## 2. Tổng quan đủ 15 phase

| Phase | Mục tiêu | Trạng thái / phạm vi |
|---|---|---|
| 0 | Nền tảng, tên dự án, package, contract | Đã triển khai; không có nghiệm thu production riêng |
| 1 | Ingestion và lifecycle tài liệu | DONE · acceptance Phase 1/2 |
| 2 | Chunking, bảng, provenance | DONE · acceptance Phase 1/2 |
| 3 | Embedding và dense index | Đã triển khai; dense report độc lập lịch sử còn CONDITIONAL |
| 4 | Basic RAG, context và cache | DONE · offline contract |
| 5 | Citation, grounding, abstention | DONE · 10/10 task, 5/5 gate, nghiệm thu nội bộ |
| 6 | BM25 + dense + RRF | DONE · release lịch sử |
| 7 | Chất lượng sản phẩm cốt lõi | DONE · scope Chat-quality, 68/68 ca |
| 8 | Benchmark và evaluation | DONE · scope Chat-quality, 300/300 ca |
| 9 | Temporal RAG | DONE · 6/6 task, 5/5 gate |
| 10 | Multi-document / multi-hop | DONE · 5/5 task, 5/5 gate |
| 11 | Chỉ mục quan hệ học phần có nguồn | DONE · 5/5 task, 5/5 gate; mặc định OFF |
| 12 | Web app MVP | DONE · local single-user; QA mở rộng theo dõi riêng |
| 13 | Đóng gói và khả năng chạy local | ĐANG CHUẨN BỊ · kế hoạch mới, chưa nghiệm thu toàn phase |
| 14 | Hardening, nghiệm thu và local release | CHƯA NGHIỆM THU · phụ thuộc RC Phase 13 |

Luồng chính: **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 12 → 13 → 14**.
Phase 11 là nhánh tùy chọn đã hoàn thành; không bắt bật graph/reranker để release.
QA mở rộng của ứng dụng là đầu vào cho Phase 13/14, không phải một phase mới.

<a id="phase-da-lam"></a>
## 3. Các phase đã làm — mục tiêu, kết quả và giới hạn

<a id="phase-0"></a>
### Phase 0 — Nền tảng dự án

Đã triển khai tên CampusAI, package `campusai`, cấu hình, README, biến môi trường,
public import contract và baseline. Mục tiêu là thống nhất cấu trúc và cách chạy,
không tự nhận đây là nghiệm thu release. Repository chính dùng `origin` CampusAI;
remote financial lịch sử chỉ fetch. [Đặc tả](docs/planning/phase_details.md#phase-0).

<a id="phase-1"></a>
### Phase 1 — Ingestion và lifecycle PDF · DONE

Tiếp nhận/kiểm tra PDF, nhận diện tài liệu, metadata, xử lý nền, lưu trữ và quản
lý vòng đời upload/retry/delete. Kiểm soát file lỗi, đường dẫn và nguồn; scan cần
OCR có giới hạn thay vì âm thầm coi trang rỗng là thành công. Phase 1/2 đã đạt
**16/16 tiêu chí acceptance chung**.
[Acceptance](evaluation/results/ingestion_acceptance.json) ·
[Contract](docs/planning/phase_details.md#phase-1).

<a id="phase-2"></a>
### Phase 2 — Chunking, bảng và provenance · DONE

Chia nội dung theo cấu trúc, kế thừa heading, giới hạn chunk/overlap, giữ header,
hàng/ô bảng và tài liệu/trang nguồn để citation tái hiện được. Có fixture cho
section, bảng và provenance. OCR/bảng mới của QA không tự thay nghiệm thu gốc.
[Hồ sơ Phase 1/2](docs/ingestion/ingestion_acceptance.md) ·
[Đặc tả](docs/planning/phase_details.md#phase-2).

<a id="phase-3"></a>
### Phase 3 — Embedding và vector search · ĐÃ TRIỂN KHAI

Có embedding multilingual, dense index bền qua restart, kiểm tra model/corpus
identity và từ chối index hỏng hoặc sai phiên bản; hash provider dành cho test.
**Report dense độc lập cũ vẫn CONDITIONAL**: corpus nhỏ và negative chưa được
calibrate đầy đủ; không đổi nhãn artifact cũ thành PASS. Pipeline ứng dụng đã
phát triển tiếp qua hybrid và QA, nhưng đó là bằng chứng theo scope khác.
[Report gốc](evaluation/results/retrieval_acceptance.json) ·
[Đặc tả](docs/planning/phase_details.md#phase-3).

<a id="phase-4"></a>
### Phase 4 — Basic RAG · DONE trong offline contract

Ghép retrieval → context có budget → prompt Việt/Anh → answer; cache theo
corpus/version và abstention khi thiếu evidence. Offline contract chứng minh
schema, cache, context và đường từ chối; chất lượng model thật được đánh giá ở
các phase sau, không suy ra từ fixture.
[Report](evaluation/results/basic_rag_report.json) ·
[Đặc tả](docs/planning/phase_details.md#phase-4).

<a id="phase-5"></a>
### Phase 5 — Citation, grounding và abstention · DONE nội bộ

**10/10 task, 5/5 gate, chốt 25/10/2026** trên `a21a4cd5` / `grounding-v29`.
Đã hoàn thành audit/contract, schema public/internal, citation/provenance,
claim grounding, abstention, benchmark/review, confidence/calibration/cache,
qualification, kiểm tra gates và bàn giao.

- **400/400 ca**: dev 120, test 130, holdout 150; kiểm tra vật lý độc lập PASS.
- Grounding/citation và abstention precision/recall **100%**, leakage **0**;
  reason accuracy **97,67%**, holdout ECE/Brier/risk **0**.
- Ba full regressions liên tiếp, mỗi lượt **2.663 PASS / 2 live SKIP**.
- Tái sử dụng 426 captures Gemini có HTTP input khớp, chạy lại pipeline;
  không gọi đó là inference mới hoặc fresh holdout.

Đây là nghiệm thu nội bộ có công khai exposure và owner duyệt. Giữ đóng Phase 5;
fresh holdout trước phân phối bản release vẫn là gate riêng ở Phase 14.
[Closure](evaluation/results/phase5-mixed-absence-20261024/phase5-closure.json) ·
[Handoff](docs/grounding/phase5_completion.md) ·
[Ngưỡng bất biến](configs/grounding_release.json).

<a id="phase-6"></a>
### Phase 6 — BM25 + dense + RRF · DONE trong release lịch sử

Kết hợp lexical/dense, route mã môn, filter document/program/year, RRF, dedupe,
confidence và giới hạn candidate. Có đo chất lượng/latency riêng các nhánh và
artifact nhận diện corpus/index/config. Manifest lịch sử không tự chứng nhận
máy hoặc corpus mới.
[Manifest](evaluation/results/hybrid_release_manifest.json) ·
[Đặc tả](docs/planning/phase_details.md#phase-6).

<a id="phase-7"></a>
### Phase 7 — Chất lượng sản phẩm cốt lõi · DONE trong scope Chat

Scope owner chốt 13/10/2026: retrieval/context/scope, answer, citation, negative,
cache và fallback. **42/42 đáp án + 26/26 negative đúng**, 74 supported claims,
90 supported claim-citation pairs; 60/60 fault cases. Optional reranker giữ OFF;
nhánh qualification cũ vẫn RELEASE-BLOCKED nếu muốn bật lại. Performance API thật
chưa được nghiệm thu trong scope này, theo dõi ở R-01.
[Handoff](docs/phase7_product_handoff.md) ·
[Task và giới hạn](docs/planning/phase_details.md#phase-7).

<a id="phase-8"></a>
### Phase 8 — Benchmark và evaluation · DONE trong scope Chat

Frozen v5 có 300 ca: **145/145 đáp án nguồn đúng + 155/155 negative đúng**,
178 supported claims, schema ứng dụng 300/300; exact-gold citation 144/145,
một chunk thay thế vẫn hợp lệ. Review tự động AI có provenance, không giả chữ
ký con người. Raw format chỉ 17 valid / 128 invalid; normalization không chứng
minh native provider format. Bộ đã exposure là regression; R-02 còn riêng.
[Evaluation](docs/phase8_evaluation.md) ·
[Completion](evaluation/results/phase78-chat-quality-completion-20261013.json).

<a id="phase-9"></a>
### Phase 9 — Temporal RAG · DONE

**6/6 task, 5/5 gate; 24/24 ca** được source review và replay ứng dụng. Phân biệt
năm/khóa/phiên bản với ngày hiệu lực; lọc source eligibility trước generation,
so sánh hai phiên bản có nguồn; thiếu căn cứ “hiện hành/mới nhất” thì abstain.
Không suy hiệu lực chỉ từ tên file hoặc ngày ký.
[Handoff và protocol](docs/phase9_temporal_handoff.md).

<a id="phase-10"></a>
### Phase 10 — Multi-document / multi-hop · DONE

**5/5 task, 5/5 gate; 24/24 ca**, 32 supported claims và 24 valid citations.
Ghép evidence có vai trò rõ, tối đa một truy hồi phụ khi identifier được nguồn
chứng minh; giữ quyền/source scope và temporal contract. Thiếu một hop, ô trống
hoặc quan hệ mâu thuẫn thì không suy diễn đáp án.
[Handoff](docs/phase10_multi_hop_handoff.md) ·
[Completion](evaluation/results/phase10-completion-20261014.json).

<a id="phase-11"></a>
### Phase 11 — Chỉ mục quan hệ có nguồn · DONE, mặc định OFF

**5/5 task, 5/5 gate** cho SQLite sidecar tùy chọn: tiên quyết trực tiếp, truy vấn
ngược và chuỗi hai cạnh, mỗi quan hệ có proof hàng/ô nguồn. Có budget, scope,
fingerprint, invalidation và rollback; không cần dịch vụ graph riêng. Chỉ bật
trên profile/corpus đã qualification; bản local có thể phát hành khi vẫn OFF.
[Handoff](docs/phase11_relation_index_handoff.md) ·
[Completion](evaluation/results/phase11-completion-20261014.json).

<a id="phase-12"></a>
### Phase 12 — Web app MVP · DONE trong local single-user

UI Python/HTML/CSS/JavaScript cùng app: thư viện, collections, upload/job, chat,
source/citation, feedback, delete và hướng dẫn. Có launcher Windows, responsive,
accessibility và browser acceptance. Upload tối đa **5 PDF mỗi lượt**, được thêm
các lượt tiếp trong cùng chat. Hoàn thành MVP không đóng thay QA mở rộng.
[UI, setup và bằng chứng](docs/ui/phase12-ui.md).

<a id="qa-goal-progress"></a>
<a id="viec-con-lai"></a>
## 4. QA mở rộng — đầu vào của bản local release

Nguồn yêu cầu: `goal.txt`. Chi tiết: [QA audit](QA_AUDIT.md),
[test scenarios](TEST_SCENARIOS.md), [performance](PERFORMANCE_REPORT.md),
[improvements](IMPROVEMENT_LOG.md). Giữ các task DONE đóng.

### Việc còn mở, làm theo thứ tự

1. [ ] **QA-03b / QA-07c — PDF đại diện.** Dùng inventory 34 PDF, đối chiếu
   trang/text/bảng/ô với nguồn; extraction ≥98%, OCR ≥90%, evidence/retrieval
   ≥95%, không mất trang, nhầm tài liệu hoặc dữ liệu. Chốt denominator và cách
   tính trước khi chấm; fixture không thay nghiệm thu PDF thật. QA-03b1 (chữ ẩn)
   và QA-03b2 (VietOCR riêng) đã DONE. QA-03b3 về liên kết ô/bảng đang verification,
   chưa nhận là DONE toàn gate. [Tiến độ bảng](docs/ui/evidence/ocr-table-grounding-20261028.json).
2. [ ] **QA-08c — Streaming model thật.** Mục tiêu p95 TTFT ≤5 giây trên môi
   trường cố định; không tính heartbeat/cache/trích đoạn thành token model.
   Engineering SSE đã DONE, mặc định OFF; cohort 20 câu có 17 đúng nguồn và
   3 timeout, p95 gồm lỗi **chưa đạt**. Không bỏ lỗi khỏi denominator.
   Nếu giữ streaming OFF cho v1, ghi gate DEFERRED và bỏ mọi tuyên bố đạt TTFT;
   đây là điều chỉnh scope release, không phải đổi QA-08c thành PASS.
   [Evidence](docs/ui/evidence/query-streaming-20261028.json).
3. [ ] **QA-09d — Nghiệm thu cuối.** Khi runtime RC ổn định: 3 full regressions
   liên tiếp cùng source, required tests/flows 100%, critical E2E 100%, tổng E2E
   ≥98%, không crash/exception chưa xử lý; không còn P0/P1 hoặc High/Critical
   đã xác nhận. Lượt full lịch sử mới nhất đã ghi: **3.149 PASS / 2 live SKIP**;
   chưa thay chuỗi 3 lượt trên runtime cuối. Thực hiện một lần tại L14-07.

<a id="da-done"></a>
### Các mốc QA đã DONE — bằng chứng được giữ lại

| Nhóm đã hoàn thành | Kết quả / hồ sơ |
|---|---|
| QA-01, QA-02 | Export từ Git có 114 app tests PASS; Phase 5 nội bộ đã đóng như trên |
| QA-03a, QA-07a | So CPU/CUDA trên 5 PDF; inventory 34 SHA và kiểm trang. [Inventory](docs/ui/evidence/phase5-v27-20261024/pdf-parser.json) |
| QA-03b1 | Loại chữ vô hình khỏi evidence; 34 PDF/268 trang giữ nguồn, 344 tests PASS. [Evidence](docs/ui/evidence/pdf-visibility-20261027.json) |
| QA-03b2 | VietOCR opt-in riêng, đủ 18 trang; mã đúng 20/20, scan fixture 97,2%; 282 tests PASS. [Evidence](docs/ui/evidence/vietnamese-ocr-20261028.json) |
| QA-03c / QA-08d | 20/20 fresh uploads PDF text 100 trang/10 MB, p95 12,25s ≤15s; model/OS cache warm trên CUDA. Startup riêng 42,51s. [Evidence](docs/ui/evidence/native100-performance-20261027.json) |
| QA-04–06, QA-10–11, QA-13 | Mixed PDF, OCR từ chi tiết, job identity cũ, cancel/progress, OCR process Việt/Anh và ảnh trong trang text. [Isolation](docs/ui/evidence/ocr-isolation-20261025.json), [OCR](docs/ui/evidence/ocr-evaluation-20261025.json) |
| QA-07b cùng các bản sửa | Natural100 accuracy bảo thủ ≥95/100, answerable ≥75/80, hallucination phát hiện 0/100; context 15/15 và 17 trường. Bộ dev exposed, không phải fresh holdout. [Quality](evaluation/results/full-app-natural-20261026/quality-qualification.json), [Context](evaluation/results/full-app-natural-20261026/context-quality.json) |
| QA-08a / QA-08b | 400/400 HTTP 200 trên workload API local; Web Vitals lab 9/9. Không suy thành tải generation AI đồng thời. [Coverage](docs/ui/evidence/hybrid-coverage-20261025.json) |
| QA-08c1 | SSE, cancel, quota/cooldown và UI chỉ công bố kết quả sau grounding; 346 related tests, 9 JS checks, UI 43/44 checks theo nhánh. [Evidence](docs/ui/evidence/query-streaming-20261028.json) |
| QA-09a / QA-09b | Unit/integration và 43/43 browser flows ở mốc lịch sử. [Browser](docs/ui/evidence/hybrid-final-ui-20261025/browser-results.json) |
| QA-09c1–c2c | Recovery local, 10 checkpoint kill/restart, deep JSON trả 400, Host guard localhost; 229 related tests và secret scan PASS. [Evidence](docs/ui/evidence/request-safety-recovery-20261027.json) |
| QA-12 | Cache metadata/library có invalidation, đọc đúng scope; quyền/delete/retry vẫn kiểm tra mới. [QA audit](QA_AUDIT.md) |

Các số test có thể chồng lấn, không cộng lại thành tổng tests độc lập. Không
thử lại TableFormer + OCR từng ô đã bị loại do chậm/sai nếu chưa có lý do mới.

<a id="phase-13"></a>
<a id="phase-13--deployment"></a>
## 5. Phase 13 — Đóng gói và vận hành bản local

**Đánh giá:** app local đã tồn tại và có recovery/performance evidence; thiếu
nghiệm thu tái tạo bản phát hành ngoài môi trường dev. Không cần xây lại server,
frontend hay pipeline. Chọn **source bundle/checkout theo tag + môi trường Python
khóa bằng `uv.lock` + launcher** cho v1; chưa cần tự ép thành một file `.exe`.
Windows x64 là đích ưu tiên; chỉ công bố OS/Python/CPU/GPU thực sự đã kiểm chứng.
Metadata Python hiện khai báo 3.11–3.14 không có nghĩa mọi tổ hợp đều đã test.

Phụ thuộc: Phase 12, runtime hiện có; đóng QA PDF trước khi khóa RC cuối. Có thể
làm packaging/docs song song về mặt tiến độ, nhưng source-bound receipt phải
được tạo từ candidate cụ thể. **Task mới chưa được tự tick theo bằng chứng cũ.**

| ID | Công việc cụ thể | Điều kiện đóng / đầu ra | Trạng thái |
|---|---|---|---|
| L13-01 | Chốt release contract | Ghi Windows/Python đã test, browser, CPU tối thiểu; GPU tăng tốc tùy chọn; phân biệt cài mới cần mạng với chạy sau setup; chốt streaming/graph/reranker OFF mặc định | [ ] |
| L13-02 | Khóa cấu hình và runtime assets | Bind commit, `uv.lock`, profile, encoder revision/hash, OCR/model/language data và license; setup có checksum, lỗi rõ, không tự tải model trong upload/query | [ ] |
| L13-03 | Tạo artifact tái tạo được | Bundle đủ `src`, `scripts`, UI, config mẫu, lock, launcher và docs; manifest SHA-256/file list; loại `.venv`, credential, PDF cá nhân, runtime state/cache và temp; phân biệt source bundle với wheel thư viện | [ ] |
| L13-04 | Cài sạch ngoài working tree dev | Giải nén/checkout candidate trong thư mục mới, tạo env từ lock, setup model/OCR, nhập key riêng; start/stop/restart và smoke upload → chat → citation → delete đạt; không mượn module/index/state của dev | [ ] |
| L13-05 | Chốt thư mục dữ liệu và preflight local | Tài liệu hóa đường dẫn PDF/store/index/job/cache/quota/log/model; tạo lần đầu, quyền ghi, dung lượng, port bận, thiếu model/key, CPU fallback; không ghi dữ liệu vào vùng cài đặt chỉ đọc | [ ] |
| L13-06 | Tài liệu người dùng và hỗ trợ | Quick start Windows, setup online/OCR tùy chọn, cấu hình key không lộ, stop/update/backup/uninstall; lỗi thường gặp, cấu hình CPU/GPU đã đo và giới hạn PDF; người mới làm được từ docs | [ ] |
| L13-07 | Khóa release candidate | Candidate có version/commit, artifact checksum, dependency/model/config identities, feature flags, báo cáo install/smoke và known issues; chuyển đúng candidate sang Phase 14 | [ ] |

**Gate đóng Phase 13:** 7/7 task, artifact không chứa secret/dữ liệu cá nhân,
cài sạch tái tạo được và vận hành end-to-end trên profile đã công bố. QA PDF
còn mở hoặc candidate thiếu asset/module thì chưa được gọi là RC sẵn sàng.

Không bê tỷ lệ **6/64 tiêu chí, 0/16 task cloud** sang kế hoạch local: chúng khác
contract. Kế hoạch cloud cũ được giữ làm lịch sử, không còn là backlog bắt buộc.
Provider admission, cache, cooldown và cấu hình portable đang có vẫn được dùng.

<a id="phase-14"></a>
## 6. Phase 14 — Hardening, nghiệm thu và phát hành local

**Đánh giá:** rủi ro còn lại nằm ở PDF/OCR thật, độ tin cậy model/provider, bảo vệ
dữ liệu trên máy và tính tái tạo của gói. Không cần Kubernetes, reverse proxy,
đăng nhập đa người dùng hay SLO cloud cho scope loopback single-user. Host guard,
quyền nguồn, timeout, quota, cancellation và grounding vẫn bắt buộc.

Phụ thuộc: RC Phase 13 có identity rõ. Đây là nghiệm thu của **candidate cụ thể**,
không mở lại toàn bộ phase cũ. Dùng lại evidence còn tương thích, chỉ chạy mới
phần thay đổi hoặc gate release yêu cầu. Không tự tạo nhãn human signoff.

| ID | Công việc cụ thể | Điều kiện đóng / đầu ra | Trạng thái |
|---|---|---|---|
| L14-01 | Khóa ma trận yêu cầu và phạm vi | Map QA/R-01/R-02/fresh holdout tới case, profile, threshold và evidence; phân biệt blocking với optional deferred; giữ nguyên lỗi và các gate chưa PASS | [ ] |
| L14-02 | Nghiệm thu PDF/AI trên RC | Đóng QA-03b/QA-07c với 34 PDF; giữ gold/threshold; thêm fresh holdout đóng băng trước output, tách dev/test, có source review và denominator theo loại câu; không tune rồi gọi chính bộ đó là fresh | [ ] |
| L14-03 | Đo provider và hiệu năng local thật | Đóng R-01/R-02 bằng protocol phù hợp profile local đã khóa trước run; đo cold/warm/cache riêng, p50/p95/errors/timeouts/RSS/usage, native format; dùng profile/budget đã được phép, không xoay key/retry vô hạn | [ ] |
| L14-04 | Bảo mật và quyền riêng tư local | Secret/dependency scan, loopback/Host/origin và request validation, path/symlink/upload limits, quyền nguồn/cache, cancel/timeout; không có P0/P1/High/Critical đã xác nhận; privacy notice mô tả payload/provider/log/retention thực tế | [ ] |
| L14-05 | Backup, restore và update/rollback | Backup nhất quán PDF/metadata/job/config cần thiết; restore vào state sạch rồi kiểm hash, citation, chat/delete; test ngắt process, hết đĩa, state/index hỏng, đổi version; rollback không làm mất source và dữ liệu cũ | [ ] |
| L14-06 | Chẩn đoán và runbook | Request ID/log có giới hạn, stage latency, lỗi quota/503/OCR và health; không log key hoặc toàn bộ tài liệu; hướng dẫn restart, reset index an toàn, cấp quyền, thu log đã lọc và uninstall có lựa chọn giữ dữ liệu | [ ] |
| L14-07 | Regression cuối đúng RC | Đóng QA-09d: 3 full liên tiếp cùng runtime, required/critical flows 100%, E2E ≥98%; test launcher/install/browser/OCR/source/delete/recovery trên artifact; live SKIP không tính live PASS | [ ] |
| L14-08 | Hồ sơ phát hành và bàn giao | Release notes/known limits, manifest/checksum, install/backup/restore docs, evidence source-bound và danh sách hoãn; owner duyệt candidate cụ thể rồi tạo tag/phát hành bản local theo phạm vi được phép | [ ] |

### Xử lý các điều kiện release cũ

| Điều kiện | Quyết định cho local release |
|---|---|
| R-01 — Performance Phase 7 | Vẫn NOT PASSED. Giữ protocol cũ 100 HTTP/54 provider calls, p95 ≤10s, timeout ≤0,5%, RSS ≤75% RAM làm mốc. Nếu workload/profile v1 khác, phải khóa amendment trước run và báo riêng; không sửa nhãn lịch sử |
| R-02 — Phase 8 live API | Vẫn NOT PASSED. Chat/replay/normalized output không thay native API latency/availability/format; nghiệm thu trên profile thực sự phân phối, báo đủ lỗi và thiếu mẫu |
| R-03 — Public cloud deployment | Rút khỏi scope theo quyết định 28/10/2026, không ghi PASS. Nghĩa vụ bảo mật, dữ liệu, recovery và vận hành local chuyển L13/L14 |
| Fresh holdout Phase 5 | Giữ gate trước phân phối release, độc lập DONE nội bộ. Khóa số mẫu/strata/review và ngưỡng trước chạy; giữ thresholds [grounding](configs/grounding_release.json), không sửa nhãn/gold để qua gate |
| QA-08c streaming ≤5s | Nếu OFF mặc định: được DEFERRED với giới hạn công khai, không claim PASS/TTFT. Muốn đưa streaming vào tính năng đã nghiệm thu phải qua gate thật, tính cả timeout |
| Graph/reranker | OFF mặc định; không bắt qualification tính năng tắt. Bật lại cần nghiệm thu đúng profile và guards lịch sử |

**Gate đóng Phase 14 / hoàn thành dự án:** 8/8 task; Phase 13 đóng; các gate
blocking chất lượng, an toàn dữ liệu, provider và final regression có bằng chứng
khớp candidate; không còn lỗi nghiêm trọng đã xác nhận; owner duyệt bản local.
Chỉ công bố máy/profile/workload đã đo. Không hứa AI offline, hỏi miễn phí vô
hạn, hỗ trợ mọi PDF/OS hoặc availability 100% khi chưa có chứng cứ.

### Thứ tự thực hiện từ hiện tại

1. Hoàn tất PDF đại diện (QA-03b/QA-07c), chốt backend OCR đủ điều kiện cho v1.
2. Làm L13-01–06; định nghĩa ma trận L14-01 và protocol live/holdout trước đo.
3. Khóa L13-07, chạy L14-02–06 trên candidate đó; giữ sửa lỗi trong scope local.
4. Chốt runtime rồi thực hiện L14-07 một lần đủ chuỗi; thay source/config sau đó
   chỉ vô hiệu hóa evidence bị ảnh hưởng, phải có lý do và phạm vi kiểm tra lại.
5. Chuẩn bị hồ sơ L14-08, owner duyệt candidate, phát hành local và bàn giao.

<a id="quy-tac-cap-nhat"></a>
## 7. Quy tắc giữ plan và bằng chứng

1. Chọn một task còn mở, ghi lỗi/khoảng trống, điều kiện đóng và evidence. Tick
   ngay khi đủ; không tính % bằng cộng task có khối lượng khác nhau.
2. Giữ task DONE đóng; chỉ mở lại vì source/phụ thuộc liên quan đổi, lỗi mới,
   môi trường ngoài scope hoặc nghiệm thu cuối bắt buộc. Ghi lý do trước.
3. Sửa tài liệu không kích hoạt full regression/400 ca/API/PDF benchmark.
   Sửa runtime chạy focused tests trước; không cộng các lượt tests chồng lấn.
4. Không tune test/holdout, không giả reviewer, không tính replay/cache/SKIP
   thành native inference/live PASS. Dùng lại captures chỉ khi binding hợp lệ.
5. Giữ giới hạn chi phí, dữ liệu và provider đã thống nhất; không bật billing,
   đổi key/model hoặc gọi API chỉ để tạo report. Local release không bỏ quota.
6. Dọn file tạm sau khi kiểm tra references/bindings. Giữ source, config, tests,
   baseline, raw failures và artifact cần tái hiện; không xóa bằng chứng phase cũ.
7. Giữ `plan.md` tại root và tracked Git; commit/push qua `origin` CampusAI,
   không đẩy sang repository financial cũ. Thay đổi chưa liên quan giữ riêng.

## 8. Tra cứu lịch sử và tương thích liên kết

[Đặc tả phase cũ](docs/planning/phase_details.md) giữ ID task, ngưỡng, contract,
cloud checklist và lịch sử thử nghiệm. **Plan hiện hành này quyết định phạm vi,
trạng thái và thứ tự công việc.** Các yêu cầu cloud cũ đã được thay thế; không
xóa/đổi byte báo cáo lịch sử để hợp thức hóa local release.

[Hardening Phase 3–6](docs/planning/release_hardening_plan.md) là backlog tham
chiếu lịch sử; đánh giá khoảng trống liên quan qua L14-01, không tự chạy lại toàn
bộ hoặc đổi trạng thái DONE của các phase đã nghiệm thu.

<a id="ưu-tiên-hiện-tại--hỏi-liên-tục-không-quá-tải-chi-phí-dịch-vụ-0"></a>
Continuity local ngày 16/10 đã đóng trong phạm vi đã đo:
[hồ sơ](docs/deployment/phase13/free-continuity-goal.md). Không đồng nghĩa provider
miễn phí vô hạn hoặc đã đạt R-01/R-02.

<a id="phase-7--hoàn-thiện-chất-lượng-sản-phẩm-phạm-vi-tinh-gọn"></a>
<a id="phase-7--reranker"></a>
<a id="phase-7--reranker-release-qualification"></a>
<a id="phase-7-joint-dev-feasibility--2026-10-04"></a>
Optional reranker giữ OFF; qualification cũ chỉ mở khi cần bật lại.
[Đặc tả lịch sử](docs/reranker/phase7_task_spec.md) ·
[Artifact storage/restore](docs/operations/artifact_storage.md).
