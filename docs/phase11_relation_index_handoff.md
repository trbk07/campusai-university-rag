# Tra cứu quan hệ học phần có nguồn

Chỉ mục SQLite tùy chọn hỗ trợ tiên quyết trực tiếp, truy vấn chiều ngược đầy đủ
và đường đi hai cạnh. Mỗi kết luận dẫn về hàng/ô trong tài liệu gốc. Bản pilot
dùng bốn tài liệu đã có; không thêm dịch vụ, dependency, model hay corpus.

## Bật và tắt

`CampusAIQueryService(..., relation_index=None)` là mặc định OFF. Profile web hiện
có tiếp tục dùng đường Phase 10. Bật bằng dependency injection trong profile
đã nghiệm thu, sau khi index tài liệu và sidecar đã build xong:

```python
from campusai.rag.relation_index import RelationIndex
from campusai.rag.service import CampusAIQueryService

relations = RelationIndex(index_root)
relations.rebuild(selected_doc_ids)  # Offline/job, không chạy trong query.
service = CampusAIQueryService(
    retriever, generator, default_mode="hybrid", relation_index=relations,
)
```

`index_root` là thư mục hybrid chứa `<doc_id>/bm25.json` và `dense.json`; retriever
và sidecar phải dùng cùng nguồn. `selected_doc_ids` là danh sách nguồn được
quản lý cho index, không thay thế quyền của từng request. Chỉ bật profile khác
sau qualification trên nguồn của profile đó. MVP khởi động không cần sidecar.

Rollback: bỏ `relation_index` hoặc truyền `None`, đóng service cũ và khởi động
service mới. Sidecar là derived artifact; có thể xóa sau khi dừng reader. Giữ
nguyên corpus/BM25/dense, protocol, baseline và bằng chứng nghiệm thu.

## Contract và phạm vi

- Identity riêng theo tài liệu/hash và metadata program/version; không gộp mã
  giống nhau giữa chương trình. Lưu hướng `môn phụ thuộc → môn tiên quyết`.
- Chỉ publish cạnh có một mã rõ ràng, hai endpoint và proof nguồn xác minh.
  Blank, nhiều mã/AND/OR, conflict, thiếu endpoint không trở thành cạnh.
- Hai cạnh là đường đi hai bước, không phải một cạnh tiên quyết trực tiếp mới.
  Không suy tương đương, chuyển đổi tín chỉ hoặc hiệu lực hiện hành toàn cục.
- Authorization, selected scope, filters và temporal resolver chạy trước lookup.
  Không dùng file name year làm ngày hiệu lực; không traversing nguồn ngoài quyền.
- Tối đa hai bước/hai adjacency lookup, 40 node/40 edge/40 evidence candidates.
  Fallback chia chung budget: tối đa hai search/two encoder queries, 20/search,
  một generation. Context tối đa 12.000 ký tự và token caps hiện có.
- Query shapes có contract trong `relations.py`; câu có điều kiện/hop không hỗ
  trợ được từ chối, không bỏ điều kiện để trả lời một phần. Câu thông thường
  vẫn đi đường cũ khi feature OFF hoặc không thuộc intent này.
- Fetch lại row/chunk nguồn và validators trước public answer. Một citation có
  nhiều fact cùng chunk dùng JSON array các hàng nguyên gốc, không ghép ô thành
  một hàng giả. Mọi hàng phải tồn tại trong cùng nguồn; quote cap giữ nguyên.

Ví dụ intent đã hỗ trợ (tên file phải thuộc scope được chọn):

```text
Theo <file>.pdf, học phần tiên quyết của INT2209 có mã gì và có bao nhiêu tín chỉ trong cùng tài liệu?
Trong <file>.pdf, liệt kê đầy đủ các học phần có PHI1004 là tiên quyết trực tiếp; dẫn nguồn cho từng quan hệ.
Trong <file>.pdf, đi theo hai bước tiên quyết liên tiếp bắt đầu từ EMA2012; nêu cả hai quan hệ và số tín chỉ của môn cuối chuỗi.
```

## Rebuild, lifecycle và lỗi

Sau update/delete/reindex, chạy `relations.rebuild(current_doc_ids)` trong job
ngoài query, rồi dùng reader/service mới. Không rebuild chỉ một subset khi muốn
giữ toàn bộ nguồn: danh sách build là toàn bộ tập nguồn sidecar cần quản lý.
Build idempotent khi source/extractor không đổi. SQLite và manifest được publish
bằng replace; nếu ngắt giữa hai file thì fingerprint không khớp và reader từ
chối bản nửa vời. Source đổi trong build/read cũng fail closed.

Manifest bind BM25/dense source hashes, extractor/schema/policy và DB. Source
stale/missing/deleted, corrupt DB/manifest hoặc policy đổi không được dùng proof
cũ. Answer cache bind graph/source generation, request/scope/context/policy;
không giữ cache lỗi. Cache/source maps có giới hạn. Direct intent tương thích
có thể fallback đường cũ khi graph chưa làm việc và còn budget; inverse/chain
hai cạnh không được rơi xuống đường một bước. Chỉ mục không tự rebuild, retry
hay gọi provider trong request.

## Kiểm tra và tái hiện

Từ root repository, bật offline trước khi chạy. Cần original corpus/index và
artifact bundle tương ứng; không cần API key. Python environment theo project.

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
.venv/Scripts/python.exe -m evaluation.phase11.prepare
# Rebuild sidecar từ các hybrid index frozen trước acceptance (idempotent).
.venv/Scripts/python.exe -c "from evaluation.phase11.prepare import prepare; from evaluation.phase11.run import build_index,INDEX; from campusai.rag.relation_index import RelationIndex; p=prepare(); build_index(p); RelationIndex(INDEX).rebuild([s['doc_id'] for s in p['pilot_sources'].values()])"
.venv/Scripts/python.exe -m evaluation.phase11.accept --split all
# Dùng đúng execution path do lệnh trên in ra, không sửa receipt lịch sử.
.venv/Scripts/python.exe -m evaluation.phase11.review <execution.json>
.venv/Scripts/python.exe -m pytest -q tests/test_relation_index.py tests/test_relation_application.py
```

`accept` dựng lại pilot hybrid index từ nguồn frozen, không dùng gold để build
relation sidecar. Nó lưu execution mới, giữ các lần cũ. `review` đối chiếu đủ
16 qid với rubric frozen, từng cạnh/fact/row/quote, routing và public contract.
Baseline lịch sử trước prototype nằm trong artifact bundle cùng source snapshot;
không chạy code mới rồi đổi nhãn thành baseline cũ.

Raw, source renders, baseline, index và các receipt lớn nằm trong artifact store;
`evaluation/artifacts/manifest.json` giữ SHA-256, gzip URI và kích thước. Dùng
`evaluation.common.artifact_store.resolve_artifact(path)` để lấy đúng byte của
artifact đã nén. Giữ object bundle khi sao lưu/mang sang máy khác; Git không chứa
model weights, sidecar hay mọi raw output. Completion summary có danh sách
binding và roadmap snapshot tại exit, không bind plan đang tiếp tục thay đổi.

## Cách đọc kết quả

Nghiệm thu là 16 câu đã exposure (8 dev/8 acceptance), Automated AI Review;
không giả chữ ký con người hay fresh validation. Candidate trả lời deterministic
local nên không cần Gemini Chat/API cho 16 câu. Một request ngoài quyền giữ
HTTP 400 error contract của adapter; báo riêng 15 answer schemas/1 error contract.

Nhánh lợi ích đã khóa là QUALITY: sửa hai lỗi dev khác chain trước model,
không phải nhánh đo 40 warm observations/arm. Timing/RSS trong receipt là quan
sát local, có cold load và lỗi, không phải API SLO. Các output Chat lịch sử chỉ
carry review khi actual prompt/schema/source và public answer khớp; lịch sử
normalization/native-format lỗi được giữ. R-01/R-02 vẫn NOT PASSED. Các control
synthetic không cộng vào mẫu 16 câu thật hoặc suy thành độ chính xác mọi query.
