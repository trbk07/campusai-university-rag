# CampusAI — Roadmap local

Cập nhật: **09/11/2026 · Asia/Bangkok**.

## Trạng thái

Web app MVP có upload PDF, OCR nền/checkpoint, truy hồi hybrid, hỏi đáp có
citation, hội thoại và quản lý tài liệu. Phase 5 hoàn tất nội bộ; Phase 7/8
đóng theo phạm vi Chat-quality của chủ dự án. Chưa nghiệm thu bản phát hành cuối.
Bộ Golden 100 gần nhất: **68/100** (32 FAIL,0 BLOCKED; lượt R15),
chưa đạt mục tiêu ≥95%; không đổi trạng thái
lịch sử thành một chứng nhận chất lượng tổng quát.
Gemini Chat đã review đủ100 output R15: **81 PASS/19 FAIL** theo cách chấm
nguồn của reviewer. Đây là chấm lại bản cũ, có khác biệt gold/rubric; không
thay điểm strict68/100 hoặc chứng minh accuracy của code hiện hành.

Theo yêu cầu ngày 31/10, các báo cáo được gom tại
[báo cáo tổng quan](docs/PROJECT_OVERVIEW.md); log, bộ kiểm thử, benchmark và
artifact nghiệm thu cũ đã bỏ khỏi cây làm việc. Mốc công việc dưới đây giữ
trạng thái lịch sử. Muốn chứng nhận lại cần bằng chứng mới khớp source được
chọn; không dựa vào đường dẫn artifact đã xóa.

## Nền cải thiện hiện hành — 09/11/2026

**Yêu cầu tổng quát hóa của owner:** mục tiêu ≥95% áp dụng cả PDF mới ngoài các tài liệu đại học đã dùng để phát triển. Không hard-code câu hỏi, đáp án, tên trường hoặc cấu trúc PDF cố định. Cần đánh giá riêng trên nguồn chưa dùng để sửa code, gồm nhiều lĩnh vực và PDF native/scan/mixed/bảng. Khi nguồn không đủ thông tin, mâu thuẫn hoặc không đọc được, phản hồi phải nói đúng giới hạn và yêu cầu làm rõ khi cần. Điểm của bốn PDF hiện tại không chứng minh accuracy ≥95% với mọi PDF.

- [ ] **GENERALIZATION-95 — Xác minh trên PDF mới:** đóng băng tập nguồn/câu hỏi/rubric trước đo; kiểm nội dung, citation, số liệu/mã quan trọng, hội thoại và từ chối đúng. Chưa có kết quả native đủ chứng minh ≥95% trên nguồn mới. Giữ nguyên khóa câu đã hỏi và không ghép điểm nhiều candidate.

- [x] **BASE-70 — Khôi phục theo yêu cầu owner:** đã đưa code, scripts và tests về đúng `962a147534bfc9dcbfb84655fa980d94cfcef58e` trước khi cải thiện tiếp; **480 tests PASS**. Đây là bản gắn với review Gemini Chat **69/100 (khoảng 70%)**, còn lỗi binding/quote/trang nên không gọi là accuracy đã chứng nhận. Không đổi gold, rubric hoặc điểm lịch sử.
- [x] **Bảo toàn công việc:** các commit sau mốc này giữ ở nhánh local `archive/rag95-before-return-20261109`; thay đổi chưa commit lưu tại `.tmp/rag95-return-962a1475/before-return.patch`. Giữ nguyên tài liệu, index, raw predictions và question lock registry. Không push.
- [x] **BASE-70-01 — Nhận diện nguồn linh hoạt:** bổ sung kiểm tra tên/alias theo toàn câu khi scope chưa rõ, chỉ đối chiếu tên từ nguồn được phép; tên trả về phải là substring thực của câu hỏi. Không chọn gần đúng hoặc lấy chủ đề làm tên trường; kết quả không chắc vẫn hỏi lại. Cache alias đã xác nhận dùng được ở vị trí ngữ pháp khác, gắn với cùng tập nguồn; kiểm thử bằng trường giả định và model kiểm soát, không gọi API thật.
- [x] **BASE-70-02 — Tái sử dụng OCR đúng trang:** đưa lại riêng sửa chữa `01b342d8` và regression tương ứng để PDF scan đã xử lý hoàn tất không bị từ chối chỉ vì metadata cũ thiếu `readable_pages`. Vẫn kiểm status/version/coverage/trang OCR và quyền nguồn, không đọc bù từ trang khác.
- [x] **BASE-70-03 — Hồi quy trên nền đã cải thiện:** **512 PASS / 0 FAIL / 0 SKIP (19,90s)**; không gửi lại câu đã khóa hoặc gọi Gemini. Chỉ bốn file source/test khác nền `962a1475`. Các task DONE sau mốc này bên dưới là lịch sử nhánh lưu, không tự coi tính năng đó còn hoạt động trên nền đã khôi phục.
- [x] **BASE-70-04 — Giữ nghĩa câu hỏi và chủ đề hội thoại:** đưa lại riêng phần chuẩn hóa ngôn ngữ của `7b5494aa` và phần ngữ cảnh của `84aaf647`, không đưa lại thử nghiệm ưu tiên literal ranking. “ai” hỏi người không bị mở rộng thành Artificial Intelligence; đồng ý/đóng tiền không thành deadline; đăng ký tạm trú/chữ ký không thành học kỳ. Follow-up “vừa nói/đã đề cập/vẫn … đó” giữ chuỗi chủ đề từ user, không lấy câu trả lời assistant làm bằng chứng. **544 PASS / 0 FAIL / 0 SKIP (20,71s)**.
- [x] **BASE-70-05 — Kiểm tra cơ chế bằng dữ liệu đã lưu:** 19/112 input cũ được loại phần mở rộng sai; lượt 3 CTX nghiên cứu giữ lại chủ đề user. Đã chạy so sánh hybrid thật trên cùng index gốc cho 4 input, dùng encoder local đã pin/GPU/CPU một luồng, không gọi Gemini. Lưu vào `post_restore_language_audit_20261109` trong results hiện có; đây không phải câu trả lời mới hoặc accuracy. Phương án đưa cụm từ hiếm lên đầu đã bị loại vì làm mất bộ citation của 4 câu dương tính cũ; không ship hoặc đổi rubric để che hồi quy.
- [x] **BASE-70-06 — Phân biệt tên nguồn và ngữ pháp:** khi một nguồn đã được nêu rõ nhưng parser coi động từ sau “trường/school” là tên mới, kiểm tra cả câu với schema giới hạn; chỉ chấp nhận source đã có thật trong câu và cùng candidate được phép. Mask chỉ dùng cho phân tích danh tính; giữ nguyên câu hỏi cho vấn đáp, không cache động từ thành alias. Hỗ trợ động từ có dấu/cuối câu; không ghép tên qua dấu phẩy, không coi từ nằm trong tên trường viết hoa là acronym mới. Kiểm từng tên trường trong cùng mệnh đề để tên đã biết không che tên chưa rõ. Code đã hồi quy; hai ca “xét/xếp” trong audit input cũ còn cần quyết định model thật, không được tính thành prediction PASS mới.
- [x] **GENERALIZATION-01 — Định tuyến PDF bất kỳ:** đưa lại riêng phần tên file/miền kỹ thuật của `e7888b49`; hỗ trợ tên có khoảng trắng, Unicode, số/mã, trùng tên và file ngoài quyền. Không lấy “trường dữ liệu/môi trường” hoặc acronym trong chính sách doanh nghiệp làm tên đại học. Follow-up đổi PDF giữ chủ đề nhưng thay phạm vi file cũ; so sánh vẫn giữ hai nguồn và không được trả lời một nguồn thay cả hai. Cập nhật cache policy để không trả lại câu trả lời đã cache trước sửa kiểm nguồn.
- [x] **GENERALIZATION-02 — Kiểm cơ chế trên PDF kỹ thuật thật:** truy hồi BM25 thực tế từ `CSDL1.pdf`, `13StacksAndQueues.pdf`, `14AnalysisOfAlgorithms.pdf` trong kho đã upload; kiểm hash PDF, đúng nguồn được chọn và giữ nguyên chunk/text/trang. File không được chọn bị chặn. Lưu trong `rag95.generalization_local_scope_checks_20261109` của results hiện có; 0 Gemini calls, chưa phải accuracy hỏi đáp. Toàn bộ hồi quy trên source cuối: **619 PASS / 0 FAIL / 0 SKIP (20,86s)**.
- [x] **GENERALIZATION-03 — Không gán miền sai cho “duration”:** câu hỏi thời hạn bảo hành, hợp đồng hoặc thời lượng phép thử không bị tự thêm “thời gian đào tạo”; giữ mở rộng học thuật khi câu hỏi nêu training/đào tạo thật. Không dùng tên file hoặc đáp án benchmark để chọn miền.
- [x] **GENERALIZATION-04 — Metadata gắn nhãn và đúng bằng chứng:** đưa lại riêng cơ chế metadata/cache có nguồn của `2a00608b`, nâng lên `source-labelled-v3-field-provenance`. Không lấy mã trong văn bản pháp luật, hàng catalogue, dấu chấm của biểu mẫu hoặc câu văn làm mã môn/chương trình/phiên bản toàn tài liệu. Nhãn có bằng chứng trỏ đúng trang chứa nhãn, không lấy một lần xuất hiện cùng giá trị ở trang trước; hỗ trợ chữ hoa/thường của mã được in thật. Giữ đọc được journal producer cũ nhưng tạo identity mới cho công việc mới.
- [x] **GENERALIZATION-05 — Nâng metadata không quét lại PDF:** cache có provenance/trang hợp lệ được cập nhật nhãn, giữ nguyên body, bảng, chunk ID và citation. Nếu header sinh tự động dài hơn, chỉ dùng header tọa độ ngắn, giữ đầy đủ metadata riêng và giới hạn chunk 2.400 ký tự. Audit chỉ đọc 4 nguồn gốc xác nhận **1.585 chunks** được giữ nguyên body/citation/table, 8 header cần rút gọn; không sửa PDF, cache/index cũ hoặc native predictions, 0 OCR/API calls. Test migration qua API ingest cũng chặn mọi lần gọi parser/OCR lại. **650 PASS / 0 FAIL / 0 SKIP (22,63s)**. Audit trong `rag95.source_metadata_upgrade_20261109` của results hiện có, chưa phải accuracy mới.
- [x] **GENERALIZATION-06 — Bằng chứng độc lập cho từng PDF:** so sánh/mô tả 3–5 PDF không bị chặn bởi giới hạn của engine phép tính hai nguồn. Mỗi file được yêu cầu phải có citation riêng, kể cả cùng trường/nhà xuất bản; không dùng một file thay cho cả nhóm. Câu hỏi chỉ yêu cầu ít nhất một nguồn được xử lý theo đúng lượng từ. Engine phép tính/hop có giới hạn riêng vẫn fail closed.
- [x] **GENERALIZATION-07 — Cú pháp file và câu hỏi ngắn:** nhận đủ tên PDF trước dấu chấm cuối câu; không chọn nhầm prefix khi có extension/suffix khác; hỗ trợ apostrophe trong tên file và cặp dấu nháy đúng. Câu hỏi ngắn đã nêu file và thuộc tính không bị chặn chỉ vì thiếu từ “and”; yêu cầu chưa nêu nội dung cần so sánh vẫn hỏi lại.
- [x] **GENERALIZATION-08 — Prompt trung lập lĩnh vực:** vai trò hỏi đáp tài liệu, không mặc định PDF là quy chế đại học. Giữ nguyên yêu cầu chỉ dùng bằng chứng, schema, claim/citation và ngưỡng kiểm chứng. **673 PASS / 0 FAIL / 0 SKIP (21,39s)** trên source cuối; chưa phải accuracy model mới.
- [ ] **GENERALIZATION-09 — Đo chẩn đoán mới qua app thật:** chuẩn bị câu chưa từng hỏi trên PDF kỹ thuật ngoài bộ đại học, khóa source/index/profile và protocol trước gửi. Không tái dùng câu đã thử, không dùng gold/nhãn làm input inference; tách rõ chẩn đoán nhỏ khỏi nghiệm thu ≥95% và fresh holdout. Không thay bằng điểm unit test.
  Lượt trên `db90e42` đã lưu **14/20 lượt**, **23 POSTs**, 17 inference thành công; sử dụng đủ 6 project, không dồn một key. Dừng ở timeout `TECH-C01` lượt 2 theo protocol; 6 lượt chưa chạy, không gửi lại câu đã thử. p95 **11,642s**; đây là chẩn đoán chưa đủ bộ, **không có accuracy mới**. Còn false abstention ở câu code/thuật toán/đánh đổi và câu tính tỷ lệ trả thiếu. Kết quả, raw trace và phạm vi trong `generalization_diagnostic_20261109` của results hiện có.
- [x] **GENERALIZATION-09a — Nguồn chẩn đoán ngoài đại học:** đọc đủ **59 + 65 trang** của hai PDF kỹ thuật, OCR bổ sung phần thiếu, tạo index hybrid riêng với encoder pin. Giữ nguyên PDF, kho/index người dùng và index lịch sử; câu hỏi không trùng registry/journal, gold không đi vào server inference. Không coi đây là fresh holdout độc lập.
- [x] **GENERALIZATION-10 — Tọa độ từng mảnh chunk:** mảnh sau khi chia không còn mặc định lấy trang đầu/dải trang của toàn section; ánh xạ offset về trang vật lý, giữ overlap và điều kiện xuyên trang. Không tìm được ánh xạ thì giữ dải bảo thủ. Nâng producer version và giữ đọc được receipt v7/metadata v3. Audit trước–sau trên hai PDF thật không đổi kho từ nguồn; index/native outputs cũ không bị sửa.
- [x] **GENERALIZATION-11 — Không nhầm số trong tên file thành số liệu:** chỉ mask nguyên tên PDF đã được câu hỏi nêu và citation xác thực. Số đứng riêng, file khác hoặc suffix giả vẫn bị kiểm nguồn. Replay offline nguyên draft `TECH-F03` đã lưu nay qua grounding; không gửi lại câu và không đổi điểm native. Bản sửa cuối: **677 PASS / 0 FAIL / 0 SKIP (27,75s)**; chưa phải accuracy model mới.
- [x] **GENERALIZATION-12 — Định danh kỹ thuật có số:** phân biệt số trong định danh được in ở dòng thuật toán/quy trình/tiêu chuẩn với số liệu thật. Chỉ áp dụng khi đúng định danh cũng xuất hiện trong câu hỏi và quote đã kiểm nguồn; số đứng riêng, định danh khác, suffix khác và lượng có đơn vị vẫn phải được chứng minh. Replay so sánh 17 draft đã lưu chỉ thay đổi hai draft của `TECH-F08` từ từ chối nhầm sang trả lời; các kết quả khác không đổi. Không gọi lại model hoặc sửa điểm native.
- [x] **GENERALIZATION-13 — Không cắt ví dụ ở dòng dữ liệu:** dãy số và phép gán/so sánh biến đơn giản không bị nhận thành heading, kể cả font lớn/đậm; giữ tiêu đề đánh số thật. Đối chiếu trực tiếp trang 11 PDF thuật toán: trước sửa ví dụ và output bị chia hai chunks, sau sửa ở cùng evidence. Nâng version chunker và giữ receipt producer cũ; chưa sửa index lịch sử. **689 PASS / 0 FAIL / 0 SKIP (34,23s)**. Cần index mới và câu chưa hỏi cho phép đo model tiếp theo; không lấy replay/local audit làm accuracy.
- [x] **GENERALIZATION-14 — Phép chia có chứng minh từ bảng:** tính tỷ số khi câu hỏi nêu rõ chiều từ/đến và hai hàng đã được kiểm nguồn đầy đủ trong cùng bảng, cùng cột. Kiểm mọi factor model nêu, làm tròn chỉ khi có nhãn xấp xỉ; số ngoài span phép tính vẫn phải có bằng chứng. Chặn hàng trùng/thiếu, ghép hai nguồn, ô mơ hồ, chia 0 và kết quả sai; không làm tròn tỷ lệ dương nhỏ thành 0. Claim phép tính sinh local, giữ confidence/ngưỡng cũ và giới hạn output. Replay 17 draft chỉ gỡ lỗi draft bảng của `TECH-R04`; draft chỉ cite prose vẫn không được nâng thành proof bảng. **705 PASS / 0 FAIL / 0 SKIP (38,84s)**; helper p95 **0,05ms/lần (1.000 lần đo)** là microbenchmark local, không phải latency app hoặc accuracy mới.
- [x] **GENERALIZATION-15 — Giữ điều kiện khi rút gọn context:** ưu tiên phân số được câu hỏi nêu và phần giải thích ngay sau nó trong đoạn nguồn nguyên văn; phân bổ lại ngân sách trong cùng PDF, không lấy phần của PDF khác, không cắt bảng hay typed field anchors. Không thêm model hoặc tăng prompt. Đối chiếu 80 trace có retrieval: chỉ context `TECH-R01` thay đổi, 54 citation đang nhìn thấy không mất; quy tắc một nửa và giải thích worst-case trước bị cắt nay cùng hiện với quy tắc một phần tư trong 7.900/8.000 ký tự. **715 PASS / 0 FAIL / 0 SKIP (39,06s)**. Đây là audit serializer trên dữ liệu cũ, không phải câu trả lời mới hay điểm accuracy.
- [x] **GENERALIZATION-16 — Candidate nguồn đồng bộ:** khóa code `3459757`, ingest/index riêng đủ 6 PDF/388 trang; mọi trang có marker vật lý và coverage hoàn tất, encoder pin đúng revision. Tái dùng 1.653 vectors có nội dung còn khớp, chỉ encode 142 nội dung mới; giữ nguyên kho người dùng và snapshot cũ. Receipt tại `data/operations/rag95-current-candidate-20261109/preparation.json`.
- [x] **GENERALIZATION-17 — Sửa follow-up quy trình bị lạc nguồn:** lượt native độc lập còn lại đã chạy đủ 5 lượt/3 case trên `3459757`, 6 inference/6 POSTs, mỗi project 1 call, 0 lỗi provider/HTTP. Review nguồn của developer: 4 lượt đúng, 1 lượt FAIL do mất chủ đề và trả từ NUAE thay PDF thuật toán; tính theo case là 2 PASS/1 FAIL, không phải overall accuracy. p95 17,875s; không công nhận gate tốc độ. Sau đo, sửa tham chiếu bước trước/sau/kế tiếp bằng topic từ user; quy trình/file mới được nêu rõ không kéo topic cũ, không dùng lời assistant làm evidence, thiếu antecedent thì hỏi lại. Local hybrid trên index thật chỉ còn đúng source và có bước verify; wrong draft cũ bị chặn khi replay trên source đúng. **728 PASS / 0 FAIL / 0 SKIP (12,51s)**. Không gửi lại câu, không đổi native FAIL thành PASS; evidence trong `current_candidate_remaining_20261109` của results hiện có.
- [x] **GENERALIZATION-18 — Feedback sửa câu trả lời cụ thể:** lượt repair duy nhất nhận lỗi số/đơn vị/định danh hoặc claim chưa được chứng minh, cùng bản nháp có nhãn untrusted, thay vì chỉ mã lỗi chung. Không đưa đáp án thay thế vào feedback; không nới verifier, tăng số lượt sinh hoặc đưa diagnostics vào API/cache công khai. Replay `TECH-R02` xác nhận báo đúng 8/32 chưa nằm trong verified claims; bản repair sai cũ vẫn bị chặn, không đổi điểm native. Test kiểm một lần sửa, câu hợp lệ chỉ một lần sinh, feedback giới hạn và public schema giữ nguyên: **732 PASS / 0 FAIL / 0 SKIP (14,30s)**. Hiệu quả trên model thật cần lượt đo mới bằng câu chưa hỏi.
- [ ] **RAG-95 — Mục tiêu vẫn ≥95%:** cần phép đo câu trả lời thực tế trên cùng candidate/rubric; mốc cải thiện phải >70%. Chưa có accuracy native của bản vừa sửa. Không ghép điểm các candidate, không gửi lại câu đã khóa. Review offline hoặc unit tests không phải accuracy mới.

## Goal RAG-95 — IN PROGRESS

**Ưu tiên hiện hành 08/11:** tập trung nâng accuracy thực tế lên≥95%, giữ nguyên grounding/an toàn và các gate. Theo chỉ đạo mới của owner, **chỉ push GitHub khi toàn bộ goal có bằng chứng DONE**; các sửa chữa tiếp theo làm và kiểm thử local. Không push các task riêng lẻ trong lúc goal chưa hoàn thành.

**Chỉ đạo mới 05/11 — khóa câu đã test:** đã lưu112 hash câu hỏi từng được gửi (1.228 bản ghi attempt), gồm cả PASS/FAIL/lỗi provider. Chỉ chấm offline output cũ; không tự mở lại vòng Golden100 hoặc gửi lại câu đã khóa. Các kế hoạch cũ nói chạy lại full100 được thay bằng chỉ đạo này. Lượt live tiếp theo phải dùng câu mới, báo riêng; không ghép điểm nhiều candidate.

**Goal hiện hành do owner cập nhật:** CampusAI RAG Accuracy **≥95%**. Xác minh bằng câu trả lời thực tế trên candidate đã khóa và đối chiếu PDF nguồn; giữ đúng mẫu số, grounding/citation và lịch sử câu đã hỏi. Không dùng test PASS hoặc replay offline thay accuracy.

Các gate Golden/fresh blind holdout≥200 câu của kế hoạch nghiệm thu tổng quát vẫn được giữ ở task tương ứng và chưa PASS; không tự ghi thành kết quả đã hoàn thành khi owner rút gọn objective hiện tại.
Mốc xuất phát:48/100 trên `0a96fe4b`;305 tests PASS và một targeted PASS trên
`ba2dfd34`. Các task DONE phía dưới giữ nguyên, không ghép kết quả nhiều bản.

- [x] **RAG-95-01 — Audit FAIL DONE:** đọc52 ca FAIL, raw traces và ma trận
  nguyên nhân trong báo cáo Golden100; xác định nhóm chọn nguồn, đoạn nguồn
  thiếu điều kiện, ngữ cảnh/so sánh, OCR và false abstention. Lượt goal trước
  được phân loại **progress**: có code, native evidence và commit thực tế.
- [ ] **RAG-95-01a — Review nguồn/fixture riêng:** đã chuẩn bị10 ca thiếu rõ
  phạm vi hoặc có vấn đề gold/locator, kèm text54 trang nguồn. Đã nhận review AI
  nhưng chưa đủ căn cứ phê duyệt: chưa giải quyết scope, FACT15 suy luận sai,
  NAT15 tự mâu thuẫn và2 ca không khớp quote/trang. Giữ nguyên gold/điểm gốc.
- [x] **RAG-95-01b — Thu review độc lập DONE:** đúng1 POST đã duyệt, nhận đủ10
  records; lưu raw response, prompt, nguồn/hash và audit trong evidence đang có.
  Đây là receipt AI, không tự chuyển verdict thành approval hoặc fresh holdout.
- [ ] **RAG-95-02 — Routing/intent:** nguồn duy nhất theo mã/chương trình được
  in trong PDF; không bỏ sót một vế tên trường/alias trong câu so sánh; hiểu
  câu hỏi vị trí, viết tắt, không dấu và follow-up. Không whitelist benchmark.
  Batch1 đã triển khai: anchor từ code/heading nguồn, alias ở cả hai vế,
  đại từ chỉ trường và contact có nhãn trong prose/bảng; **317 tests PASS**.
  Đã đo đủ100 ca/112 lượt trên `b6bf27e4`: **56 PASS/44 FAIL**,96 inference thật,
  0 lỗi HTTP/timeout/cache, p95 **8,098s**. Đây là dev review, chưa đạt95%.
  Batch2 đã sửa xác nhận nguồn, viết tắt vượt ranh giới tên trường và recall
  mệnh đề/ngưỡng có nguồn; kết quả đủ100 ca ở RAG-95-05b. Không mở lại task DONE.
- [x] **RAG-95-02a — Code batch2 DONE (`eb485c16`):** xác nhận nguồn không gọi
  model giới thiệu; giữ câu hỏi chờ và trường ở lượt tiếp theo; bỏ alias cắt qua
  tiền tố tên trường; truy hồi mệnh đề nguồn và giữ trong context; chặn heading
  học kỳ không in trong chunk. **327 tests PASS**, secret scan/diff check PASS,
  đã push origin CampusAI. Đây là DONE code/hồi quy, không phải accuracy95%.
- [ ] **RAG-95-03 — Retrieval/grounding:** giữ trọn điều kiện, ngoại lệ và quan
  hệ bảng/học kỳ; trả lời đủ nguồn trong so sánh, giảm false abstention.
- [x] **RAG-95-03a — Code batch3 DONE:** nối các phần của viết tắt hoàn chỉnh
  lấy từ tên nguồn; prompt hiểu câu so sánh nối tiếp; giữ điều kiện đã được
  kiểm chứng trong câu trả lời; đọc nhóm điều kiện đóng bằng heading cùng cấp;
  truy hồi điều khoản cải thiện điểm của từng nguồn và giữ phần điều kiện sau
  mệnh đề trong context. **356 tests PASS (18,97s)**, secret scan/diff check PASS.
  Replay local trên output cũ chỉ kiểm cơ chế, không tính là prediction hoặc điểm mới.
- [x] **RAG-95-03b — Code batch4 DONE (`daae9bcb`):** chọn nguồn từ tiêu đề
  mục/điều và trang người dùng nêu, kể cả mapping dạng danh sách; giữ ambiguity
  khi nhiều nguồn trùng hoặc có nguồn chưa đọc. Sửa CPA có dấu phẩy ngăn mệnh đề,
  chứng minh tỷ lệ phần trăm được làm tròn và đổi thứ tự diễn đạt; tên trường
  có cụm “đối với”; giữ kết quả/ngoại lệ trong một mục quyền hạn ngắn đã đóng.
  **376 tests PASS (20,95s),0 SKIP** trên repo chính; secret scan/diff check PASS.
  Không thêm lookup benchmark; điểm100 ca trên code batch4 nằm ở RAG-95-05d.
- [x] **RAG-95-03c — Sửa pipeline batch5 DONE (`5e8ea511`):** thống nhất chứng
  minh số liệu đầu vào của người dùng giữa lớp trình bày và kiểm nguồn; chỉ
  chứng minh trong đúng nguồn sở hữu, không miễn kiểm tra số liệu giữa các PDF.
  Giữ học kỳ khi người dùng nêu số tín chỉ đăng ký; giữ điều kiện/ngoại lệ từ
  cấu trúc mục nguồn đã đóng. Phân bổ context theo tài liệu thay vì số chunk,
  giữ nguyên bảng và giới hạn8.000 ký tự. **389 PASS/0 FAIL/0 SKIP (17,08s)**;
  secret scan/diff check PASS. Không thêm dependency/model, không đổi gold/PDF/index.
  Học cách tách chẩn đoán retrieval/generation của RAGChecker, giữ cấu trúc nguồn
  của Docling và citation truy vết của RAGFlow; không chuyển cả framework nặng.
  Replay offline chỉ kiểm cơ chế; OCR04 còn thiếu nội dung, chưa ghi accuracy mới.
- [x] **RAG-95-03d — Chặn khẳng định thiếu thông tin sai DONE:** phát hiện
  tuyên bố nguồn không đề cập ở ranh giới mệnh đề, kể cả bên trong câu so sánh;
  chuyển về kiểm đủ nguồn thay vì công bố thành câu trả lời dương tính.
  Không thêm tên trường, giá trị hoặc câu benchmark vào runtime. **400 tests
  PASS/0 SKIP (20,57s)**, secret scan/diff check PASS. Replay đúng bản nháp lỗi
  CTX06-L3 đã bị chặn,0 lời gọi model mới; chưa tính thành prediction/accuracy mới.
- [x] **RAG-95-03e — Tính phép áp dụng ngưỡng phần trăm DONE:** khi người dùng
  nêu rõ hai số, câu trả lời gốc đã qua grounding và một trích dẫn duy nhất chứng
  minh ngưỡng, hệ thống bổ sung phép tính chính xác; chỉ công bố khi kết luận model
  khớp phép so sánh. Không suy rộng thành kết luận đủ mọi điều kiện. **402 tests
  PASS (16,40s)** trên commit `5774b20d`; gold/PDF/index/profile giữ nguyên. Native
  accuracy chưa đo lại.
- [x] **RAG-95-03f — Literal course-row and conditional-branch extraction DONE (local):** parse course codes, credits, wrapped names, selection groups, and eligibility branches only from exact retrieved source text; require a same-span citation and explicit semester label for semester-scoped group answers. Four general regression tests pass. Full app/Gemini requalification remains under RAG-95-05g.
- [x] **RAG-95-03g — Giữ điều kiện và hồ sơ đi kèm DONE (local, 05/11):** nhận diện nhóm điều kiện với cả LF/CRLF/CR, giữ nguyên quote gốc và chặn chỉ dẫn chèn trong nguồn; bổ sung danh sách hồ sơ được in ngay sau quy định đã chứng minh, chỉ khi danh sách có ranh giới kết thúc rõ. Replay trace R15 OCR04 giữ lời nhắc kiểm tra các điều kiện khác; NAT17 có đủ đơn, xác nhận cố vấn/Khoa và giấy tờ y tế. Citation được kiểm lại cùng source hash. Đây là replay offline, chưa phải accuracy mới.
- [x] **RAG-95-02b — Phân biệt phạm vi khóa với chọn phiên bản DONE (local, 05/11):** câu hỏi một quy chế đã chọn có áp dụng cho một khóa hay không được đối chiếu với phạm vi in trong chính nguồn, kể cả khóa nằm ngoài phạm vi. Sửa nhận diện “áp dụng đối với các khóa tuyển sinh từ năm”; chỉ nhận metadata khi quote/trang/chunk khớp. Thiếu bằng chứng, nhiều nguồn, xung đột bộ lọc hoặc yêu cầu hiệu lực hiện hành vẫn chặn. Replay NAT11 đã tìm đúng bằng chứng khóa 2025 trên trang 1. Năm test mới và toàn suite **418 PASS**; chờ native requalification tại 05g.
- [ ] **RAG-95-04 — OCR:** sửa cơ chế đọc ký hiệu/bảng/scan từ PDF gốc;
  đo lỗi nhận dạng riêng, không đoán ký tự hoặc sửa golden/PDF để tăng điểm.
- [x] **RAG-95-04a — Chặn dữ liệu lịch OCR bất khả thi DONE:** ngày/tháng/giờ
  sai không được xác minh chỉ vì trùng chuỗi OCR; ngày nhuận và giờ hợp lệ vẫn
  qua kiểm chứng. Thuộc batch4 đã PASS376 tests; không tự sửa hoặc suy ngày thiếu.
  Nhận dạng đúng ký hiệu “+”, số quyết định và người ký vẫn thuộc task04 đang mở.
- [ ] **RAG-95-05 — Đo lại:** sau mỗi nhóm sửa, chạy hồi quy rồi khóa code,
  profile, PDF/index và chạy đủ100 ca/112 lượt qua app/Gemini thật. Luôn giữ
  lỗi, toàn bộ mẫu số, cùng rubric; không chọn lượt tốt nhất hoặc ghép điểm.
- [x] **RAG-95-05a — Đo batch1 DONE:** đủ100 ca, giữ nguyên input/gold/PDF/profile
  và các bước CTX. Lưu toàn bộ raw outputs/citations/traces; không ghép focused runs.
  Phát hiện hai ghi chú chấm cũ sai (CTX05/NAT12), lưu correction riêng;
  không sửa baseline hay tính điểm sửa chấm thành cải thiện nhờ code.
- [x] **RAG-95-05b — Đo batch2 DONE (`eb485c16`):** sau duyệt chính xác scope
  `fae32047…`, chạy đủ112/112 lượt,95 inference Gemini thật; **66 PASS/34 FAIL**,
  0 lỗi HTTP/provider/timeout/cache. PDF/index/profile/source giữ đúng hash.
  Citation audit95 citations:0 lỗi tọa độ/quote, chưa phải semantic precision.
  p50 **4,777s**, p95 **11,352s**; không nhận latency PASS theo mốc10s.
  Golden/locator còn vấn đề giữ FAIL và review riêng; không ghép focused runs.
- [x] **RAG-95-05c — Đo/chấm batch3 DONE (`ca0e9a8c`):** đã gửi112 lượt,
  lưu111 phản hồi; **52 PASS/32 FAIL/16 BLOCKED**,80 lời gọi Gemini thành công,
  15 lượt provider503 và1 lượt REA10 gián đoạn không biết kết quả. Giữ lỗi trong
  mẫu số100; chỉ tiếp tục38 lượt chưa gửi sau khi cả hai tiến trình dừng, không
  retry. CTX giữ đúng phiên/thứ tự. Source/profile/index/baseline đúng hash;
  84 citations không lỗi tọa độ/quote, chưa chứng minh OCR/semantic precision.
  Không chọn lượt66 thay52. Server p95 **37,174s**; p95 client không công bố do
  collector đầu tính cả cooldown vào latency lỗi (raw giữ nguyên, đã ghi rõ).
- [x] **RAG-95-05d — Đo/chấm batch4 DONE (`daae9bcb`):** đủ112 phản hồi thật,
  **62 PASS/37 FAIL/1 BLOCKED**,97 lời gọi Gemini thành công,1 lượt provider503,
  0 HTTP error/timeout/cache, không retry/reset quota. Giữ nguyên input/gold,
  4 PDF/index/profile/source và rubric; mọi lỗi nằm trong mẫu số100.
  Client p50 **5,030s**, p95 **18,020s**, đo riêng cooldown; chưa đạt mốc10s.
  96 citations không lỗi tọa độ/quote; không suy thành semantic/OCR PASS.
  OCR04/06 đã chọn đúng nguồn nhưng còn thiếu facts bắt buộc nên vẫn FAIL.
- [x] **RAG-95-05e — Đo/chấm batch5 DONE (`5e8ea511`):** gói R13 đã được chủ
  dự án duyệt đúng hash `bf695e3d…`; đủ112 phản hồi thật, **69 PASS/31 FAIL/
  0 BLOCKED**,96 lời gọi Gemini thành công,0 HTTP/provider error/timeout/cache.
  Client p50 **4,257s**, p95 **8,898s**; giữ nguyên gold/PDF/index/profile/CTX,
  không retry, reset quota hoặc chọn kết quả tốt nhất. Citation101 không lỗi
  tọa độ/quote; không suy thành semantic/OCR PASS. Có lỗi khẳng định thiếu
  thông tin sai ở CTX06-L3; đã sửa code riêng ở03d, không sửa kết quả R13.
- [x] **RAG-95-05f — Native candidate qualification DONE (`5774b20d`):** R15 ran 112/112 app turns on the current source-identical candidate; **68 PASS/32 FAIL/0 BLOCKED**, with 99 real Gemini inferences and no provider/HTTP errors, timeouts, or cache hits. Three project keys each served 33 successful calls; no retries or quota resets. Citation audit: 98 citations, no page/quote geometry errors. Client p50 4,201 ms, p95 9,221 ms. R14 `provider_unavailable` was an environment/network permission issue and is excluded from score. R15 is developer review only; independent review and fresh holdout remain open.
- [ ] **RAG-95-05g — Re-measure after root-cause fixes:** prioritize source-grounded reading of curriculum tables/diagrams, conditional branches, multi-course answers, and false abstentions. Keep the R15 score as the last official measurement until the full app/Gemini run is repeated on the frozen candidate. No case-ID or question-specific lookup.
  Current local work fixes literal course-row parsing, conditional branches, explicit sibling exceptions, and diagram semester scope. Geometry-derived semester metadata survives chunking only when the source group heading and every literal course code are present; retrieval boosts only the matching semester/selection group, with source codes checked. Offline PDF reparse/chunk/hybrid-retrieval/grounding replay on the student handbook places the HK7 audit/controls choice group first and returns its two literal course rows with a physical-page-33 citation. This is local replay, not a new Gemini prediction or Golden100 score. R15 OCR03 also replays with the Rector exception. Replaying OCR06 with the original source hash and resolved evidence IDs retains the obligation to retake the course after another failure. The full local suite passes (**418 tests**). The official R15 remains **68/100**; independent adjudication and fresh holdout remain open. The parser/chunker version change requires re-ingestion before new geometry metadata is available in existing indexes. Next: requalify the full app/native candidate before updating the score; keep source/gold/review gates separate.
- [x] **RAG-95-05h — Chuẩn bị candidate R16 DONE (05/11):** khóa `e4ecf04`, đủ 264 trang của 4 PDF; xác minh hash và giữ nguyên text/OCR so với R15. Re-chunk bằng code hiện tại, thêm metadata quan hệ học kỳ cho 18 chunks sơ đồ, tái sử dụng đủ 1.585 vectors cùng model/revision. App thật khởi động thành công; source/index/baseline không đổi trong lúc đo.
- [ ] **R16 — Đo native còn BLOCKED bởi provider:** đã bắt đầu 10/112 lượt hỏi, lưu được 9 phản hồi app; 3 lần gọi Gemini thật đều gặp HTTP503, 0 inference thành công. Dừng lô sau lỗi quá tải liên tiếp; 90 case chưa thử và 1 phản hồi chưa checkpoint không được tính PASS. Pool thực tế có đủ 3 key; kiểm tra local xác nhận thứ tự key_1 → key_2 → key_3 lặp lại, không gửi thêm API. HTTP503 dùng cooldown chung; HTTP429 mới chuyển project trong cùng câu. Giữ quota, không retry/reset hoặc thay model. Lưu raw attempts/traces/scope/harness và lý do dừng vào results.json hiện có; accuracy đầy đủ gần nhất vẫn 68/100. Phần native của 05g chỉ DONE sau một lượt đầy đủ hợp lệ.
- [x] **FIX-07b — Phục hồi 503 qua pool DONE (code, 05/11):** profile ba project chuyển khi HTTP503, mỗi project tối đa một attempt trong cùng lời gọi; cửa sổ chuyển 10 giây, giảm timeout các lần tiếp theo theo thời gian còn lại. Giữ cooldown project; cả pool quá tải hoặc có Retry-After của dịch vụ thì nghỉ chung. Không lặp key, không chuyển lỗi auth/timeout hoặc stream đã có text; mọi attempt vẫn tính quota. Telemetry ghi slot key cả khi thất bại, không ghi khóa. **430 tests PASS**; kiểm tra API thật bằng prompt JSON đơn giản thành công trong **1,245s**, không phải Golden100 prediction/accuracy. Đã thử native R17 trên `8091416`: telemetry xác nhận cả key_1/key_2/key_3 đều được gọi cho FACT01; 3 HTTP attempts, 0 model success, provider vẫn503 nên dừng ngay. Source/index/baseline đều khớp hash; không retry collector. Đây là xác minh failover thật, chưa phải Golden100 hoàn tất; accuracy đầy đủ vẫn68/100.

- [x] **FIX-07c — Pool sáu key DONE (code, 05/11):** chủ dự án bổ sung key_4–6 và xác nhận mỗi key thuộc project riêng. Router/factory/launcher nhận 2–16 bindings tường minh; profile hiện dùng 6 key, ưu tiên thứ tự4→5→6→1→2→3. Xác minh 6 credential khác nhau mà không ghi giá trị; giữ ngân sách quota/cooldown chung và giới hạn phục hồi đã có. **431 tests PASS**, secret scan PASS. Đo lại Golden100 trên candidate khóa riêng; chưa cập nhật accuracy trước khi đủ kết quả thật.

- [x] **QA-CHAT-EXPORT — DONE (05/11):** đã xuất tệp local `evaluation/results/campusai_100_remediation_20261103/campusai_gemini_review.txt`, gồm100 case/112 lượt R15 và54 case/54 lượt R19. Đủ câu hỏi, gold gốc, câu trả lời thực tế, citation, lỗi provider và lịch sử CTX; tách rõ hai candidate và46 case chưa có output mới. Không kèm verdict cũ để tránh neo điểm; kiểm tra không chứa credential. Đã nhận review Gemini Chat, lưu nguyên văn/hash trong kết quả hiện có; không ghi thành human approval/fresh holdout. Không gọi API khi xuất file.
- [x] **QA-CHAT-AUDIT — DONE (05/11, lượt đầu):** đối soát review nhận được: thiếu10 case CTX/ROB dù export đủ100; bảng R15 đếm73 PASS/17 FAIL nhưng summary ghi71/19; OCR19 R19 bị chấm PASS dù reviewer xác nhận lẫn chú thích. Review đầu **INCOMPLETE**, không thay điểm strict R15 **68/100**. Đã xuất một file bổ sung13 case (10 thiếu +3 tranh chấp), có prompt và output nguyên trạng; kết quả bổ sung ở task dưới.
- [x] **RAG-95-03h — Tách chú thích khỏi tên học phần DONE (local, 05/11):** parser dừng ở legend/chú giải và nhãn quan hệ tiên quyết; giữ offset gốc để citation không mất tên khi xuống dòng hoặc có nhiều khoảng trắng. Kiểm ảnh trang33 PDF TTN và replay retrieval OCR19 đã lưu xác nhận tên môn sạch, quote nguyên văn. **436 tests PASS**, không gửi câu đã khóa; replay không tính là inference/accuracy mới.

- [x] **RAG-95-05j — Khóa bộ đo v2 DONE (08/11):**100 case/112 lượt, đủ8 nhóm;0 trùng hash với224 câu đã khóa, tách gold khỏi inference. Gắn gold với PDF/trang; đã soi các trang scan và sơ đồ trọng yếu. Đây là dev source review, không phải fresh holdout độc lập. Candidate `af2091b5`, đúng gói owner đã duyệt `369eda79…`/scope `79e0928b…`.
- [ ] **RAG-95-05k — Thu/chấm v2 CHƯA ĐỦ100 case:** đã thử70 case, lưu69 phản hồi;1 lượt dở giữ không xác định,1 lượt timeout,62 attempts/57 inference thành công quan sát được. Dừng theo scope; không resend. Ít nhất10 FAIL rõ nguồn và1 ca cần review gold/phạm vi CTĐT, nên trần lý thuyết≤90/100 kể cả mọi ca khác PASS; đây không phải accuracy đã đo. Giữ30 case/42 lượt chưa hỏi cho candidate sau, giữ nguyên gold/output/index cũ; tổng294 câu đã khóa.
- [x] **RAG-95-05l — Candidate v3 / nguồn và bank DONE (09/11):** ingest/index4 PDF gốc bằng chunker v9:264 trang,1703 chunks, tái dùng1484 vectors; PDF/hash và Điều9 đã kiểm. Runtime khóa `e7888b49`,100 case/112 lượt đủ8 nhóm,0 trùng294 câu đã khóa, gold tách inference. Đây là development/exposed-source, không phải fresh holdout.
- [x] **RAG-95-05m — Thu native v3 DONE (09/11):** đủ100 case/112 lượt qua app trên một candidate;75 POST/75 inference thành công,0 lỗi HTTP/provider, p95 **8,988s**. Xoay6 project thực: key1/2/3 mỗi12, key4/5/6 mỗi13 inference. Source/index không đổi;406 câu đã khóa. Collector/server đã kết thúc, port8001 đóng. Cap600 chỉ dùng75;525 còn dư không tự dùng cho code/câu khác. Đây là DONE thu output, không phải PASS accuracy.
- [x] **RAG-95-05n — Gói Gemini Chat v3 DONE (09/11):** owner chọn chấm qua Chat. Một file `evaluation/results/campusai_100_remediation_20261103/campusai_v3_gemini_review.txt` có prompt,100 case/112 actual outputs, gold đã khóa, citation, trace tóm tắt và hash mỗi case; đã kiểm đủ dòng/một candidate/không credential. Đọc kèm4 PDF gốc, không trộn kết quả cũ, không dùng câu Chat tự tạo thay output app.
- [ ] **RAG-95-05o — Chấm chất lượng v3:** đã nhận review Gemini Chat: đủ100 ID/hash đúng candidate; đếm từng dòng47 PASS/53 FAIL (47%), trong khi summary ghi38/62. Giữ nguyên raw review; cần kiểm quote/trang và giải quyết lệch summary trước khi xác nhận accuracy. Đã xác nhận nguồn ít nhất6 nonpass nên bản v3 chưa thể đạt95%; trần lý thuyết94/100 này không phải accuracy đã chấm. Không tự PASS, không giảm mẫu số hoặc sửa gold để tăng điểm.
- [ ] **RAG-95-02d — Gỡ phụ thuộc danh sách động từ trong tên nguồn:** các câu HUST ở vị trí/từ nối mới vẫn bị hỏi tên trường trước retrieval. Cần nhận diện alias/nguồn theo ngữ nghĩa có kiểm chứng và schema ràng buộc, không tiếp tục vá từng câu/mẫu động từ; giữ tách trường với phòng ban/sản phẩm và tài liệu ngoài giáo dục.
- [ ] **RAG-95-03x — Locator tự nhiên xuyên pipeline:** xử lý trang23/Điều30/page19 và số/mã viết liền theo cùng parser, không biến thành mã môn hoặc điểm; giữ nguyên raw question, bảo vệ mã sản phẩm/tên PDF và citation/trang nguồn. V3 đã thu xong nên có thể sửa tiếp mà không thay output baseline.
- [x] **RAG-95-02c — Phạm vi trường trong câu tự nhiên DONE (code/local, 08/11):** đưa viết tắt sau quy chế/sổ tay, đầu câu và sau số trang tới verifier hiện có; không tự đoán trường. Không coi số lượng, vai trò học thuật, “cấp Đại học” hoặc từ nằm trong tên trường đã nhận diện là trường lạ.23 regression tổng quát; toàn suite **634 PASS (18,21s)**. Probe offline6 câu đã lưu:5 tham chiếu HUST được chuyển đúng tới verifier,1 câu “hai học kỳ” chọn đúng nguồn và không hỏi tên trường.0 gọi model; chưa có native accuracy cho bản sửa này.
- [x] **RAG-95-03q — Phạm vi CTĐT trong catalogue DONE (code/local, 09/11):** nhận heading ngành đánh số đúng nguồn, ưu tiên ngành được nêu trong câu hiện tại và không nhập các chương trình có tên lồng nhau. Cùng policy áp dụng cho retrieval và tra bảng nhanh; loại chunk băng qua ranh giới ngành.13 regression mới, toàn suite **647 PASS (21,57s)**. Probe nguồn thật FACT13/14 giới hạn đúng hàng trang24; FACT17 cần review vì gold mượn mã của CTĐT Kế toán–Kiểm toán cho câu nêu Kế toán. Không sửa gold/output cũ, không gọi model, chưa có accuracy mới; cache tự đổi theo source fingerprint.
- [x] **RAG-95-03r — Danh tính nguồn ở nhánh hỏi trang DONE (code/local, 09/11):** dùng chung proof header nguyên văn đúng tài liệu cho retrieval và hỏi trang; không mượn header của nguồn khác, metadata suy đoán, hash sai hoặc tên trường mâu thuẫn. Giữ nguyên text/trang/citation và bind proof vào cache.6 regression mới; replay nguyên draft đầu OCR06 hợp lệ với1 lần đọc, citation trang10 và header trang1,0 API calls. Toàn suite653 PASS; không sửa output/accuracy cũ.
- [x] **RAG-95-03s — Áp dụng ngưỡng điểm có chứng minh DONE (code/local, 09/11):** kiểm Decimal cho một điểm trung bình có tên và thang điểm do user nêu, đối chiếu đúng field/ngưỡng/thang trong claim nguồn. Chỉ áp dụng khi hỏi riêng ngưỡng điểm; chặn sai đầu vào, sai thang/field/kết luận, nhiều đầu vào, điều kiện ghép/ngưỡng xung đột và khẳng định đủ toàn bộ điều kiện.18 regression mới, toàn suite **671 PASS (21,83s)**. Replay nguyên draft đầu REA01 qua grounding/citation trang29 với1 lần đọc/0 provider requests; chưa phải native accuracy mới. Không push khi goal chưa đạt.
- [x] **RAG-95-03t — Tách câu hỏi thủ tục khỏi bảng kỳ học DONE (code/local, 09/11):** ưu tiên bảng theo học kỳ chỉ khi user hỏi CTĐT/bảng/môn/tín chỉ; câu hỏi nghĩa vụ đăng ký/rút môn không bị đồng nhất với bảng học kỳ. Bật trong nhánh web không calibration, giữ mặc định lịch sử. Replay hybrid thật trên cùng index loại các bảng khỏi đầu kết quả NAT13,0 API calls.9 regression mới.
- [x] **RAG-95-03u — Ranh giới điều khoản OCR DONE (code/local, 09/11):** chunker v9 nhận marker điều/chương riêng dòng với title theo sau, và title dài có mã điều tường minh ngay cả thiếu font/bold. Không tạo heading từ tham chiếu cuối câu/list thường.10 regression mới; source-only PDF Thủ đô nay tách đúng Điều9 khỏi Điều8, giữ text/trang gốc. Index native v2 giữ nguyên; cần ingest/index phiên bản mới trước lượt nghiệm thu tiếp theo.
- [x] **RAG-95-03v — Giữ đủ field thủ tục trong context DONE (code/local, 09/11):** recall source-owned quy định đăng ký kỳ đầu và sĩ số mở/hủy lớp; giữ mọi alternative/ngoại lệ nguyên văn, không gán giá trị theo trường/mã benchmark.5 regression mới; kiểm lại đúng profile8000 ký tự/balanced cho NAT13/18, đủ toàn bộ anchors trước đây bị mất/cắt. Toàn suite **695 PASS (19,84s)**, secret scan/diff check PASS; không thay native output/accuracy.
- [x] **RAG-95-03w — PDF ngoài giáo dục và tên nguồn tổng quát DONE (code/local, 09/11):** metadata regulation/handbook không đủ để coi viết tắt phòng ban/sản phẩm là tên trường; không hiểu trường dữ liệu/điện trường/từ trường là trường đại học. Chọn file theo tên đầy đủ, Unicode/khoảng trắng trong phạm vi được cấp quyền, hỏi rõ nếu trùng tên/thiếu file. Bỏ tên file khỏi truy vấn nội dung để mã trong filename không thành mã môn; planner giữ đúng offset khi gán phép tính cho từng nguồn, thuật ngữ prerequisites chung không tự thành đồ thị học phần.31 regression mới, toàn suite **726 PASS (10,29s)**, không mock retrieval; draft kiểm thử có kiểm soát chỉ là unit/regression, chưa phải accuracy AI.
- [x] **QA-CHAT-FOLLOWUP — DONE (05/11):** nhận review bổ sung13 case và bảng đủ100; đếm lại khớp summary: R15 **81 PASS/19 FAIL**, R19 **29 PASS/7 FAIL/18 BLOCKED/46 NOT_RUN**. Reviewer đã sửa OCR19 thành FAIL. FACT24 đúng là chỉ hỏi A, còn gold yêu cầu thêm B/C/D/F; FACT15 và locator CTX03 giữ thành vấn đề gold/nguồn riêng. Lưu nguyên văn/hash/bảng vào results hiện có, không sửa gold hoặc output. Đây là review AI hồi cứu, chưa nghiệm thu code mới hoặc fresh holdout; strict R15 vẫn68/100.
- [x] **RAG-95-03i — Giảm từ chối cả câu hỏi hỗn hợp DONE (code/local, 05/11):** tách yêu cầu tiết lộ nội bộ đứng đầu khỏi câu hỏi tài liệu tiếp theo; từ chối secret nhưng phần tra cứu vẫn qua scope/retrieval/grounding/citation bình thường. Áp dụng cả luồng hỏi và hỏi trang PDF; yêu cầu chỉ lấy secret không gọi model/truy hồi. Cache chỉ giữ câu trả lời nguồn đã kiểm chứng, không làm lời từ chối lọt sang câu hỏi thông thường. Không nhận keyword API/prompt trong câu giải thích hoặc trích dẫn thành lệnh tiết lộ. **453 tests PASS**; chưa có native accuracy mới, không gửi lại câu đã khóa.
- [x] **RAG-95-03j — Phân biệt locator với điểm đầu vào DONE (code/local, 06/11):** số trang/khoảng trang, số điều/mục/bảng, năm/khóa và số trong token PDF không còn bị gom thành điểm cần quy đổi. Giữ mơ hồ khi còn nhiều điểm; vẫn yêu cầu khoảng điểm/chữ đúng nguồn, chặn khoảng mâu thuẫn hoặc nhãn OCR chưa rõ. Bảy regression mới, toàn suite **460 PASS (11,17s)**. Replay câu đã lưu nhận đúng điểm đầu vào nhưng vẫn chặn nhãn OCR lỗi; không tạo native prediction hoặc accuracy mới.
- [x] **RAG-95-04b — Chẩn đoán glyph OCR DONE (local, 06/11):** kiểm ảnh trang16 PDF Thủ đô xác nhận dấu cộng bị Tesseract đọc thành `t`. Hai crop ở scale2/3 vẫn sai nên dừng cách tăng scale; RapidOCR trên cùng vùng, model pin/1 luồng CPU, đọc được `A+` trong1,224s gồm khởi tạo. Chỉ là thử OCR nguồn, không phải app QA hoặc benchmark mới. Chưa sửa text/index/gold; tích hợp kiểm glyph có giới hạn, audit/model identity và hồi quy vẫn thuộc task04 đang mở.
- [x] **RAG-95-04c — Kiểm glyph từ raster DONE (code/local, 08/11):** chỉ nạp model OCR phụ đã pin khi có nhãn khoảng điểm bất thường; đọc một khối nhỏ, rồi tối đa một batch dòng còn thiếu. Tối đa4 nhãn/trang,12 nhãn/mỗi process OCR,600.000 pixels/crop; CPU/OpenCV/ONNX giới hạn1, GPU tắt. Chỉ đổi ký hiệu khi hàng, chữ cái và mọi số khớp, confidence≥0,9; giữ nguyên từ/số/dấu câu còn lại. Thiếu model, nhận dạng mâu thuẫn hoặc không chắc thì giữ text gốc. Audit có tọa độ, output đọc độc lập và hash model; giao thức worker kiểm lại thay đổi trước khi nhận. Policy v4 vô hiệu cache OCR cũ nhưng vẫn đọc được journal v3; audit được giữ khi OCR tiếp trang. PDF thật trang16–17 mất **3,874s**, CPU3,656s, RSS worker đỉnh264,81MiB: A+/B+ trang16 đã đọc lại đúng, C+/D+ trang17 vẫn chưa giải quyết. Không sửa PDF/index/gold đã nghiệm thu; chưa phải đo toàn tài liệu hoặc native accuracy.
- [x] **RAG-95-03k — Claim quy đổi điểm ngắn, đúng nguồn DONE (code/local, 08/11):** khoảng điểm in trong prose/scan được lấy bằng offset nguyên văn của đúng dòng; không gửi cả trang dài làm claim rồi thất bại giới hạn citation. Giữ nguyên proof bảng chữ nhật và chặn khoảng mâu thuẫn; hỗ trợ nhãn khoảng Việt/Anh. Replay local sau OCR trả A+ và citation đúng trang/quote, không gọi Gemini. Toàn bộ **476 tests PASS (10,28s)**; secret scan PASS. Điểm benchmark vẫn giữ riêng strict R15=68/100 và review Chat=81/100.
- [x] **RAG-95-03l — Giữ phạm vi điều kiện trong context DONE (code/local, 08/11):** đoạn nguồn có field anchor giữ tiêu đề được in phía trước khi vừa budget, kể cả xa hơn120 ký tự; dừng trước nhóm điều kiện kế tiếp khi đủ ranh giới. Nếu có nhiều field/tiêu đề cần so sánh, giữ mọi anchor. Sau window/truncate, nhãn `section` chỉ được giữ khi có trong nội dung model thực sự nhìn thấy. Trace CTX06-L3 nay giữ tiêu đề/điều kiện khóa luận và bỏ nhãn mục kỷ luật không liên quan; không sửa output model cũ. **480 tests PASS (12,89s)**, bốn regression mới; chưa có native accuracy mới.
- [x] **QA-95-PREP — Chuẩn bị đo DONE (08/11):** khóa source `962a1475`,100 case mới/112 lượt, không trùng112 câu cũ. Bốn PDF đủ264 trang/hash đúng; ingest/index hiện hành, tái dùng1.584/1.585 vectors. Owner duyệt scope `98c38e75…`, pool6 project/cap600; không gold/expected trong inference, không phải blind holdout.
- [x] **QA-95-RUN — Thu native DONE (08/11):** đủ112 app attempts/100 case trên một candidate;108 inference Gemini thành công, **18/key trên cả6 key**,109 transport attempts kể cả1 lỗi sandbox10013 ban đầu. Giữ lỗi/lock, sửa quyền khởi chạy rồi chỉ tiếp tục câu chưa thử; không collector retry/reset quota. p95 **10,804s**, source/index không đổi đến cuối lượt. Đây là thu output, chưa phải PASS chất lượng.
- [x] **RAG-95-03m — Tái dùng OCR ở nhánh hỏi trang DONE (code/local, 08/11):** phát hiện8 case báo thiếu OCR dù đã có text đúng trang. Nhánh hỏi trang nay nhận danh sách trang OCR từ ingest hoàn tất/current coverage policy khi thiếu field progressive-readable; không OCR lại, không mượn text trang khác, không nhận metadata partial/cũ/không hợp lệ hoặc ghi đè danh sách rỗng tường minh. **494 tests PASS (10,39s)**; replay extraction thực tế đủ8 ca nhận đúng trang/text,0 model calls. Không thay output native cũ hoặc cộng replay vào accuracy.
- [x] **QA-95-CHAT-PACKET — Xuất output DONE (08/11):** một tệp `campusai_unseen_review.md` cạnh results hiện có, đủ100 case/112 lượt, lịch sử/citation/lỗi thật, hash từng case và prompt kiểm PDF. Bốn PDF gốc giữ nguyên. Secret scan PASS; không phải independent review đã hoàn tất.
- [x] **QA-95-CHAT-AUDIT — Nhận/đối soát review DONE (08/11):** review đủ100 case, đếm đúng69 PASS/21 FAIL/1 BLOCKED/9 REVIEW_REQUIRED trên candidate `962a1475`; không cùng tập với strict R15. Hash packet/candidate khớp nhưng FACT17 sai hash;34 verdict PASS/FAIL thiếu trang hoặc quote,12 quote không khớp trang khai báo theo parsed source. Reviewer còn gán sai tên môn ở OCR14 so với native PDF. Lưu nguyên review/hash và audit; **69% là điểm reviewer báo, chưa phải verified accuracy**, không sửa gold/prediction hoặc công nhận independent release PASS.
- [x] **RAG-95-03n — Đúng đơn vị phần trăm và ranh giới tên trường DONE (code/local, 08/11):** kiểm đầy đủ theo số tín chỉ, phần trăm hoặc cả hai được hỏi; tiếp tục chặn sai số/đơn vị. Nhận diện tên trường không còn nuốt các động từ hành động sinh viên viết thường; giữ chặn tên mở rộng giả/tên trường khác.24 checks mới, toàn suite **518 PASS (10,31s)**. Replay draft thật FACT16 qua toàn bộ kiểm grounding có1 claim supported/1 citation, không cần wording-repair thứ hai;0 API calls, không thay accuracy/output native cũ. Chưa push theo chỉ đạo mới.
- [x] **RAG-95-03o — Giữ bằng chứng bảng ở nhánh hỏi trang DONE (code/local, 08/11):** nhận header cột gốc nằm dưới tiêu đề gộp chỉ khi mọi header lặp khớp; quote giữ nguyên title/header/body rows, không tự gán đơn vị hoặc trộn ô. Nhánh hỏi trang có mã môn dùng lại bảng đã index trong đúng nguồn/trang yêu cầu, giữ mọi match mâu thuẫn; metadata sai/hash khác/trang ngoài phạm vi bị loại. Không OCR/embedding/LLM thêm; câu thường không đọc thêm bảng.19 checks mới, toàn suite **537 PASS (10,36s)**. Replay extraction/typed proof trên PDF thật giữ bảng và text trang12, đọc đúng quan hệ mã–1 tín chỉ;0 provider calls, không thay native output/accuracy. Chỉ lưu local, chưa push.
- [x] **UPSTREAM-01 — Giữ header qua chunking DONE (code/local, 08/11):** đã đọc Docling serialization, Unstructured table chunking và RAGFlow dataset config. Áp dụng header gốc lặp vào chunk tiếp theo, giữ row indices/provenance và budget; schema mâu thuẫn không được mang sang. Tách helper thuần bảng dùng chung ingestion/grounding, không thêm model/dependency. Chunker v8 yêu cầu re-index để bảng cũ có header continuation. Toàn suite **539 PASS (10,16s)**. Audit35 bảng nguồn giữ đúng mọi source row,28,14ms, không ghi đè index/PDF; chưa tăng số dòng mã hợp lệ vì còn lỗi mã bị tách ở bước extraction. Không tính thành accuracy mới. Tiếp theo: kiểm geometry của các mã/hàng lỗi rồi xác minh retrieval trên candidate mới.
- [x] **UPSTREAM-02 — Sửa query trước retrieval DONE (code/local, 08/11):** bỏ mở rộng sai đại từ “ai”→AI, “đồng ý/đóng tiền”→deadline và “đăng ký tạm trú/chữ ký”→học kỳ; vẫn nhận AI kỹ thuật, đóng cổng và “học kì/kỳ/HK” thật. Thêm ưu tiên cụm chủ đề nguyên văn hiếm trong source body cho web hybrid một tài liệu chưa calibration; không thêm candidate/metadata fact, không đổi score/ngưỡng, không áp lên route mã/trang/học kỳ hoặc cấu hình Phase6/7 đã khóa.30 checks mới, toàn suite **569 PASS (10,88s)**. A/B offline4 câu/cùng index+encoder: nguồn thai sản trở lại đầu kết quả, nội trú vào top3;2 ca còn lại giữ nguyên. Không gọi Gemini hoặc gửi lại câu đã khóa; chưa phải accuracy mới. Native geometry chữ số tràn hàng vẫn chưa tự sửa khi thiếu proof. Chỉ commit local.

- [x] **UPSTREAM-03 — Metadata trước chunk/retrieval DONE (code/local, 08/11):** nhận tên trường từ nhãn/header nguồn, không bắt đuôi tên miền hoặc câu văn; mã học phần phải có nhãn riêng và duy nhất, không lấy mã luật/mã đầu tiên trong catalog làm mã cho toàn PDF. Bỏ placeholder Khoa và “phiên bản” trong prose. Kiểm tra4 PDF thật phát hiện/sửa tên `TT`, câu “Ngoài cách đăng ký…” và mã `QH14`/mã học phần bị gán toàn tài liệu. Cache có version; cập nhật metadata/chunk header từ text đã lưu khi bảo toàn body/citation/bảng và giới hạn2.400 ký tự, nếu không thì xử lý lại. Job identity giữ lịch sử ledger và phân biệt producer mới. **588 tests PASS (10,40s)**; audit offline3/4 nguồn nâng nhãn an toàn không OCR, nguồn còn lại cần rebuild vì header dài hơn. Không gọi model, không sửa gold/PDF hoặc gửi lại câu đã khóa; chưa phải accuracy mới. Chưa push.

- [x] **UPSTREAM-04 — Giữ chủ đề trước retrieval DONE (code/local, 08/11):** nhận tham chiếu “vừa nói/đã nhắc/đã đề cập”, “vẫn … đó/này” và English mentioned-topic trước nhánh miễn context của PDF. Giữ chuỗi câu hỏi user, không lấy lời assistant làm bằng chứng và không kế thừa sang chủ đề mới độc lập; bump context cache version. Sáu regression tổng quát trên hợp đồng/bảo trì/báo cáo; toàn suite **594 PASS (10,46s)**. Replay retrieval thật, không gọi Gemini: CTX02 từ top8 `[99,15,99,18,37,99,21,95]` thành `[37,37,38,37,38,38,35,38]`, khôi phục đúng vùng nghiên cứu khoa học. Chưa phải câu trả lời mới hoặc accuracy.
- [x] **UPSTREAM-05 — Index chuẩn bị hiện hành DONE (local, 08/11):** cập nhật cả4 PDF/264 trang theo chunker v8 và metadata v2, tổng1.586 chunks; giữ nguyên SHA nguồn và baseline đã đo. Ba nguồn tái sử dụng trích xuất, một nguồn re-ingest để bảo toàn body trong chunk budget mới. Lưu revision/hashes tại results hiện có;0 câu hỏi/0 provider calls ở bộ chuẩn bị này. Kiểm retrieval4 câu đã lưu không phải đo QA và không tự mở khóa câu cũ. Chờ bộ câu mới/phạm vi live hợp lệ tại task đo; chưa PASS goal hoặc push.

- [x] **RAG-95-03h — Chứng minh phép tính tỷ lệ tín chỉ DONE (local, 08/11):** xác minh tổng/tín chỉ chuyển ở trường khác do user nêu, một ngưỡng phần trăm có nguồn và phép nhân Decimal; chỉ bỏ kiểm tra lặp số ở đúng vị trí/đơn vị đã chứng minh. Không cấp quyền/đủ mọi điều kiện, không cho số tiền trùng giá trị đi qua. Từ chối sai tổng, tử số, kết quả, kết luận, đơn vị/phạm vi, ngưỡng xung đột và kết luận tự mâu thuẫn.17 regression mới, toàn suite **611 PASS (10,73s)**. Replay nguyên draft đầu NEW-REA-02 hiện qua grounding với1 lần đọc draft lưu/0 provider calls; không sửa prediction cũ hoặc cộng vào accuracy. Chuẩn bị candidate vẫn chưa có native score mới; chưa push.
- [ ] **QA-95-NEXT — Đo trên candidate cuối:** theo chỉ đạo08/11, tự kiểm tra ≥95% bằng câu trả lời thực tế sau khi chốt code; dùng câu chưa từng hỏi, khóa protocol/candidate trước đo, giữ đủ lỗi và toàn bộ mẫu số. Không dùng unit-test PASS hoặc replay context làm accuracy. Nếu cần Gemini Chat, cung cấp một file output thật/citation/context và prompt chấm riêng; Chat tự trả lời câu hỏi không thay thế prediction của app. Hiện registry đã khóa224 câu (112 cũ +112 lượt mới); không gửi lại, không gộp outputs nhiều candidate hoặc đổi gold/thresholds để đạt95%. Packet Chat hiện tại là bản đo trước sửa03m; chất lượng bản sửa cuối chưa được đo lại bằng model.

- [ ] **RAG-95-06 — Blind holdout tự động:** chủ dự án chọn tự động hóa reviewer
  ngày03/11. Dùng **AI review độc lập**, không ghi thành human review hoặc
  approval của người dùng. Giữ nguyên **≥200 câu /≥95%** và các gate an toàn.
  Worker riêng tạo và kiểm gold, giữ gold ngoài output/context của Codex phát triển;
  tách bước tạo và review, lưu đúng model/config/nguồn/hash thực tế. Chưa tạo hoặc
  chạy bộ blind, không báo PASS chỉ vì đã có protocol. Không khẳng định cách ly
  quyền quản trị OS nếu chỉ tách process. Nếu không đảm bảo được gold không lộ,
  trạng thái phải NOT BLIND, không tính là evidence nghiệm thu.
  Khóa hash gold, code/profile/index, protocol và ngưỡng trước inference; runtime
  chỉ nhận question/source-selection/session, không expected/labels. Worker chấm
  raw predictions, citation và hallucination trên PDF gốc. Nếu
  candidate FAIL, không chỉnh rồi chạy lại cùng holdout để nhận chứng nhận;
  vòng code sau cần một tập blind mới. Không tạo reviewer/approval giả.
- [x] **RAG-95-06a — Kiểm tra export/review tự động DONE:** có CLI offline
  `python -m scripts.release.blind_holdout` kiểm hash candidate/index, đủ200 ca,
  history đúng từng phiên, family exposure, receipt review riêng, cách ly gold,
  citation và binding prediction→review. Giữ mọi lỗi provider trong mẫu số;
  không tạo thêm gate “0 outage” thay ngưỡng95%. **349 tests PASS** trên toàn bộ
  suite, gồm fixtures giả lập ghi rõ không phải holdout/inference/review thật.
  Worker tạo/chấm gold riêng và bộ200 câu thật **chưa triển khai/chưa chạy**;
  validator không tự tạo receipt hoặc nhận mình đã chứng minh cách ly gold.
- [ ] **RAG-95-07 — Acceptance:** chỉ DONE khi tất cả gate có bằng chứng PASS.
  Golden:NOT PASSED68% ở lượt R15 gần nhất. Holdout:NOT RUN;
  các gate an toàn cần kiểm lại đúng
  candidate. FACT15/scope/gold có vấn đề được báo riêng, không sửa hoặc loại ca.

Bằng chứng dùng lại: [QA/remediation](evaluation/results/campusai_100_remediation_20261103/report.md).
Giữ9 đầu ra đã có; chỉ thêm dữ liệu cần tái hiện/audit, dọn fixture/log tạm.

## Tài liệu

- [x] **DOC-01 — README tiếng Anh DONE (01/11):** viết lại giới thiệu, tính năng,
  sơ đồ xử lý, setup Windows/Docker, quyền riêng tư, development/CI và mục lục tài
  liệu; đối chiếu lệnh với code/config, kiểm tra liên kết nội bộ. Không thêm file báo cáo.

## Chất lượng trả lời và thao tác hỏi — 02/11

- [x] **ANS-11a — Tái hiện và hồi quy vòng sửa Golden 100 DONE (03/11):**
  thêm regression tổng quát dùng trường/mã giả; trước sửa 11 FAIL/9 PASS trong
  20 ca P0. Bản sửa routing/context, ràng buộc ngành theo heading nguồn, số thập
  phân tự nhiên và guard vắng thông tin đã **PASS toàn bộ 279 tests**, không đổi
  profile, retry, quota/cooldown hoặc index. Lượt diagnostic thật: **19 case /
  31 turns, 36 Gemini calls**, không lỗi HTTP/provider. CTX01 trả đúng cả 3 lượt;
  OCR02 đọc được trang scan đúng nguồn; CTX06 đã đúng chương trình ở lượt 1.
  Đây là diagnostic, **chưa phải** điểm lại đủ 100 ca hoặc nghiệm thu ≥95%.
  Dữ liệu mới và đề xuất gold/scope giữ tại
  [vòng sửa Golden 100](evaluation/results/campusai_100_remediation_20261103/report.md),
  không ghi đè baseline. Diagnostics xác định thêm lỗi validator loại suy luận
  số học đúng, alias/so sánh thiếu nguồn và diễn giải sai nhóm môn tự chọn; tiếp tục sửa.
- [ ] **ANS-11b — Đóng vòng sửa bằng kiểm chứng thật:** khắc phục các lỗi còn
  quan sát được; xác nhận ≥95% trên cùng bản cuối. Báo riêng strict gốc,
  adjudicated v2 sau review nguồn và fresh holdout được đóng băng sau sửa.
  FACT15 và các fixture phạm vi/ý phụ không tự chuyển thành PASS; chưa có bằng
  chứng thì ghi PENDING_GOLD_REVIEW/NOT PASSED.
- [x] **ANS-11c — Đo lại đủ Golden 100 DONE (03/11, `0a96fe4b`):**
  **100 ca /112 lượt thật**, **48 PASS /52 FAIL**, so với baseline33 PASS;
  82 Gemini calls thành công,0 lỗi HTTP/timeout,0 answer-cache hits;
  p50 **2,78s**, p95 **8,10s**.74 citation hợp lệ về nguồn/trang/quote.
  Ba nhóm CTX hoàn thành cả3 lượt; chất lượng tổng vẫn **NOT PASSED**.
  Giữ nguyên golden,4 PDF và index; lịch sử lỗi/các snapshot trước được giữ
  riêng trong [báo cáo](evaluation/results/campusai_100_remediation_20261103/report.md).
  Không lặp lại lượt đo đã DONE để ghép điểm của nhiều snapshot.
- [x] **ANS-11d — Sửa đơn vị bảng và parser scope DONE (03/11, `ba2dfd34`):**
  **305 tests PASS**, gồm chống tráo dòng/đơn vị và giữ nguyên mã học phần.
  Kiểm tra NAT18 qua app chuẩn: đúng KC213046,2 TC,HK5,trang29;
  **1 Gemini call /2,68s**, không mock hoặc dùng golden làm input.
  Đã phục hồi an toàn checkpoint local khi có Windows reader lock.
  Đây là kiểm targeted riêng, không thay thế điểm48/100 của snapshot đã khóa.

- [x] **ANS-07 — Baseline Golden 100 DONE (03/11, `8ddcd9c5`):** đã chạy đủ
  **100 case / 112 lượt HTTP thật** qua app với 4 PDF, không mock; CTX chạy đúng
  thứ tự trong phiên riêng, các ca độc lập không dùng lịch sử chung. Đối chiếu đủ
  **264/264 trang, 1.585 chunks/vectors**, hash PDF khớp bản gốc. Không đổi code,
  config, index hoặc golden; không đưa expected/nhãn trường vào inference.
  Chấm AI dev theo đủ ý ở câu trả lời chính: **33 PASS / 67 FAIL, accuracy 33%**;
  **chưa đạt** ngưỡng 95%. Trong số FAIL có 7 ca chỉ thiếu ý phụ theo golden;
  FACT15 cần review gold với trang nguồn, các câu thiếu phạm vi trường được ghi riêng.
  Không loại các ca này khỏi mẫu để tăng điểm. Có lỗi nhầm trường/ngành/học kỳ và
  khẳng định sai tài liệu không đề cập. **91 Gemini calls thành công** chia 31/30/30
  giữa 3 project, 74 lượt cần model, 38 lượt local, 0 cache; 0 timeout/lỗi HTTP.
  p95 client **7,83s** gồm overhead collector, riêng lượt có model **8,14s**;
  5 phản hồi `document-info-v1` không đạt validator chỉ nhận grounding schema,
  không gọi đó là lỗi HTTP hoặc tuyên bố toàn bộ schema PASS.
  Giữ đúng 3 file được yêu cầu tại [báo cáo baseline](evaluation/results/campusai_100/report.md),
  [CSV từng ca](evaluation/results/campusai_100/results.csv) và
  [raw responses/protocol/review](evaluation/results/campusai_100/results.json).
  Đây là owner benchmark đã exposure, không phải fresh holdout/nghiệm thu độc lập.
  Đã hoàn tất báo cáo trước sửa; các đề xuất dưới đây **chưa triển khai** theo yêu cầu.
- [ ] **ANS-08 — P0 giữ đúng phạm vi hội thoại/ngành:** CTX04 áp CPA Tây Nguyên
  vào hội thoại Thủ đô; REA08/CTX06 lấy nhầm sơ đồ Kế toán–Kiểm toán cho Kế toán.
  Cần khóa trường, ngành, học kỳ và đối tượng theo bằng chứng/ngữ cảnh, không chỉ so số.
- [ ] **ANS-09 — P0 phân biệt chưa truy hồi với tài liệu không có:** CROSS03 nói
  HUST không có quy định cải thiện dù PDF trang 10 có. Cần chứng minh đủ phạm vi
  trước kết luận vắng thông tin và truy hồi đủ từng nguồn trong câu so sánh.
- [ ] **ANS-10 — P1 routing/truy hồi/suy luận:** tránh nhận `SCAN`/`API` là trường,
  hiểu trang PDF theo nguồn được nêu, giữ chủ đề khi hỏi nối tiếp; truy hồi đúng bảng
  mã môn/ngành/học kỳ, xử lý số thập phân tự nhiên và điều kiện số học có proof.
  Chẩn đoán từ chối nhầm trước khi sửa, không nới grounding hoặc hard-code câu owner.

- [x] **UX-03 — Thẻ PDF trong khung nhập chat DONE (03/11, `01bcc838`):** hiện
  ảnh trang đầu/tên file; tải lên hoặc xử lý thì xoay, sẵn sàng thì tự chọn làm nguồn.
  File lỗi dừng xoay và có thao tác thử lại/chọn lại; × chỉ bỏ khỏi câu hỏi, giữ PDF
  trong thư viện. Chờ các file mới đính kèm sẵn sàng trước khi gửi để không âm thầm
  bỏ qua nguồn; phần đã đọc vẫn hỏi được với coverage rõ. Hỗ trợ 5 PDF/lượt rồi thêm
  nhiều lượt tiếp, không giới hạn tổng nguồn ở 5. Thumbnail local nhỏ, cache RAM có
  giới hạn và kiểm quyền/hash nguồn, không OCR/model hoặc tạo ảnh trên đĩa.
  **249 tests PASS**, gồm vòng đời upload 5+5, bỏ khi đang tải, lỗi và partial OCR.
  HTTP local: HTML mới và 8 lượt đọc thumbnail của 4 PDF PASS; ảnh 4,7–32,8 KB,
  lần đầu 0,033–0,046s, cache 0,002–0,012s trong mẫu đo; không gọi Gemini.
  CI Windows/Linux, package và container PASS.
  Chưa xác nhận giao diện trực quan vì phiên không có browser kết nối; không chạy
  lại Gemini và không dùng task giao diện này để đóng các lỗi chất lượng ANS-04/05/06.

- [x] **ANS-03 — Đo Gemini thật DONE (03/11, `9753ddb1`):** chạy cùng một bản
  đủ 56 case / 60 lượt với 4 PDF đang có; 35 lượt cần model, 37 Gemini calls thành
  công chia 13/12/12 giữa 3 project, 25 lượt xử lý local, 0 cache. Không timeout
  hoặc lỗi schema/citation; median **2,83s**, p95 **5,39s**, max **8,46s**.
  Riêng 35 lượt có gọi model: p95 **8,00s**, không gộp thành tốc độ mọi câu Gemini.
  Chấm dev chặt phần trả lời chính theo gold gốc: **49 PASS / 1 PARTIAL / 2 FAIL /
  4 REVIEW_REQUIRED**; 49/52 case đủ điều kiện = **94,23%**, chưa đạt mục tiêu 99%.
  F01 có đủ ý trong claims nhưng thiếu thời gian ở phần trả lời chính; tính thêm
  claims thì 50/52 = 96,15%, báo riêng. Đây là AI dev review, không phải holdout
  mới hoặc nghiệm thu độc lập. Evidence local tại `data/operations/local-acceptance-20261103/`;
  chỉ giữ packet đã duyệt, raw responses kèm review và timing cần đối chiếu.
- [ ] **ANS-04 — Từ chối nhầm địa chỉ:** F15 không trả địa chỉ NUAE dù PDF trang 4
  có đầy đủ thông tin; cần xác định và sửa nguyên nhân kiểm chứng, không nới grounding.
- [ ] **ANS-05 — Không áp quy tắc chung thành dữ kiện cá nhân:** A01 lấy quy tắc
  mật khẩu lần đầu/reset của Đại học Tây Nguyên để trả lời câu hỏi mật khẩu cá nhân
  chưa rõ trường. Cần phân biệt thông tin hướng dẫn với dữ kiện riêng của người hỏi.
- [ ] **ANS-06 — Đủ ý ở câu trả lời chính:** trường dữ liệu nguồn đã xác minh cần
  xuất hiện rõ trong câu trả lời khi cần, tránh chỉ nằm trong claims thu gọn (F01).
  Bốn ca F02/F05/N03/F24 vẫn cần review gold/scope; không tự chuyển thành PASS.

- [x] **ANS-01 — Đúng PDF được hỏi DONE (`0d8b5a1a`):** câu hỏi nội dung nêu rõ
  “trong/theo/in/according to” tên PDF chỉ truy hồi nguồn đó trong phạm vi đã chọn
  và được cấp quyền; câu so sánh giữ các nguồn được nêu. Tên thiếu, không tồn tại,
  trùng hoặc chỉ dẫn loại trừ chưa rõ được hỏi lại trước khi gọi model. JSON và
  streaming dùng chung xử lý. Test grounding xác nhận citation từ PDF khác bị từ chối.
- [x] **ANS-02 — Nhận diện tên và câu hỏi số trang DONE:** ưu tiên tên chính xác
  trước so khớp bỏ dấu; không cộng nhầm `Résumé.pdf` với `Resume.pdf`. Hiểu câu hỏi
  “mỗi/từng/each” PDF qua metadata thật, không dùng model để đoán số trang.
- [x] **UX-01 — Sửa câu hỏi và chọn lại nguồn DONE:** thêm thao tác ngay trên câu
  chưa trả lời được; khôi phục câu hỏi/ngôn ngữ/nguồn cũ khi còn hợp lệ, không tự gửi.
  Nêu số trang chưa xử lý và phân biệt nguồn mâu thuẫn với câu hỏi chưa rõ.
- [x] **UX-02 — Giữ thao tác khi polling DONE:** cập nhật tiến độ job không dựng lại
  bộ lọc và checkbox thư viện nếu danh sách tài liệu không đổi.
  **246 tests hiện hành + 164 tests hồi quy hỏi đáp PASS**; một positive control cũ
  thiếu fixture không chạy. Không thêm dependency hoặc file báo cáo rời. Tests model
  có kiểm soát xác minh provenance, không phải predictions Gemini thật; chưa xác nhận
  chất lượng semantic toàn bộ PDF hoặc giao diện trực quan do không có browser kết nối.
  CI source `0d8b5a1a`: Windows/Linux, package và container PASS. Ba ca HTTP local
  trên runtime cuối PASS (0,027–0,036s), không gọi model.

## Tối ưu truy hồi và RAM — 02/11

- [x] **OPT-01 — BM25 nhẹ RAM DONE (`ed7cac5f`):** chia sẻ chuỗi token bất biến,
  tính IDF một lần mỗi query term, giữ thứ tự cộng điểm và tie-break. Index thật
  918 đoạn: phần RAM token/counter **18,00 → 5,84 MiB**; 100 lượt search
  **0,1222 → 0,0980s**. Đây là bộ phận truy hồi, không phải RAM toàn app.
- [x] **OPT-02 — Dense search tránh copy ma trận DONE:** phạm vi đủ mọi hàng dùng
  ma trận float64 hiện có; filter một phần vẫn lấy đúng hàng. 100 lượt tính điểm
  **0,4399 → 0,2254s**, peak cấp phát tạm **7,217 → 0,105 MiB**; thứ hạng và điểm
  trên ca đối chiếu giống baseline, không đổi model/ngưỡng/candidate limit.
- [x] **OPT-03 — Dùng lại metadata nguồn đã nạp DONE:** chỉ reuse khi identity của
  file khớp; đổi/xóa/thay thế index làm mất hiệu lực cache. Với 4 PDF đã load:
  chuẩn bị metadata thời gian **1,6777 → 0,0037s**, phần RAM giữ thêm **46,37 →
  0,01 MiB**; metadata và proof giống nhau. **208 tests hiện hành + 164 hỏi đáp
  + 17 truy hồi tương thích PASS**. Một positive control và module failure-case
  lịch sử thiếu evaluation/fixture đã dọn không chạy, không tính PASS.
  100 HTTP metadata local: **p95 0,0293s**, max **0,0338s**, 0 model calls;
  đây không phải nghiệm thu 100 câu AI hoặc semantic quality mọi PDF.
  CI Windows/Linux, package/container PASS; task chỉ chốt trong phạm vi đã đo.

## Đọc PDF và OCR — yêu cầu bổ sung 02/11

- [x] **OCR-07 — Hoàn tất scan nhanh hơn, giữ CPU nhẹ DONE (`22baa126`):** bỏ
  đọc lặp registry/index, chia sẻ riêng metadata đã commit và cache manifest nhỏ
  có giới hạn; chia lô theo thời gian OCR thật thay vì thời gian I/O/index.
  Scan EREER 16 trang qua HTTP: baseline **32,766s**, hai lượt cuối **11,686s /
  10,396s**, đủ 16/16 trang và cùng hash toàn văn. Hỏi phần đầu **5,640s / 3,445s**.
  CPU toàn app/process con trên máy 20 luồng: trung bình **4,27% / 4,00%**, đỉnh
  **5,85% / 5,78%**. Giữ 1 OCR engine, 2 luồng CPU inference, model/quality cũ.
  **205 tests hiện hành + 15 tương thích registry/index PASS**; không thêm
  dependency hoặc báo cáo rời; CI Windows/Linux, package/container PASS.
  Đây là workload đã đo, không phải SLO mọi PDF.

- [x] **OCR-05 — Web app nhẹ CPU DONE (`4f19e9e3`):** mặc định 1 job tài liệu,
  1 OCR engine, 1 worker bảng và 2 luồng CPU inference; tắt tokenizer song song.
  Hỏi sớm trên 4 trang native hoặc 2 trang scan đã đọc, phần còn lại tiếp tục nền
  với coverage thật. Không coi phần chưa đọc là không có thông tin.
  HTTP local: PDF 148 trang hỏi phần đầu sau **10,88s**, scan 16 trang sau
  **10,64s**; hoàn tất lần lượt **114,79s / 31,75s**, đủ 148/148 và 16/16 trang.
  CPU app trung bình **4,74% / 4,31%** toàn máy 20 luồng, đỉnh **6,01% / 5,56%**;
  idle mẫu 2s gần 0%. Chưa đo nhiệt độ/RPM hoặc xác nhận máy yếu đạt cùng tốc độ.
- [x] **OCR-06 — Giảm chi phí lưu index DONE (`86843d81`):** ghi JSON thành khối,
  giữ nguyên format, checksum, fsync/atomic replace; file index 31,25 MB giống byte
  baseline. **199 tests hiện hành + 24 tương thích bảng PASS**, 3 ca thiếu corpus
  lịch sử không chạy; CI Windows/Linux, package/container PASS. Không thêm model,
  service hoặc artifact nghiệm thu mới.

- [x] **OCR-02 — Tốc độ và chữ nhỏ DONE (profile lịch sử):** render xám cho trang giấy, tăng độ phân
  giải có chọn lọc cho chữ nhỏ một cột; giữ RGB/độ phân giải cũ cho vùng ảnh màu.
  Profile đã đo dùng tối đa 4 worker; mặc định hiện tại 1 theo OCR-05/07.
  Không hạ giới hạn pixel, timeout hoặc coverage.
  Workload 5 PDF / 41 trang cần OCR, hai lần A/B: trung bình **8,42 → 6,59s**
  (nhanh hơn 21,8%, chỉ phần OCR). Sáu mẫu raster Việt/Anh có reference xác định:
  CER **34,01% → 0,58%** trên 4.998 ký tự; không suy thành accuracy mọi PDF.
- [x] **OCR-03 — Cache và upload DONE:** upload lại PDF có policy OCR cũ sẽ xử lý
  nâng cấp, giữ cùng tài liệu; policy hiện hành vẫn trả duplicate nhanh. Checkpoint,
  coverage và audit vùng ảnh khớp policy mới, không mất audit giữa các lô.
- [x] **OCR-04 — Không đọc lại bảng mỗi lô DONE (`c05007b0`):** tái dùng kết quả
  giải mã vật lý trong cùng job; ràng buộc source/visibility, cô lập từng snapshot
  và job, giải phóng khi hoàn tất hoặc lỗi. Không thêm cache/báo cáo trên đĩa.
  A/B toàn pipeline NUAE 148 trang: **122,51 → 94,94s**, bảng **3 → 1 lần đọc**,
  output giống hệt; phần đầu sẵn sàng **53,07s**, vẫn còn chi phí index lần đầu.
  **196 tests hiện hành PASS**, gồm 6 ca OCR thật local; CI không có font/model
  sẽ skip 6 ca này. Kiểm tra tương thích bảng: 24 PASS, 3 ca thiếu corpus cũ.
  CI Windows/Linux, package/container PASS. QA-07c accuracy nguồn thật còn mở;
  không tuyên bố mọi PDF đạt 99–100% hoặc mọi upload hoàn tất trong vài giây.

## Goal đã hoàn tất — cải thiện hỏi đáp PDF

Goal hoàn tất ngày **01/11/2026**, source **`cacb4bdd`**. Tập trung chất lượng trao đổi với người dùng,
không mở lại OCR/Docker hoặc qualification đã DONE nếu không có hồi quy.
Theo yêu cầu mới: lặp tái hiện → sửa → hồi quy, chỉ mời owner kiểm khi đã đạt
mục tiêu 99–100% trên bộ ca hợp lệ chốt trước và không còn lỗi nghiêm trọng đã biết.
Đếm riêng semantic quality, thiếu ý, từ chối nhầm và HTTP/schema; không tính ca
cần review gold là PASS. Không tạo JSON/log nghiệm thu rời nếu không cần thiết;
giữ checklist/kết quả trong tài liệu hiện có, chỉ thêm regression test khóa lỗi.

- [x] **ASK-01 — Rà soát ban đầu DONE:** C04 bị guard tên trường chặn cả hai
  lượt do tách nhầm tên/predicate và thiếu proof tên trong đoạn truy hồi; C02 có
  claim thời hạn đã kiểm chứng nhưng phần trả lời bỏ mất; A06 nhầm chức danh
  “hiệu trưởng” thành tên trường. Giữ các ca này làm hồi quy, dùng dữ liệu phản
  chứng/tên giả trong test; F24 vẫn review gold riêng, không sửa đáp án để tăng điểm.
- [x] **ASK-02 — Nhiều nguồn DONE:** sửa nhận diện tên trong nguồn được trích,
  chặn đảo số liệu và chuẩn hóa `TC`/`tín chỉ`. Đoạn văn bị trích thành bảng cột
  rỗng được giữ đủ dòng, không làm mất cấu trúc bảng thật. C01–C04 trả đúng nguồn
  trong lượt 60 HTTP trên `cacb4bdd`, không cache.
  Tests vẫn chặn mâu thuẫn nội bộ, tên bịa, sai phủ định và số liệu tráo nguồn.
- [x] **ASK-03 — Câu trả lời đủ nghĩa DONE:** giữ điều kiện, ngoại lệ, thời hạn,
  đối tượng, khoảng điểm và ngữ cảnh cùng hàng/mục nguồn. Chín ca thiếu ý
  F01/F04/F17/F19/F20/F25/F26/N01/N04 đã đủ ý trong lượt cuối; R06 cũng giữ lưu ý
  về các điều kiện khác trên nhánh local. Không đoán nhóm đầu vào hoặc cộng thêm
  lượt AI. Mục chưa khép, bảng thật, bằng chứng mơ hồ hoặc thông tin đã hiện đủ
  không được dùng để thêm/lặp ghi chú. Mọi phần bổ sung phải kiểm chứng lại.
  F24 giải thích thiếu bằng chứng từng kỳ, không suy từ tổng năm hoặc tự kết luận
  toàn tài liệu không đề cập. Bốn ca cần review gold/scope giữ riêng ở ASK-08.
- [x] **ASK-04 — Hội thoại tự nhiên DONE trong phạm vi lỗi đã xác định:** 4 hội thoại
  M01–M04/8 lượt giữ đúng trường, điểm, học kỳ và chủ đề. Role “hiệu trưởng” không
  còn bị nhận nhầm thành tên trường; thiếu thời điểm thì yêu cầu nguồn cập nhật.
  Regression dùng tên/đối tượng giả, không whitelist trường hoặc câu hỏi owner.
- [x] **ASK-05 — Tốc độ DONE trong workload đã đo:** 60 HTTP liên tục trên
  `cacb4bdd`, p95 **4,700s**, tối đa **7,735s**, không timeout hoặc lỗi provider;
  25 lượt local, 0 cache, 35 lượt có provider/37 attempts (2 lượt sửa diễn đạt).
  Giữ quota/cooldown; đây là thời gian hoàn tất, không phải TTFT hoặc cam kết mọi PDF.
- [x] **ASK-06 — Chốt goal DONE:** **173 tests hiện hành + 164 tương thích PASS**;
  1 test cũ thiếu corpus không chạy. Đủ **56 case / 60 HTTP trên cùng `cacb4bdd`**,
  155 file runtime không đổi; C01–C04, M01–M04 và thiếu ý đều được đối chiếu.
  Chấm dev: **52 PASS / 0 PARTIAL / 4 REVIEW_REQUIRED**; 52/52 ca đủ input/gold
  đạt trong bộ đã exposure, không phải chứng nhận độc lập hoặc accuracy mọi PDF.
  CI Windows/Linux, package/container PASS; code đã push đúng origin CampusAI.
- [x] **ASK-07 — OCR nhanh hơn DONE (`c54b2b8b`):** OCR song song có giới hạn,
  lô tăng theo tốc độ thực và chỉ encode đoạn mới/thay đổi. PDF scan 34 trang:
  toàn bộ pipeline **52,81 → 29,48s**, phần đầu sẵn sàng **4,27s**, đủ 34/34 trang;
  hash toàn văn giống baseline. Hai PDF scan/mixed chạy cùng lúc: OCR **14,92 →
  4,65s**, text/layout/confidence giống bản tuần tự. Đã kiểm cancel, partial timeout,
  checkpoint, giới hạn worker và rollback index. Đây là A/B warm một lượt/workload,
  không phải p95 hay chứng nhận accuracy trên mọi PDF; giữ nguyên FIX-03b trước đó.
- [ ] **ASK-08 — Review input/gold, giữ mở:** F02/F05/N03 cần nêu trường trong
  input hoặc nghiệm thu hành vi hỏi rõ nguồn; không dùng school label để trả thay.
  F24 cần bằng chứng quy định số tuần **từng kỳ** hoặc gold abstention đã review;
  tổng 30 tuần/năm không chứng minh mỗi kỳ tối thiểu 15 tuần. Không tự sửa gold,
  không đếm bốn ca thành PASS. Fresh holdout/public release vẫn theo gate riêng.

Không hard-code bộ owner vào runtime, không đưa gold/nhãn vào inference và
không hạ gate grounding/citation. Hoàn tất goal này là đóng các lỗi hỏi đáp đã
xác định và kiểm chứng; fresh holdout/review gold/public release vẫn theo gate riêng.

## Những lỗi đã xử lý

| ID | Kết quả |
|---|---|
| FIX-01 | OCR tự động, giữ cancel/retry và lịch sử job |
| FIX-02 | Hỏi trên phần đã đọc, hiển thị coverage và số trang gốc |
| FIX-03a | Tiếp tục OCR từ checkpoint hợp lệ qua các lô/restart |
| FIX-04a | Tách câu trả lời chính, trích đoạn và lỗi provider/quota |
| FIX-04b | Giữ điều kiện/deadline và quan hệ bảng khi phân bổ context |
| FIX-06 | Chờ slot có giới hạn thay vì từ chối ngay khi AI bận |
| FIX-07 | [x] DONE - Round-robin across three independent Gemini projects, skip projects on cooldown, and fail over quota only on HTTP 429 while preserving shared quota/cooldown state. R15 recorded 33 successful calls per project. The sample .env allows automatic pool selection when all three distinct credentials exist. |
| FIX-08 | Sửa từ chối nhầm đã tái hiện, đổi trường khi hỏi tiếp và quy đổi điểm từ nguồn |
| FIX-09 | [x] DONE — Nhận diện trường từ metadata/nội dung nguồn, xác minh khi quy định chưa rõ trường; giữ câu hỏi qua xác nhận/đổi trường. Sách, bài báo, hướng dẫn và PDF khác vẫn hỏi đáp nội dung bình thường. 25 tests PASS; HTTP 3 lượt đúng nguồn. |
| FIX-09b | [x] DONE — Khi viết tắt chưa có trong PDF, tối đa 1 lượt Gemini đối chiếu với tên trường trong nguồn được chọn; chỉ khớp rõ một trường mới tiếp tục câu hỏi gốc. Mơ hồ/lỗi API thì nói rõ và hỏi tên đầy đủ. Native `hust/HUST/Hust` đúng nguồn, chỉ 1 lượt đối chiếu; 44 tests liên quan PASS. |
| FIX-10 | [x] DONE — Thêm nút “Chọn tất cả” trong bộ chọn nguồn. Chọn mọi PDF sẵn sàng, không giới hạn 5 tài liệu; cập nhật checkbox và nút chọn/bỏ chọn đồng bộ. Kiểm tra callback/render PASS với 6 PDF sẵn sàng và 1 PDF chưa sẵn sàng. |
| FIX-11 | [x] DONE — Giữ chủ đề và trường đang hỏi khi nối tiếp/đổi trường (HUST → NUAE → HUST); tái dùng câu trả lời đã kiểm chứng đúng nguồn. 143 tests liên quan PASS; đã kiểm tra HTTP thật. |
| FIX-12 | [x] DONE — Câu hỏi tổng số trang bằng dạng số nhiều PDF/file được trả lời bằng metadata: HTTP thực tế 0,049s, không gọi model. |
| FIX-13 | [x] DONE — Tách “học trước” khỏi “tiên quyết”, bổ sung truy hồi địa chỉ/khóa áp dụng và nhận diện so sánh “giống/khác nhau”; vẫn chặn mâu thuẫn trong cùng nguồn. |
| FIX-14 | [x] DONE — Tra giới hạn đăng ký và khóa áp dụng từ mệnh đề nguồn rõ ràng, giữ điều kiện năm cuối, mức cảnh báo và học kỳ; không có nguồn đúng mẫu thì giữ pipeline model. Bốn ca HTTP 0,51–0,98s. |

## Hạ tầng bổ sung — 31/10/2026

- [x] **Supermemory:** dừng theo yêu cầu; không thêm SDK, key hoặc gửi hội thoại tới dịch vụ này.
- [x] **CI/CD implementation:** thêm GitHub Actions cho Windows/Linux, package và Docker;
  Release publish image GHCR, deploy opt-in có health check/rollback. 56 tests local
  PASS, Compose config PASS. Hướng dẫn: [ci-cd.md](docs/operations/ci-cd.md).
- [x] **CI run:** [run 41192650931](https://github.com/trbk07/campusai-university-rag/actions/runs/41192650931)
  trên source `dadfcfa0` PASS: 56 tests ở cả 4 môi trường, package, build image CPU,
  entrypoint và Compose. Publish/deploy chưa chạy vì chưa tạo Release/máy đích.
- [x] **Docker Windows prerequisites:** đã bật Virtual Machine Platform và WSL feature.
- [x] **WSL:** đã cài WSL 3.0.3 từ MSI Microsoft, kiểm tra SHA-256 và chữ ký hợp lệ.
- [x] **Docker local:** virtualization/hypervisor đã hoạt động sau restart;
  Docker Desktop 4.89.0 / Linux Engine 29.7.2 và container `hello-world` PASS.
  Đây là kiểm tra Engine, chưa phải nghiệm thu CampusAI chạy trong container.
- [ ] **Production deployment:** cần máy Linux/runner và environment; chưa triển khai thực tế.

## Nghiệm thu đang chốt — 01/11/2026

- [x] **FIX-03b — DONE:** 20 trang ảnh thật / 3 PDF, lặp 3 lần; 60/60 lượt trang,
  0 lỗi/timeout; p95 **1,874s/trang**, **12,676s/batch**. Workload/threshold được
  khóa trước đo. Đây là đo tốc độ OCR; độ đúng ký tự thuộc QA-07c.
- [x] **QA-03b — DONE:** khóa đủ 5 loại: native, scan, mixed, bảng trên PDF đang
  giữ, cộng 1 PDF font-mapping lỗi **có kiểm soát, ghi rõ synthetic**. Fixture font
  tái tạo được bằng test; không thay kiểm chất lượng font lỗi thực tế.
- [ ] **QA-07c:** đo extraction ≥98%, OCR ≥90%, evidence/retrieval ≥95% trên bộ
  đại diện với reference được review; không dùng confidence OCR thay accuracy.
- [x] **FIX-05a — DONE phần sửa đã kiểm:** giữ ý định câu hỏi tiếp; trả đủ điểm
  chữ/hệ 4 và so sánh bằng chứng riêng từng nguồn; xử lý đăng ký hè khẩu ngữ,
  học phần học trước; chặn suy diễn tổng tuần cả năm thành một học kỳ và kết luận
  thiếu thông tin khi chưa kiểm đủ nguồn. Không dùng ID/đáp án benchmark trong runtime.
- [ ] **FIX-05 — nghiệm thu chất lượng cuối:** phần sửa lỗi và chấm dev **DONE**
  ở ASK-01–ASK-06: đủ 60 lượt trên `cacb4bdd`, **52 PASS / 0 PARTIAL / 4 REVIEW_REQUIRED**.
  C04, điều kiện và nhánh local đã khắc phục. Còn review gold F24, scope
  F02/F05/N03 và nghiệm thu chính thức; không dùng điểm dev của bộ đã exposure
  thay independent review/holdout hoặc tự tạo owner sign-off.
- [x] **R-01 — DONE qualification profile trên `3289f41f`:** 112/112 HTTP,
  83 inference provider thật, 0 timeout/lỗi HTTP, 0 cache hit; p95 **8,514s**,
  RSS đỉnh **8,00% RAM**. Đạt nguyên ngưỡng ≥100 HTTP/≥54 inference, p95 ≤10s,
  timeout ≤0,5%, RSS ≤75%; không reset quota. Receipt: `owner112-final.json`.
- [x] **R-02 — DONE trên cùng lượt 112:** public schema/citation vật lý hợp lệ
  112/112; provider thực báo `gemini-3.5-flash-lite`, bind profile/index/source hash.
  Không có lỗi output schema. Đây không phải chứng nhận độ đúng semantic.
- [ ] **Fresh holdout:** đóng băng tập chưa exposure, protocol/ngưỡng trước đo;
  không dùng tập đã tuning làm holdout.
- [ ] **QA-09d:** vòng kiểm cuối và bàn giao candidate đã khóa.

R-01/R-02 ghi đúng bản đã đo. Bản vá parser bullet GPA sau `3289f41f` đã kiểm
tập trung: **4/4 HTTP PASS** trên `fc8a56af`; N06 trả đúng literal nguồn trong
0,539s, không cache/provider; 3 lượt còn lại dùng cache đã kiểm chứng. Nghiệm thu
chất lượng và bàn giao toàn bộ bản mới vẫn nằm ở FIX-05/QA-09d.
Hồi quy hiện hành trên `cacb4bdd`: **173 tests hiện tại + 164 tương thích = 337 PASS**;
1 test lịch sử thiếu fixture đã dọn không chạy, không tính PASS. Kết quả
106 + 164 trên `fc8a56af` giữ là mốc lịch sử.

Evidence local đang giữ: `data/operations/local-acceptance-20261101/`.
Lệnh đo dùng `scripts/release/measure_ocr.py`, collector HTTP dùng
`scripts/release/verify_answers.py`; không gửi expected/gold/school vào inference.
Chi tiết kết quả mới cập nhật tại [báo cáo tổng quan](docs/PROJECT_OVERVIEW.md).

Streaming mặc định OFF; p95 TTFT ≤5 giây chưa đạt nghiệm thu. Graph/reranker OFF.
R-03 cloud đã rút khỏi scope, không ghi PASS.

<a id="phase-13"></a>
<a id="bo-sung-phase-13"></a>
## Phase 13 — Cài đặt và đóng gói local

Đã có triển khai encoder pin, launcher, state root và script đóng gói; chưa
chốt nghiệm thu RC/cài sạch.

| Task | Việc cần hoàn tất |
|---|---|
| L13-01 | Khóa Windows/Python/browser, máy tham chiếu, profile/OCR/flags và giới hạn PDF |
| L13-02 | Dependency từ lock, revision/hash model, dung lượng và giấy phép |
| L13-03 | Source từ commit sạch, đủ UI/config/launcher/docs, không kèm secrets/state |
| L13-04 | Cài sạch gói phân phối vào đường dẫn có khoảng trắng, state/model riêng |
| L13-05 | Xác minh state root, quyền ghi/preflight và giữ quota/cooldown |
| L13-06 | Chốt hướng dẫn cài, dùng, backup/restore và lỗi thường gặp |
| L13-07 | Khóa candidate: source commit, ZIP/hash, dependency/model/profile |

Hướng dẫn: [local-install.md](docs/operations/local-install.md).
Asset: [runtime-assets.json](configs/local/runtime-assets.json).

<a id="phase-14"></a>
<a id="bo-sung-phase-14"></a>
## Phase 14 — Kiểm chứng và bàn giao

| Task | Điều kiện hoàn tất |
|---|---|
| L14-01 | Ma trận requirement → protocol/ngưỡng → kết quả và vấn đề còn mở |
| L14-02 | PDF đại diện, câu trả lời, citation và holdout; giữ cả ca lỗi |
| L14-03 | Đo riêng startup/upload/query, cold/warm/cache, latency/errors và RSS |
| L14-04 | Dữ liệu, secrets/dependency, local HTTP, upload và quyền nguồn trên gói cuối |
| L14-05 | Backup/restore và rollback thật, giữ PDF/job/quota/cooldown |
| L14-06 | Chẩn đoán version/profile, model/OCR, lỗi provider và vị trí dữ liệu |
| L14-07 | Ba lượt hồi quy đầy đủ trên RC cuối, smoke UI/HTTP, kiểm nguồn và ảnh hưởng source |
| L14-08 | Owner duyệt candidate cụ thể cùng hướng dẫn, giới hạn và cách quay về bản trước |

Mốc R-01 cũ: 100 HTTP/54 provider calls, p95 ≤10s, timeout ≤0,5%, RSS ≤75% RAM.
Nếu đổi workload local, khóa protocol mới trước chạy và báo riêng. Mốc PDF
đại diện: extraction ≥98%, OCR ≥90%, evidence/retrieval ≥95%, không mất/nhầm
trang. Đây vẫn là mục tiêu, chưa được xác nhận bởi đợt dọn file.

Thứ tự: chốt QA PDF/profile → cài và đóng gói → khóa candidate → kiểm chất
lượng/provider/dữ liệu/recovery → vòng cuối → owner duyệt bàn giao. Chỉ cập
nhật trạng thái có căn cứ; không tự mở lại task đã đóng.

## Duy trì

Giữ source, cấu hình chạy/cài, hướng dẫn và dữ liệu/model đang sử dụng. Kết quả
kiểm tra mới cập nhật vào báo cáo tổng quan; xóa đầu ra tạm khi hết cần thiết.
Đợt tinh gọn không tuyên bố nghiệm thu bản cuối, không gọi API chỉ để tạo báo
cáo và không reset quota. Commit/push qua `origin` CampusAI; legacy financial
remote chỉ để fetch.
