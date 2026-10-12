# Áp dụng kinh nghiệm từ med_rag vào CampusAI

Đối chiếu mã nguồn repo người dùng cung cấp tại commit
[`e30839adb0c2396c5ffcbbd70237eccf1acf883b`](https://github.com/Jmhzbmcn2/med_rag/tree/e30839adb0c2396c5ffcbbd70237eccf1acf883b).
Hai dự án cùng dùng truy xuất tài liệu để trả lời theo bằng chứng. CampusAI tiếp
tục xử lý tài liệu đại học và citation theo tài liệu/trang; không nhập dữ liệu y tế.
Các thay đổi dưới đây được triển khai theo cấu trúc sẵn có của CampusAI.

| Kinh nghiệm đối chiếu | Quyết định áp dụng |
| --- | --- |
| [Hybrid dense/BM25, RRF và reranker tùy chọn](https://github.com/Jmhzbmcn2/med_rag/blob/e30839adb0c2396c5ffcbbd70237eccf1acf883b/backend/medical_rag/retrieval.py) | CampusAI đã có. Giữ fallback Phase 6 khi reranker lỗi; không thêm hệ truy xuất hoặc dịch vụ embedding. |
| [Tính ngân sách sau khi ghép header và nội dung](https://github.com/Jmhzbmcn2/med_rag/blob/e30839adb0c2396c5ffcbbd70237eccf1acf883b/backend/medical_rag/ingestion/chunking.py) | Sửa serializer context: tính cả metadata, dấu phân cách và nhãn cắt; bỏ block không còn chỗ cho trích đoạn. Dùng bộ ước lượng ký tự hiện có, không nhận là tokenizer chính xác của provider. |
| Header nguồn/mục rõ ràng | Dùng metadata citation đã có; loại header index được sinh tự động khỏi phần nội dung gửi LLM bằng `source_body(..., decode_tables=False)`. Giữ nguyên `RetrievalResult.content`, JSON bảng, doc/chunk/page/table và kiểm chứng quote. Đổi cache prompt thành `grounding-context-v2`. |
| [Đo article hit riêng với chunk hit](https://github.com/Jmhzbmcn2/med_rag/blob/e30839adb0c2396c5ffcbbd70237eccf1acf883b/backend/scripts/eval_retrieval.py) | Thêm chẩn đoán document/evidence vào evaluator hiện có qua `include_document_diagnostics=True` hoặc `--document-diagnostics`. Chỉ tính kết quả có provenance hợp lệ, đúng scope; evidence phải khớp doc/chunk/page. Không dùng document hit để thay gold-evidence recall. Mặc định giữ nguyên dictionary báo cáo lịch sử. |

Không chuyển sang Qdrant/OpenRouter hoặc thêm framework. Những thành phần này
không giải quyết trực tiếp blocker ranking/grounded-answer đang có. Repo tham
khảo cũng không cung cấp bằng chứng để đánh dấu gate của CampusAI PASS.

## Kết quả kiểm chứng

- Full offline suite: **1093 passed, 2 live integration tests skipped**.
- Replay đúng hash của **829 F0-dev** đã lưu; 473 câu answerable. Không chạy lại
  retrieval/model/provider, không mở primary test/holdout, không chọn cấu hình.
- Context tổng giảm từ **3.414.175** xuống **3.141.635 ký tự** (**7,98%**), số block
  giữ ở **2.291**. Đây là tiết kiệm ký tự; chưa phải token thực tế hay accuracy.
- Trong top-5 baseline đã ghi: **455** câu có đủ gold evidence, **16** câu tìm đúng
  mọi tài liệu nhưng thiếu đoạn, **2** câu không tìm đúng tài liệu gold.
- Trong pool tối đa 40: **471** câu có đủ gold evidence; còn **2** câu thiếu tài
  liệu gold. Kết quả chỉ ra điểm cần xử lý nằm chủ yếu ở chọn đoạn/ranking sau
  candidate generation. Chẩn đoán này chưa chứng minh đạt uplift +3%.
- Các trường hợp vượt ngân sách/dư nhãn cắt được tái hiện bằng regression test;
  dữ liệu dev ở ngân sách 12.000 ký tự không có trường hợp vượt trước hoặc sau.

Lệnh tái hiện từ root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=evaluation/results/phase7-completion-20261004/med-rag-adoption-regression-20261008.xml
.\.venv\Scripts\python.exe evaluation/results/phase7-completion-20261004/reproduce_med_rag_adoption_20261008.py
```

Bằng chứng: [audit kèm input/source hash và kết quả từng query](../../evaluation/results/phase7-completion-20261004/med-rag-adoption-audit-20261008.json),
[JUnit](../../evaluation/results/phase7-completion-20261004/med-rag-adoption-regression-20261008.xml).
Các prompt/pilot packet đã đóng băng trước đổi serializer vẫn là bằng chứng lịch
sử; cần packet mới với identity hiện tại trước khi đo live, không sửa packet cũ.

## Liên hệ Phase 7

Đây là cải thiện context cho P7-06 và công cụ chẩn đoán cho P7-09, chưa hoàn thành
hai task hoặc gate liên quan. Vẫn **6/20 task DONE, 3/19 gate PASS**.
Tiếp tục theo [plan gốc](../../plan.md) và
[ledger](../../evaluation/results/phase7-completion-20261004/completion_task_ledger.json).
Ưu tiên giao thức baseline/comparator hợp lệ và tính khả thi trên các lỗi dev
đã xác định; giữ nguyên ngưỡng nghiệm thu và quyết định dừng candidate cũ.
