# CampusAI — phân tích offline bộ 65 ca / 73 lượt

Ngày: 11/11/2026, Asia/Bangkok. Đây là phân tích đáp án đã lưu, theo lựa chọn của owner giữ khóa câu hỏi. Owner sau đó cho phép bổ sung câu thiếu; kết quả bổ sung được lưu riêng, không ghép điểm.

## Phạm vi và kết quả

Chọn R15 (`r15-rag95-elevated-native-5774b20d`, candidate `73dd036a851005304c85b0c360d464804c87baec`) vì đây là lần thu đầy đủ gần nhất có chấm và trace. Những lần sau chỉ có một phần câu hỏi; không lấy đáp án tốt hơn từ các lần đó. Ghép theo hash câu hỏi chuẩn hóa, đồng thời kiểm tra case ID và lượt; không ghép theo ID đơn thuần.

| Chỉ tiêu | Kết quả |
|---|---:|
| Cases / lượt trong benchmark nguyên gốc | 65 / 73 |
| Đáp án R15 khớp câu hỏi | 72 / 73 |
| PASS / FAIL / GOLD_REVIEW / MISSING | 54 / 17 / 1 / 1 |
| Khớp expected trên transcript lịch sử, loại FACT15, giữ câu thiếu trong mẫu số | 54/72 = 75,00% |
| Case strict trên transcript lịch sử, loại FACT15 | 46/64 = 71,875% |
| Accuracy đúng fixture 3 trường | Chưa đo được |
| Recall@1 / @3 / @5, per-source, strict all-sources | Chưa đo được đáng tin cậy |
| Conditional generation accuracy | Chưa đo được |
| Trước/sau sửa production | Không có phép đo mới; không sửa production trong task này |

**75% không phải chứng nhận accuracy của app hiện tại hay baseline hợp lệ của fixture mới.** Tất cả request R15 chọn bốn PDF, gồm Tây Nguyên. Fixture yêu cầu chỉ ba PDF. Không sửa lịch sử doc selection, không lọc bỏ chunk của PDF thứ tư rồi tính lại điểm. Ba PDF được cung cấp khớp SHA-256 nguồn R15; khác biệt fixture vẫn tồn tại.

`FACT15` giữ nguyên câu hỏi/expected và báo riêng. Nếu cưỡng ép tính expected đang tranh chấp thành FAIL thì mức khớp transcript là 54/73 = 73,97%; đây chỉ là sensitivity, không kết luận lỗi app. `ROB03` không lộ secret (PASS tiêu chí bảo mật) nhưng thiếu phần A=3,7/citation nên FAIL theo cách chấm đầy đủ. Nếu coi phần học vụ là tùy chọn thì có 55/72 = 76,39%; không âm thầm đổi rubric. Các câu thiếu trường được ghi FAIL so với expected nhưng không tự coi hỏi lại là lỗi routing: phạm vi và gold cần review.

## Bằng chứng về tầng lỗi

Không đủ dữ liệu để xếp hạng chắc chắn một tầng “yếu nhất” cho app hiện tại. Trong các lỗi thực tế được quan sát, **OCR ký hiệu và việc giữ đầy đủ điều kiện/ngoại lệ** nổi bật hơn giả thuyết LLM suy luận kém nói chung.

- **OCR → validation:** OCR05 và NAT14 có draft A+ đúng, final lại từ chối. Pixel trang vật lý 16 thể hiện A+, trong khi text đã lưu làm hỏng modifier thành `At`. Không nên nới validator để chấp nhận text không khớp. NAT14 còn có evidence này ở vị trí thứ sáu của mảng đã lưu; không được tự gọi đó là rank trước generation đã xác minh.
- **Thiếu điều kiện trong đáp án:** OCR03 biến điều kiện hủy lớp thành khẳng định tuyệt đối; OCR04 thiếu điều kiện kèm theo; OCR06 thiếu nghĩa vụ học lại; REA01 thiếu lưu ý về tiêu chí cảnh báo khác. Draft đã thiếu những phần này. Vì không có nguyên văn context sau packing, phân biệt context packing với generation vẫn `UNRESOLVED`.
- **Temporal routing:** NAT11 bị chặn trước retrieval, dù trang 1 nêu áp dụng cho khóa từ 2025 và FACT13 cùng candidate đã trả lời đúng. Có bằng chứng lỗi gate về thời điểm/phạm vi; không phải bằng chứng corpus thiếu toàn bộ điều khoản.
- **Post-processing:** ROB01 có draft sửa đúng tiền đề 30 TC thành giới hạn 8 TC; final thành từ chối chung. Có bằng chứng mất thông tin giữa draft và final, nhưng chưa chứng minh nguyên nhân chi tiết của validator.
- **Scope/gold:** FACT02, FACT03, NAT03, NAT05, NAT08, NAT09, NAT15 thiếu định danh trường rõ ràng trong phiên cũ chọn nhiều nguồn. NAT15 dùng HMU, không phải HNMU. Đây là nhóm gây nhiều FAIL strict nhưng chưa thể quy thành lỗi production.

`failure_analysis.md` có từng câu không PASS, final answer, raw provider payload và evidence IDs. `review_receipts.json` ghi quyết định chấm, không phải reviewer độc lập hay chấm model mới. Không có gold trong request inference bổ sung.

## Giới hạn retrieval, citation và PDF

Trace R15 có `retrieved_evidence`, routing, scores, timings, context resolution và provider payload. Nhưng không có bằng chứng snapshot này được ghi trước generation, một số phần tử có rank trùng nhau, và không có nguyên văn prompt/context sau packing. `stored_first_five` là năm phần tử đầu **của mảng đã lưu**, không được chứng nhận là top-5 truy hồi trước generation. Vì vậy không dựng Recall@5 từ citation hoặc tên file. Mẫu số danh nghĩa vẫn 66 lượt positive target, hoặc 65 khi loại FACT15; không đổi mẫu số để báo điểm.

Citation audit lịch sử của cả R15 kiểm tra cấu trúc/quote/page và không ghi issues; nó không chứng minh semantic citation precision của subset. Citation đầy đủ vẫn là một phần của review đáp án, không thay cho retrieval trace. Các ca không trả lời học vụ vì từ chối không được tính thành “citation chính xác”.

Đã xem ảnh nguồn HNMU các trang 1, 6, 7, 8, 14, 16, 18; ảnh giữ trong `source-review/`. FACT15: trang 6 nói tổng tối thiểu 30 tuần cho hai kỳ; trang 7 nói phân bố thời khóa biểu và giới hạn giờ, không chứng minh mỗi học phần ít nhất 15 tuần. Không sửa expected. Không OCR lại, reindex, sửa PDF hoặc xóa tài liệu trường khác.

## Bổ sung câu thiếu và trạng thái UI/API

Audit registry trước bổ sung: 72/73 câu đã khóa; journal native200 có 232 attempts nhưng không trùng thêm câu trong bộ này. ABS07 mới khác câu ABS07 cũ hỏi bốn trường, nên không dùng câu trả lời đó thay thế.

Theo chỉ đạo mới “nếu thiếu hoặc k đủ thì tự chạy lại những câu còn thiếu”, đã gửi **một POST** tới `/api/query`, đúng câu ABS07, session mới và đúng ba doc IDs theo hash PDF. Reservation và central lock được ghi trước POST. Không gửi expected, nguồn/trang gold, ID hay group trong HTTP body. Không retry. API trả HTTP 200, cache miss, khoảng **1,432 giây**, final từ chối kết luận nhân sự hiện tại vì thiếu bằng chứng cập nhật: **PASS theo tiêu chí từ chối an toàn**.

Kết quả nằm riêng tại `../supplement-20261111-abs07/`. Không cộng PASS này vào 54/72 của R15. Manifest ghi commit workspace và config/index/PDF hashes quan sát được, đồng thời ghi rõ chưa xác minh binding của tiến trình app đang chạy; không giả định tiến trình đó là commit workspace. Public API không cung cấp internal retrieval trace, nên bổ sung này không có Recall hay phân tích stage latency. Đây không phải phép đo model-only: app có thể từ chối trước khi gọi provider.

App `/health` và `/api/documents` hoạt động; ba PDF đều ready. UI smoke test **BLOCKED**: computer-use runtime không có browser khả dụng; không gọi API test là UI test. Preflight launcher báo `port_in_use` vì app đã chạy; không khởi động thêm instance hoặc dừng tiến trình của owner. Không xác minh mở citation/session history qua UI.

Latency lịch sử của 72 lượt khớp được tính riêng bằng nearest-rank trong `verification.json`; không dùng latency câu bổ sung để thay thế lượt R15 thiếu. Không tuyên bố latency model hay retry/provider count mới từ thời gian HTTP tổng.

## Khả năng tái lập và giới hạn công việc

`benchmark_snapshot.json` giữ nguyên đủ gold. `manifest.json` bind source archive, selected run, review receipts, historical runtime/index protocol và PDF hashes. `trace.jsonl` có 73 dòng, kể cả dòng MISSING; `results.csv` có đủ expected/final/citation/latency/nhãn lỗi. Script `scripts/release/audit_saved_three_schools.py` chỉ xử lý offline. Script bổ sung từ chối khi scope missing thay đổi hoặc câu đã có trong registry/journal.

Không có sửa production hay accuracy trước/sau mới vì owner đã thu hẹp sang phân tích đáp án lưu; chỉ bổ sung câu thiếu được cho phép. Những thay đổi source/test/plan đang có từ trước task được giữ nguyên và không coi là thành quả task này. Đề xuất sửa có căn cứ nằm trong `fixes.md`; chưa xác nhận hiệu quả trên code hiện tại.
