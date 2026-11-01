# CampusAI — Tổng quan chất lượng và vận hành

**Cập nhật 01/11/2026 · Phạm vi: web app local, một người dùng trên Windows.**

Tài liệu này thay các báo cáo kiểm tra, nghiệm thu, hiệu năng và nhật ký rời.
Các số lịch sử bên dưới được tổng hợp trước khi xóa đầu ra cũ; chúng không
chứng nhận phiên bản hiện tại đã hoàn tất nghiệm thu. Công việc tiếp theo nằm
trong [roadmap](../plan.md); thao tác cài và backup nằm trong
[hướng dẫn local](operations/local-install.md).

## 1. Ứng dụng hiện có

CampusAI nhận PDF, đọc chữ và bảng, OCR nền khi cần rồi lập chỉ mục hybrid.
Người dùng chọn nguồn để hỏi; câu trả lời phải qua kiểm chứng và có citation
theo trang. Nguồn thiếu hoặc chưa đọc đủ được thể hiện rõ thay vì suy đoán
toàn văn. OCR hỗ trợ checkpoint, hủy, thử lại và tiếp tục sau restart.

Gemini sinh câu trả lời qua Internet; model truy hồi và OCR chạy trên máy.
Profile đang dùng là `configs/free_multi_project.yaml`, chia tải qua ba Google
project độc lập đã được chủ dự án xác nhận. Quota, cooldown và số lượt thử vẫn
được kiểm soát; không cam kết miễn phí vô hạn. Streaming, graph và reranker
không nằm trong cấu hình mặc định đang phát hành.

## 2. Kết quả đã quan sát và giới hạn diễn giải

**Cải thiện OCR ngày 01/11 (`c54b2b8b`):** giữ nguyên Tesseract vie+eng, độ phân
giải và BGE-M3 đã pin; chia OCR thành hai worker khi đủ trang, giới hạn tổng
worker trên nhiều tài liệu. Lô đầu vẫn nhỏ để hỏi sớm; các lô sau tăng theo tốc
độ thực. Chỉ tái dùng vector khi input embedding, model và document khớp chính
xác; metadata/coverage được cập nhật và index vẫn commit nguyên tử.

Trên PDF scan thật 34 trang, pipeline đọc → OCR → index giảm **52,811 → 29,479s**
(giảm 44,2%); phần đầu sẵn sàng **4,265s**, cuối cùng đủ 34/34 trang và hash toàn
văn giống bản tuần tự. Số đoạn encode cộng dồn giảm **363 → 98**. Thử riêng
workload hai PDF gồm 10 trang scan + 5 trang mixed/10 vùng ảnh: OCR **14,923 →
4,652s**, text, layout, confidence và audit vùng ảnh giống bản tuần tự.
Đây là A/B một lượt trên máy local, cache hệ điều hành/model warm; thời gian
warm encoder 16,27s tách riêng. Không phải p95 hoặc phép đo accuracy độc lập.
128 tests hiện hành PASS; thêm 20 tests tương thích ingestion/cancel/progressive
và 164 tests tương thích hỏi đáp từ `f9d8ba10` PASS; 1 test cũ thiếu corpus không
chạy. Các bản test tạm tự xóa; không thêm báo cáo JSON vào repo.

**Hỏi đáp, 01/11:** sửa guard tên trường theo provenance của nguồn được trích;
chặn đảo số liệu đơn giản giữa hai PDF dù các số đều xuất hiện trong tổng bằng
chứng; coi `TC` và `tín chỉ` là cùng đơn vị. Khôi phục điều kiện từ nguồn rồi kiểm
chứng lại; giữ các điều kiện trong cùng danh sách và ngoại lệ ở câu liền sau,
không lặp ghi chú khi phần trả lời đã diễn đạt ngoại lệ tương đương. Quy đổi điểm
hiển thị khoảng điểm làm căn cứ. Đây là kiểm tra có giới hạn, không phải bộ suy
luận ngữ nghĩa đầy đủ cho mọi cách diễn đạt/PDF.

C03 từng bị chặn trên `0fe1cdc1`: parser lưu đoạn văn thành bảng hai cột, một
cột rỗng; citation chỉ lấy một dòng nên claim đầy đủ bị coi là mâu thuẫn. Bản sửa
giữ nguyên các hàng liên tiếp trong cột không có tiêu đề, không ghép qua cột có
dữ liệu, hàng rời hoặc đoạn lặp mơ hồ. Claim phải khớp đủ nguyên văn trước khi
được kiểm chứng như văn xuôi; sai phủ định hoặc đổi từ cuối vẫn bị chặn.

Các lượt đủ bộ owner gốc, cùng **56 case / 60 HTTP**:

| Source | Local / cache / HTTP có provider | Provider attempts | p95 / tối đa | Chấm dev theo toàn bộ gold |
|---|---|---|---|---|
| `7ca85979` | 25 / 1 / 34 | 36 | 5,590 / 7,611s | 40 PASS / 12 PARTIAL / 4 REVIEW_REQUIRED |
| `0fe1cdc1` | 25 / 0 / 35 | 36 | 4,571 / 8,001s | Phát hiện C03 từ chối; không nghiệm thu chất lượng |
| `f5a5356f` | 25 / 0 / 35 | 36 | **4,513 / 8,423s** | **43 PASS / 9 PARTIAL / 4 REVIEW_REQUIRED** |

Cả ba lượt không timeout hoặc lỗi schema/citation. Benchmark SHA-256
`07f1ac1782b058bb9ce824490cd8c77521b0ab0fee5998a139a4e2ee2d1fb2fc`;
154 file runtime không đổi trong lượt chạy. Chỉ input câu hỏi/lịch sử thật và
ba PDF đã chọn đi vào inference; không dùng school label/gold/expected.

Chấm AI bảo thủ dùng để theo dõi dev, chưa phải review độc lập/owner sign-off.
F18, F27, N06 và M04 đã đủ ý trong lượt mới; F17 vẫn thiếu ngày ban hành có trong
gold. Chín ca PARTIAL cần đối chiếu phần gold bổ sung so với câu hỏi:

| Ca | Phần gold chưa xuất hiện đầy đủ trong câu trả lời |
|---|---|
| F01 | Thời gian chuẩn 4 năm ngoài mức tín chỉ được hỏi |
| F04 | Điều kiện số tín chỉ khi dùng học phần tương đương thay thế |
| F17 | Ngày 09/06/2021 ngoài số quyết định được hỏi |
| F19 | Đối chiếu A+ = 4,0 ngoài phép quy đổi A được hỏi |
| F20, N04 | Các mức D/D+ được học cải thiện, ngoài việc từ chối mức C |
| F25 | Khả năng tổ chức học kỳ phụ ngoài số kỳ chính được hỏi |
| F26 | Cận tối thiểu 2/3 ngoài cận tối đa 3/2 được hỏi |
| N01 | Lưu ý phải xét các điều kiện cảnh báo khác |

Giữ nguyên gold/rubric; không tự thu hẹp để tính các ca này thành PASS.
F02/F05/N03 thiếu trường trong input khi chọn nhiều nguồn; app hỏi làm rõ, không
được lấy school label để trả thay. F24 gold “15 tuần/kỳ” chưa được chứng minh:
trang 6 chỉ nêu hai kỳ tổng tối thiểu 30 tuần, còn 15 giờ/tuần ở đoạn khác không
phải 15 tuần/kỳ. Giữ nguyên gold gốc, review riêng; không tính 4 ca này thành PASS.

Từ `d370b6ea`, tổng thời lượng nhiều kỳ không thay thời lượng từng kỳ; 8 HTTP
trọng tâm đã kiểm trước đó. Bản hiện hành `190fa8bb` giữ cả đuôi văn bản ngắn và
tránh lặp ngoại lệ: **145 tests hiện hành + 164 tests tương thích PASS**, 1 test
cũ thiếu corpus không chạy. **9 HTTP trọng tâm** trên chính bản này, 3 local,
6 HTTP có provider / 7 attempts, 0 cache, không lỗi schema/citation; C03 đúng hai
nguồn, N07 giữ ngoại lệ không lặp, GPA giữ điều kiện, F24 giải thích giới hạn bằng
chứng. Không ghép 9 lượt này thành một cohort 60 mới.
Goal chất lượng vẫn mở; chưa có bằng chứng 99–100% và chưa mời owner nghiệm thu.
CI source `190fa8bb` đã PASS: [run 41290867645](https://github.com/trbk07/campusai-university-rag/actions/runs/41290867645),
gồm Windows/Linux, package và container. Không coi CI là phép chấm semantic.

**F01 đã khắc phục trên `9ec52954`:** khi bảng được trích và bảng gốc cùng xác
định duy nhất một hàng/nhóm đầu vào, app bổ sung trường thời gian hoặc tín chỉ
còn thiếu rồi kiểm chứng lại. Có nhiều nhóm, trường không hợp lệ, câu so sánh
hoặc yêu cầu trả ngắn thì không tự thêm. Opt-in qua profile web hiện hành; các
phase khác giữ mặc định. Giá trị lấy từ ô nguồn, không từ ID câu hỏi/gold.

**149 tests hiện hành + 164 tương thích PASS** (1 corpus cũ thiếu nên không chạy).
**7 HTTP** trên source này: 3 local, 4 có provider/4 attempts, 0 cache, không lỗi
schema/citation; runtime không đổi. F01 đủ 132 tín chỉ/4 năm trong **2,807s**;
bản tiếng Anh **2,130s**, mỗi câu 1 inference, không có call bổ sung cho ngữ cảnh
hàng bảng. C03/C04 và hội thoại đổi trường M01 vẫn đúng, F02 vẫn hỏi rõ nguồn.
CI [run 41293834828](https://github.com/trbk07/campusai-university-rag/actions/runs/41293834828) PASS.

F01 DONE khỏi backlog; còn F04/F17/F19/F20/F25/F26/N01/N04 và bốn ca review đã
nêu. Lượt đủ 60 trên `f5a5356f` giữ nguyên 43/9/4; không ghép bảy lượt kiểm riêng
thành cohort mới hoặc tự nhận 99–100%.

| Nội dung | Kết quả lịch sử | Phạm vi / giới hạn |
|---|---|---|
| Grounding Phase 5 | 400/400 kết quả, 5/5 gates nội bộ | Bộ đã exposure; chưa thay fresh holdout cho bản cuối |
| Natural100 | Accuracy bảo thủ ≥95/100; phát hiện hallucination 0/100; context 15/15, đủ 17 trường | Bộ dev đã dùng để sửa lỗi, không phải tập kiểm độc lập |
| Upload PDF text 100 trang / khoảng 10 MB | 20/20 lượt; p95 12,25s, tối đa 14,16s | CUDA, model/OS cache warm, upload tuần tự; startup đo riêng 42,51s |
| OCR nguồn tiếng Việt 31 trang | 98,38% ký tự; 46,33s; đủ 120 điều | Một tài liệu và reference riêng từ cơ quan xuất bản; không suy rộng mọi scan |
| Liên tục ba project Gemini | 100/100 HTTP hoàn tất; 96 trả lời, 4 abstain; 0 timeout/quota/HTTP failure; p95 4,654s | Thời gian hoàn tất, không phải TTFT; số trả lời không phải accuracy |
| Bộ QA owner 31/10 | 56 case, 60 lượt; tổng hợp mới nhất 36 PASS, 19 PARTIAL, 1 REVIEW_REQUIRED | Ghép các cohort của các phiên bản kế tiếp; chưa chạy đủ 60 lượt trên cùng bản cuối |
| Hồi quy trước đợt tinh gọn | Mốc gần nhất đã ghi: 3.740 PASS, 2 live opt-in SKIP; 427 focused PASS | Kết quả lịch sử, không phải bộ kiểm được giữ trong cây dự án hiện tại |

Các bản sửa đã xử lý nhận diện trường khi hỏi tiếp, quan hệ hàng/cột bảng
điểm, đơn vị tín chỉ, phân bổ bằng chứng giữa hai nguồn và điều kiện khi cắt
context. Quy đổi điểm có quy tắc rõ được tính từ nguồn, vẫn kiểm citation;
không dùng bảng đáp án owner làm dữ liệu inference. Profile web cho phép tối
đa một lượt sửa cách diễn đạt khi output dương tính bị validator chặn và phải
kiểm lại đầy đủ.

Riêng scan Thủ đô 34 trang: lần đo Tesseract `vie+eng` là 21,805s so với OCR cũ
237,925s. Ba lượt quy đổi điểm trả A/4,0 rồi A/3,7 trong 0,440–1,555s, không
cache, không gọi Gemini. Đây là các quan sát trên ca cụ thể.

## 3. Vấn đề chưa đóng

### Kiểm tra mới ngày 01/11

- **FIX-03b DONE:** chốt trước 20 trang ảnh thật của 3 PDF, 3 lần lặp, Tesseract
  `vie+eng`, scale 1,5, worker mới mỗi batch, nguyên deadline 120s. 60/60 lượt
  trang và 9/9 batch thành công; p95 nearest-rank **1,874079s/trang**,
  **12,676236s/batch**. OS/model file cache không bị purge; app đã nạp model,
  không có workload truy vấn kiểm soát đồng thời. Không suy rộng mọi PDF.
- **QA-03b DONE về chọn bộ:** native HUST tr.6; scan HNMU tr.7/14; mixed NUAE
  tr.31–33; bảng HUST tr.9; thêm fixture font ToUnicode sai được ghi rõ controlled.
  Đã xem trang render. Fixture giữ nguyên chữ hiển thị, parser không công bố lớp
  text sai, yêu cầu OCR; OCR khớp toàn bộ text reference sau chuẩn hóa whitespace.
  Reference fixture là dữ liệu kiểm soát tự tạo; không phải bằng chứng accuracy
  đại diện để đóng QA-07c. Bộ chọn và hash nằm trong `pdf-suite.json` local.
- **Baseline owner:** 56 case/60 HTTP liên tiếp trên cùng code và index, không
  cache hit, không timeout, schema/citation vật lý hợp lệ 60/60. p95 **15,097723s**,
  nên không đóng R-01. Chưa có independent semantic grading trên lượt này;
  số câu trả lời dương tính không được tính là accuracy.
- **Sửa code:** tổng trang PDF/file số nhiều dùng metadata (HTTP 0,049s);
  học trước không bị mở rộng thành tiên quyết; truy hồi địa chỉ/khóa áp dụng;
  nhận diện “giống/khác nhau” khi so sánh và vẫn chặn mâu thuẫn trong một nguồn.
  Source fields giữ nguyên điều kiện năm cuối, mức cảnh báo/học kỳ của giới hạn
  đăng ký và mệnh đề khóa áp dụng. Bốn ca trước chậm/sai trả đúng nguồn trong
  **0,508–0,981s**, không dùng giá trị/ID tài liệu cố định.
- **An toàn OCR:** subprocess chỉ nhận environment hệ điều hành/native cần
  thiết, không nhận key phụ/custom credential hoặc Python injection settings.
  Các RPC Gemini được ghi counter inference/countTokens riêng và model version
  thực nhận trong diagnostics opt-in; không ghi prompt/answer/key vào timing log.
- **F24:** đã đọc ảnh gốc cả tr.6 và tr.7: nguồn xác lập 2 học kỳ chính với tổng
  tối thiểu 30 tuần; không xác lập riêng mỗi kỳ tối thiểu 15 tuần. Giữ gold cũ
  nguyên vẹn, đánh dấu cần review; không tự phê duyệt gold thay thế. F02/F05/N03
  cần review scope vì input không nêu trường khi cả ba PDF được chọn.

Raw baseline, protocol khóa trước đo, PDF/hash và predictions được giữ local ở
`data/operations/local-acceptance-20261101/`; không đưa PDF/state/credentials vào
Git. Script đo và tests được giữ trong source để tái chạy. Fresh holdout,
semantic quality và RC cuối vẫn cần evidence riêng theo [plan](../plan.md).

### Qualification mới và sửa lỗi nội dung

Đã chạy **112 HTTP liên tiếp trên một commit `3289f41f`**: đủ 60 lượt gốc của
owner và một biến thể lịch sự cho từng câu đơn (52 câu). Đây là bộ dev đã
exposure, không phải fresh holdout. Mỗi request chỉ nhận câu hỏi, PDF được chọn,
ngôn ngữ và hội thoại thực tế trước đó; không nhận school/gold/expected/nhãn.

| Gate / phép đo | Kết quả trên `3289f41f` |
|---|---|
| R-01 profile qualification | PASS: 112/112 HTTP; 83 RPC inference thành công, không tính countTokens/local answer |
| Latency / availability | p95 nearest-rank 8,514353s; 0 timeout, 0 lỗi HTTP, 0 cache hit |
| RAM | RSS server và process con đỉnh 7,9951% RAM máy |
| R-02 API format | 112/112 public responses đúng schema, citation trỏ đúng chunk/page-range trong index khóa |
| Provider identity | Phản hồi thật báo `gemini-3.5-flash-lite`; profile, code, index và benchmark có hash |
| Semantic quality / public release | Chưa PASS; không dùng số HTTP thành công làm accuracy |

Lượt 100 HTTP trước đó trên `4ec44369` cũng không timeout nhưng p95 11,366472s,
nên giữ nguyên kết quả FAIL của lượt ấy. Không chọn ca tốt rồi ghép thành lượt
PASS. Hai lượt đều có protocol lưu trước request đầu, cùng các đầu ra lỗi/abstain.

Lượt 112 xác nhận sửa được hỏi tiếp về thời điểm kỳ thi phụ, trả đủ điểm chữ/hệ 4,
quy đổi độc lập giữa hai PDF (4,0 và 3,7 từ từng nguồn), đăng ký hè khẩu ngữ và
định nghĩa học phần học trước. Rule chỉ đọc literal source fields, giữ điều kiện
và xung đột, không chứa tên trường, ID benchmark hoặc giá trị gold cố định.
Guard cũng chặn public answer gán số tuần của cả năm cho một học kỳ và nhận ra
phát biểu thiếu thông tin có tên/chủ sở hữu nguồn ở giữa câu.

Ca CPA không còn công bố kết luận sai “tài liệu không quy định”, nhưng còn từ
chối trên `3289f41f`: bullet nguồn xuống dòng và kết thúc bằng `;`. Bản vá
`fc8a56af` chỉ mở nhận định dạng bullet này, giữ nguyên literal quote/threshold;
kiểm hồi quy 106 tests hiện tại + 164 tests tương thích PASS. Một test lịch sử
phụ thuộc fixture đã dọn bị loại riêng. CI của `3289f41f` PASS cả Windows/Linux,
Python 3.11/3.12/3.14, package và container:
[run 41232112418](https://github.com/trbk07/campusai-university-rag/actions/runs/41232112418).
Không gọi lượt 112 là đo toàn bộ bản vá sau đó; FIX-05/QA-09d vẫn mở.

CI bản vá `fc8a56af` cũng PASS:
[run 41233159681](https://github.com/trbk07/campusai-university-rag/actions/runs/41233159681).
164 tests tương thích lấy nguyên assertions từ `f9d8ba10`: `test_basic_rag`,
`test_grounding_policies`, `test_source_windows`, `test_grade_ranges`,
`test_presentation_fidelity`, `test_explicit_request_completeness`,
`test_cross_language_grounding`; helper model/payload từ `test_grounding`.
Loại riêng `existing_dev_positive_control_remains_answerable_before_provider`
vì thiếu corpus cũ. Các bản trích và thư mục pytest tạm đã dọn; source gốc vẫn
trong Git, 106 tests hiện hành giữ lại trong repo. Không thay assertions để tăng PASS.

Kiểm HTTP tập trung sau bản vá `fc8a56af`: F27, N06 và hai lượt M04 đều hợp lệ.
N06 trả đúng literal điều kiện 2,8 từ nguồn trong **0,538821s**, không cache và
không gọi provider; ba lượt khác dùng cache đã kiểm chứng. Không tính bốn lượt
này là bốn inference Gemini mới hoặc ghép vào phép đo 112 ở commit trước.

Các finding còn cần giải quyết: C04 còn abstain dù có nguồn; C02 chưa nêu thời
điểm thi phụ trong comparison; một số gold có thông tin ngoài câu hỏi (ví dụ
F01 thêm thời gian đào tạo, F26 thêm giới hạn tối thiểu). Giữ rubric/gold gốc
cho review, không tự bỏ các ý để tăng điểm. F24 và ba ca scope vẫn cần quyết
định review cụ thể; không tự tạo owner sign-off.

### Protocol fresh holdout trước khi đo

Chưa có tập mới đủ provenance để đóng gate. Không tái gắn nhãn bộ owner hoặc
52 biến thể làm holdout. Việc chuẩn bị/đo tiếp phải giữ đúng
[release contract trong lịch sử Git](https://github.com/trbk07/campusai-university-rag/blob/f9d8ba10/docs/grounding/grounding_release_gates.md):

- Holdout mới ≥150 record trong tổng benchmark ≥400 (dev ≥120, test ≥130),
  đủ category, cả answerable và abstention; family nguồn/template/intent không
  trùng split. Audit exposure cả lịch sử; chia lại dữ liệu đã tuning không làm mới nó.
- Khóa question/gold/evidence, source hash, review provenance và protocol trước
  inference; independent AI review được ghi đúng là AI, owner sign-off bind bộ cụ thể.
- Giữ leakage 0, coordinate validity 100%; citation precision/recall ≥0,99/0,98;
  grounded precision/recall ≥0,99/0,95; abstention precision/recall ≥0,99/0,98,
  reason accuracy ≥0,95. Calibration fit dev và pin trước held-out; các gate
  calibration còn lại giữ nguyên contract, không thay bằng số trên bộ owner.
- Khóa candidate/config/index trước đo, lưu predictions/RPC thật; không dùng gold
  trong inference. Nếu xem kết quả rồi sửa runtime/tuning, ghi exposure và dùng
  fresh holdout khác cho lần chứng nhận public tiếp theo.

| Nhóm | Việc còn lại |
|---|---|
| Chất lượng câu trả lời — FIX-05 | Đã có đủ 60 lượt gốc trên một code; còn chấm semantic, xử lý C04, điều kiện thiếu và review rubric/gold |
| Gold F24 | Nguồn đã xem nói không vượt quá 15 giờ/tuần cho học phần học tập trung; chưa chứng minh từng học kỳ ít nhất 15 tuần như gold. Giữ trạng thái cần review |
| Nguồn mơ hồ | N03 không nêu trường; khi chọn cả ba PDF không được dùng nhãn trường trong CSV để ngầm định hướng inference |
| PDF/OCR — QA-07c | FIX-03b/QA-03b DONE theo scope trên; còn đo accuracy với reference được review, không dùng OCR confidence thay accuracy |
| Provider — R-01/R-02 | Qualification trên `3289f41f` PASS; không thay nghiệm thu chất lượng/bàn giao toàn bộ candidate sau bản vá |
| Streaming — QA-08c | Mục tiêu p95 TTFT ≤5s chưa được nghiệm thu; giữ OFF mặc định |
| Phát hành local — Phase 13/14 | Cài sạch, khóa RC, holdout, backup/restore/rollback và vòng kiểm cuối còn mở |

Phase 5 DONE nội bộ và các sửa lỗi riêng vẫn giữ nguyên phạm vi lịch sử.
Đợt dọn file không chuyển các mục đang mở thành PASS.

## 4. Phạm vi dọn dự án

Theo yêu cầu của chủ dự án, đã loại các thành phần không tham gia vận hành web
app local: bộ kiểm thử và fixture; mã benchmark/đánh giá/nghiệm thu cũ; dữ liệu
benchmark/corpus dùng thử; JSON/XML/log/ảnh/bundle kết quả; tài liệu phase và
nhật ký trùng lặp; model LLM thử nghiệm; cache tải gói; môi trường Python và
model đóng gói thử; thư mục tạm và kho raw artifact.

Giữ backend/UI, script launcher/setup/đóng gói, profile đang dùng và fallback,
manifest model/OCR, dependency lock, hướng dẫn cài, giấy phép, README, roadmap
và quy tắc repository. Dữ liệu PDF/index/job/cache/quota người dùng được giữ,
kể cả kho local trước đây. `.env` và file key vẫn ở local, được Git ignore.

Đầu ra local không có trong Git đã bị xóa và không còn cơ chế restore artifact
cũ. File từng commit có thể xem trong lịch sử Git. Không viết lại hoặc xóa
lịch sử Git trong đợt này. Muốn tái đánh giá phải chuẩn bị bộ đo phù hợp và ghi
kết quả mới; các con số trong mục 2 chỉ còn là bản tổng hợp lịch sử.

## 5. Dung lượng và xác minh sau dọn

| Thành phần | Trước dọn | Sau dọn |
|---|---:|---:|
| Toàn dự án, gồm môi trường/model/Git | Khoảng 46,31 GB | Khoảng 8,02 GB |
| Python `.venv` đang dùng | 5,15 GB | Giữ nguyên |
| Encoder BGE-M3 đang dùng | 2,29 GB | Giữ nguyên |
| PDF, index và state người dùng còn giữ | — | Khoảng 196 MB |
| Lịch sử Git | Khoảng 380 MB | Giữ nguyên, tăng nhẹ sau commit |
| Ngôn ngữ OCR đang dùng | 4,64 MB | Giữ nguyên |

GB/MB dùng hệ thập phân, tổng kích thước file logic đã đọc được. Một số fixture
bị chặn quyền trước khi khôi phục quyền và xóa nên số trước dọn là xấp xỉ.
Dung lượng trống ổ D tăng khoảng 39,1 GB tại thời điểm đo; có thể chịu tác động
từ hoạt động khác trên cùng ổ. Không cộng hai cách đo thành dung lượng tiết
kiệm. Source, UI, lock và tài liệu chỉ khoảng vài MB; phần lớn 8 GB còn lại
phục vụ runtime trên máy.

Xác minh ngày 31/10/2026:

- **126 bài kiểm tra liên quan PASS** trước khi bỏ bộ test cũ: launcher,
  state/model, HTTP/document API, routing Gemini và OCR nền.
- Tiến trình mới tải được encoder thật; preflight với port trống đạt
  **PREREQUISITES_PASS**, gồm checksum encoder/OCR. Check port 8000 khi app
  đang mở báo `port_in_use`, đúng với server đang hoạt động.
- Đã dừng server cũ để bỏ log bị giữ mở, rồi khởi động lại bằng
  `scripts.operations.local`, cùng `.env`, model và dữ liệu hiện có.
- **9/9 yêu cầu HTTP sau restart trả 200**: health, trang chính, bốn CSS,
  JavaScript chính/chat và API tài liệu. API vẫn nhận đủ **3 tài liệu**, AI
  đã cấu hình, streaming OFF. Không gọi Gemini để tạo báo cáo này.
- Đã đối chiếu SHA-256 của 732 file được bảo vệ sau đợt xóa. Chỉ journal
  SQLite đang hoạt động đổi hash; model, PDF/index, credentials/config và
  source trong lần đối chiếu đó giữ nguyên. Quota/cooldown không bị xóa.
- `uv lock --check --offline` đạt; lockfile dependency không đổi.

Trong lúc dọn có công việc khác tiếp tục sửa runtime và tạo lại
`tests/test_institution_context.py`. Các thay đổi mới này được giữ nguyên;
file test mới thuộc công việc đang diễn ra, không phải bộ nghiệm thu lịch sử.
Không xóa lặp lại file đang được tạo bởi công việc hiện hành.

Các bước trên xác nhận khởi động và các đường đọc cơ bản sau dọn; chưa thay
nghiệm thu chất lượng câu trả lời hoặc tốc độ provider trong mục 3.

## 6. Giữ dự án gọn về sau

**FIX-09, 31/10:** Web xác định tên/viết tắt trường từ metadata và nội dung nguồn,
không dùng danh sách trường hoặc câu trả lời cố định. Chỉ hỏi xác minh trường khi
câu hỏi về quy định còn mơ hồ giữa các nguồn; affiliation trong sách/bài báo không
biến tài liệu đó thành quy chế. PDF thông thường tiếp tục truy hồi nội dung.
Xác nhận tên trường và đổi trường giữ lại câu hỏi gốc trong lịch sử có giới hạn.
25 tests liên quan PASS (15 mới và 10 tương thích trước đó; 1 test cũ không chạy
do phụ thuộc fixture đã dọn). Không phải full regression. HTTP local ba lượt:
hỏi trường 0,166s; NUAE trả A/3,7 trong 0,150s (cache); đổi Bách khoa trả A/4,0
trong 0,262s (không cache), citation đúng từng PDF. Đây là kiểm tra luồng cụ thể,
không phải đo chất lượng trên mọi PDF hay nghiệm thu toàn bộ bản phát hành.

**FIX-09b, 31/10:** Bổ sung đối chiếu viết tắt chưa có trong PDF qua Gemini hiện
cấu hình, tối đa một lượt phân loại cho một viết tắt và bộ nguồn; chỉ gửi viết
tắt và các tên trường lấy từ nguồn được chọn. Chỉ chấp nhận một candidate hợp lệ
được model xác nhận là alias/name variant, không chọn tên gần giống nhất. Tri
thức model ở bước này chỉ dùng chọn nguồn; câu trả lời vẫn phải kiểm chứng bằng
PDF và citation. Kết quả nhớ tạm 5 phút, phân biệt bộ nguồn; lỗi dịch vụ giữ 30
giây để tránh gọi dồn. Không thêm retry, key hoặc reset quota.

Kết quả chưa rõ thì app giải thích thông tin còn thiếu, liệt kê tên trường từ
PDF và hỏi tên đầy đủ/chọn nguồn. API lỗi được báo riêng. Xác nhận lại không làm
mất câu hỏi gốc. Prompt và thông báo phân biệt thiếu phạm vi người dùng với thiếu
bằng chứng nguồn; không mặc định mọi PDF là tài liệu đại học.

44 tests liên quan PASS (34 hiện tại và 10 tương thích từ mốc `f9d8ba10`; 1 test
cũ phụ thuộc fixture đã dọn không chạy), gồm alias được xác nhận, mơ hồ/unknown, kết quả sai schema/ngoài
scope, lỗi API, cache theo nguồn và hướng dẫn bổ sung thông tin. HTTP thật với
3 PDF: câu hỏi gốc → `hust` → `HUST` → `Hust`; cả ba câu trả lời tiếp tục quy đổi
điểm và chỉ trích PDF Bách khoa Hà Nội. Thời gian 2,554s / 0,644s / 0,736s;
metric đối chiếu tăng đúng 1, không lỗi, khoảng 1,21 giây. Các số này là kiểm tra luồng
cụ thể, không phải full regression hay accuracy cho mọi tên trường/PDF.

**FIX-11, 31/10 — Hội thoại liền mạch:** Client giữ ý định câu hỏi đã giải quyết
theo cuộc chat, bộ PDF và ngôn ngữ, thay vì chỉ dựa vào 6 tin gần nhất. Ý định
được giữ riêng với câu trả lời/citation; lịch sử chat không trở thành bằng chứng
nguồn. Chat mới xóa bộ nhớ. Câu hỏi ngắn đổi trường được viết lại giữ thuộc tính
đang hỏi và thay tên nguồn cũ; hỗ trợ alias nằm trong cả câu hỏi đầy đủ. Mơ hồ
về đối tượng so sánh vẫn hỏi lại, không tự suy đoán.

Tái dùng chỉ câu trả lời dương tính đã được cache kiểm chứng chấp nhận, khi câu
hỏi đã đủ nghĩa và nêu rõ trường, cùng PDF/corpus, model, cấu hình và ngôn ngữ.
Câu cá nhân, trích đoạn đang chọn, câu còn phụ thuộc ngữ cảnh và câu trả lời
chưa xác minh không dùng cơ chế này. Policy cache của các phase khác vẫn giữ
qua opt-in web; context policy đổi sang `request-context-v13` để tránh dùng lại
cách mở rộng lịch sử cũ. Không đổi ngưỡng grounding hoặc citation.

Kiểm tra: 52 tests hiện tại + 91 tests tương thích từ `f9d8ba10` = 143 PASS.
Một assert phiên bản cache của test cũ được chuyển v12 → v13; logic/ngưỡng khác
giữ nguyên. Có 120 lần đổi trường và 250 lượt hội thoại **giả lập**, kiểm tra
đổi chủ đề, reset chat, cô lập nguồn, giữ trường qua 15 câu mới không nhắc tên
và không đưa câu trả lời AI thành user intent.
Đây là focused regression, không phải full regression hay 250 inference thật.

HTTP thật nguyên ví dụ: “quy định của hust là gì” → “còn nuae thì sao” → “còn
hust thì sao”; cả ba trả lời đúng nguồn HUST/NUAE/HUST, citation lần lượt trang
5 / 84,85,109 / 5. Lượt cuối 2,952s / 0,548s / 0,910s, **cả ba dùng câu trả lời
đã kiểm chứng trong cache**; lượt đầu vẫn đối chiếu alias qua Gemini. Các lượt
sinh câu trả lời trước đó đo 10,606s cho HUST và 8,384s cho NUAE. Không coi số
cache warm này là latency inference mới hoặc accuracy cho mọi hội thoại.

Tiếp tục thêm 6 câu mới về quy đổi điểm, không nhắc tên trường trong câu hỏi:
6/6 trả lời từ PDF HUST, vẫn giữ trường khi câu nhắc HUST ban đầu đã ra khỏi
6 tin gần nhất. Các câu dùng phép chiếu bảng nguồn (`grade0/grade1`), hoàn tất
trong 1,014–1,325s; đây không phải 6 inference Gemini mới.

Thiết kế tham khảo [bộ nhớ theo thread của LangChain](https://docs.langchain.com/oss/python/langchain/short-term-memory),
[query rewriting trong RAG nhiều lượt của NVIDIA](https://docs.nvidia.com/rag/latest/multiturn.html)
và [cách lưu/truy hồi memory của Supermemory](https://supermemory.ai/docs/concepts/how-it-works).
Phần triển khai hiện dùng state local và Gemini sẵn có; chưa tích hợp dịch vụ
Supermemory hay huấn luyện thêm RNN. FIX-05 và nghiệm thu release cuối vẫn mở.

Không commit PDF cá nhân, model, môi trường Python, database, cache hoặc log.
Chỉ tạo đầu ra chẩn đoán khi xử lý sự cố cụ thể và xóa khi xong. Kết quả cần
lưu lâu dài cập nhật ngắn gọn vào chính báo cáo này; các bước còn làm cập nhật
vào `plan.md`. Đường dẫn dữ liệu do `.env` chọn phải được kiểm tra trước mọi
lần dọn thư mục.
