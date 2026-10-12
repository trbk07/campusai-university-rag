# Phase 8 v5 automated benchmark review

**AUTOMATED_REVIEW_COMPLETE. OFFICIALLY_APPROVED: false.**

- Reviewer: Codex — Automated AI Review (owner_delegated_ai).
- Reviewed at: 2026-10-11T02:29:30+00:00 (UTC).
- Benchmark SHA-256: `0001ed7e3c6ad932434c368eb0bf212110a5d6165a9a4af12a639eb09ce4a93d`
- 30 Accept / 0 Reject / 0 Pending; no human signature is claimed.
- V4's 28 unchanged decisions are retained after hash/provenance revalidation. Only its two rejected questions are repaired and re-reviewed here.
- Regression only; historical source exposure remains. Automated review completion is separate from the evaluation freeze manifest and product acceptance.

## 01. `p8-temporal-2021-adjustment-01`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Truyền thông quang (mã cũ ELT3213) là gì?
- Expected answer: `ELT3067`
- Gold claim: Theo đính chính năm 2021, học phần Truyền thông quang đổi mã từ ELT3213 thành ELT3067, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`, page 1, range [1, 1].
- Source row: 1 ELT3213 Truyền thông quang 3 ELT3067 Truyền thông quang 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 1; physical PDF page 1.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 1: cột hiện hành ghi ELT3213, cột điều chỉnh ghi ELT3067; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3067 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 1: cột hiện hành ghi ELT3213, cột điều chỉnh ghi ELT3067; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3067 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 1, PDF trang 1; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ ELT3213 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ ELT3213 được cho; mã trả lời ELT3067 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 02. `p8-temporal-2021-adjustment-02`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Mạng truyền thông máy tính 2: mã mới thay ELT3214 là mã nào?
- Expected answer: `ELT3062`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 2 đổi mã từ ELT3214 thành ELT3062, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`, page 1, range [1, 1].
- Source row: 2 ELT3214 Mạng truyền thông máy tính 2 3 ELT3062 Mạng truyền thông máy tính 2 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 2; physical PDF page 1.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 2: cột hiện hành ghi ELT3214, cột điều chỉnh ghi ELT3062; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3062 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 2: cột hiện hành ghi ELT3214, cột điều chỉnh ghi ELT3062; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3062 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 2, PDF trang 1; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ ELT3214 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ ELT3214 được cho; mã trả lời ELT3062 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 03. `p8-temporal-2021-adjustment-03`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, ELT3215 được đổi thành mã nào cho học phần Mạng truyền thông di động?
- Expected answer: `ELT3163`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông di động đổi mã từ ELT3215 thành ELT3163, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`, page 1, range [1, 1].
- Source row: 3 ELT3215 Mạng truyền thông di động 3 ELT3163 Mạng truyền thông di động 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 3; physical PDF page 1.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 3: cột hiện hành ghi ELT3215, cột điều chỉnh ghi ELT3163; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3163 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 3: cột hiện hành ghi ELT3215, cột điều chỉnh ghi ELT3163; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3163 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 3, PDF trang 1; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ ELT3215 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ ELT3215 được cho; mã trả lời ELT3163 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 04. `p8-temporal-2021-adjustment-04a`

- Question: Phụ lục đính chính ngày 27/08/2021 bổ sung mã học phần nào cho Khóa luận tốt nghiệp của chương trình CNTT định hướng thị trường Nhật Bản?
- Expected answer: `INT4050`
- Gold claim: Đính chính năm 2021 bổ sung mã INT4050 cho Khóa luận tốt nghiệp 7 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`, page 1, range [1, 1].
- Source row: 4  Khóa luận tốt nghiệp 7 INT4050 Khóa luận tốt nghiệp 7
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 4, cột CTĐT; physical PDF page 1.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 1, mục I dòng 4: ô mã cũ trống, mã bổ sung INT4050, Khóa luận tốt nghiệp 7 tín chỉ. Cột CTĐT bên phải xác nhận CNTT định hướng thị trường Nhật Bản. Không diễn giải ô trống thành một mã cũ giả.
- question_answer_correctness: **PASS** — PDF gốc trang 1, mục I dòng 4: ô mã cũ trống, mã bổ sung INT4050, Khóa luận tốt nghiệp 7 tín chỉ. Cột CTĐT bên phải xác nhận CNTT định hướng thị trường Nhật Bản. Không diễn giải ô trống thành một mã cũ giả.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục I, dòng 4, cột CTĐT, PDF trang 1; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1 và trang gốc. Cột CTĐT chỉ thấy đầy đủ trong PDF, không có trong quote bảng rút gọn; đã kiểm tra trực quan.
- clarity: **PASS** — Câu hỏi nói bổ sung mã và nêu chương trình Nhật Bản, phân biệt với nhóm Mạng máy tính phía trên.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Tên học phần/chương trình không chứa INT4050; cần tra dòng 4.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 05. `p8-temporal-2021-adjustment-04`

- Question: Với học phần Trải nghiệm và Khám phá về Robot, mã điều chỉnh theo văn bản UET năm 2021 là gì (mã trước đính chính: RBE1003)?
- Expected answer: `RBE1001`
- Gold claim: Theo đính chính năm 2021, học phần Trải nghiệm và Khám phá về Robot đổi mã từ RBE1003 thành RBE1001, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`, page 1, range [1, 1].
- Source row: 1 RBE1003 Trải nghiệm và Khám phá về Robot 2 RBE1001 Trải nghiệm và Khám phá về Robot 2
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 1; physical PDF page 1.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 1: cột hiện hành ghi RBE1003, cột điều chỉnh ghi RBE1001; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE1001 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 1, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 1: cột hiện hành ghi RBE1003, cột điều chỉnh ghi RBE1001; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE1001 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 1, PDF trang 1; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ RBE1003 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ RBE1003 được cho; mã trả lời RBE1001 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **PASS** — Đã đối chiếu v3 và PDF gốc: chỉ question thay đổi, gold/claims/evidence giữ nguyên. V4 hỏi mã mới RBE1001 thay vì đòi cả cặp mã; mã cũ RBE1003 được nêu làm điều kiện. Đây là sửa lệch phạm vi câu hỏi/đáp án, không hợp thức hóa gold sai.

## 06. `p8-temporal-2021-adjustment-05`

- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Thực hành thiết kế và xây dựng Robot 1, khi cột hiện hành ghi RBE2023?
- Expected answer: `RBE2021`
- Gold claim: Theo đính chính năm 2021, học phần Thực hành thiết kế và xây dựng Robot 1 đổi mã từ RBE2023 thành RBE2021, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 2 RBE2023 Thực hành thiết kế và xây dựng Robot 1 2 RBE2021 Thực hành thiết kế và xây dựng Robot 1 2
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 2; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 2: cột hiện hành ghi RBE2023, cột điều chỉnh ghi RBE2021; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE2021 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 2: cột hiện hành ghi RBE2023, cột điều chỉnh ghi RBE2021; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE2021 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 2, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ RBE2023 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ RBE2023 được cho; mã trả lời RBE2021 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 07. `p8-temporal-2021-adjustment-06`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Thực hành thiết kế và xây dựng Robot 2 (mã cũ RBE2024) là gì?
- Expected answer: `RBE2022`
- Gold claim: Theo đính chính năm 2021, học phần Thực hành thiết kế và xây dựng Robot 2 đổi mã từ RBE2024 thành RBE2022, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 3 RBE2024 Thực hành thiết kế và xây dựng Robot 2 2 RBE2022 Thực hành thiết kế và xây dựng Robot 2 2
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 3; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 3: cột hiện hành ghi RBE2024, cột điều chỉnh ghi RBE2022; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE2022 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 3: cột hiện hành ghi RBE2024, cột điều chỉnh ghi RBE2022; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE2022 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 3, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ RBE2024 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ RBE2024 được cho; mã trả lời RBE2022 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 08. `p8-temporal-2021-adjustment-07`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Đồ án 1: Thiết kế và xây dựng Robot 1: mã mới thay RBE3023 là mã nào?
- Expected answer: `RBE3021`
- Gold claim: Theo đính chính năm 2021, học phần Đồ án 1: Thiết kế và xây dựng Robot 1 đổi mã từ RBE3023 thành RBE3021, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 4 RBE3023 Đồ án 1: Thiết kế và xây dựng Robot 1 2 RBE3021 Đồ án 1: Thiết kế và xây dựng Robot 1 2
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 4; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 4: cột hiện hành ghi RBE3023, cột điều chỉnh ghi RBE3021; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE3021 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 4: cột hiện hành ghi RBE3023, cột điều chỉnh ghi RBE3021; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE3021 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 4, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ RBE3023 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.Hai dấu hai chấm hơi cứng nhưng không làm thay đổi đối tượng hoặc gây hai cách hiểu.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ RBE3023 được cho; mã trả lời RBE3021 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 09. `p8-temporal-2021-adjustment-08`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, RBE3024 được đổi thành mã nào cho học phần Đồ án 2: Thiết kế và xây dựng Robot 2?
- Expected answer: `RBE3022`
- Gold claim: Theo đính chính năm 2021, học phần Đồ án 2: Thiết kế và xây dựng Robot 2 đổi mã từ RBE3024 thành RBE3022, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 5 RBE3024 Đồ án 2: Thiết kế và xây dựng Robot 2 2 RBE3022 Đồ án 2: Thiết kế và xây dựng Robot 2 2
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 5; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 5: cột hiện hành ghi RBE3024, cột điều chỉnh ghi RBE3022; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE3022 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 5: cột hiện hành ghi RBE3024, cột điều chỉnh ghi RBE3022; cùng học phần và cùng 2 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE3022 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 5, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ RBE3024 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ RBE3024 được cho; mã trả lời RBE3022 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 10. `p8-temporal-2021-adjustment-09`

- Question: Với học phần Thiết kế kiểu dáng công nghiệp, mã điều chỉnh theo văn bản UET năm 2021 là gì (mã trước đính chính: REB3016)?
- Expected answer: `RBE3016`
- Gold claim: Theo đính chính năm 2021, học phần Thiết kế kiểu dáng công nghiệp đổi mã từ REB3016 thành RBE3016, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 6 REB3016 Thiết kế kiểu dáng công nghiệp 3 RBE3016 Thiết kế kiểu dáng công nghiệp 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 6; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 6: cột hiện hành ghi REB3016, cột điều chỉnh ghi RBE3016; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE3016 đúng chiều đối chiếu.REB3016 là chữ in trong cột cũ, không tự sửa thành RBE3016 trước khi so sánh.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 6: cột hiện hành ghi REB3016, cột điều chỉnh ghi RBE3016; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold RBE3016 đúng chiều đối chiếu.REB3016 là chữ in trong cột cũ, không tự sửa thành RBE3016 trước khi so sánh.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 6, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ REB3016 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ REB3016 được cho; mã trả lời RBE3016 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **PASS** — Đã đối chiếu v3 và PDF gốc: chỉ question thay đổi, gold/claims/evidence giữ nguyên. V4 hỏi mã mới RBE3016 thay vì đòi cả cặp mã; mã cũ REB3016 được nêu làm điều kiện. Đây là sửa lệch phạm vi câu hỏi/đáp án, không hợp thức hóa gold sai.

## 11. `p8-temporal-2021-adjustment-10`

- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Mạng truyền thông máy tính 1, khi cột hiện hành ghi ELT3212E?
- Expected answer: `ELT3046E`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 1 đổi mã từ ELT3212E thành ELT3046E, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 9 ELT3212E Mạng truyền thông máy tính 1 3 ELT3046E Mạng truyền thông máy tính 1 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 9; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 9: cột hiện hành ghi ELT3212E, cột điều chỉnh ghi ELT3046E; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3046E đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 9: cột hiện hành ghi ELT3212E, cột điều chỉnh ghi ELT3046E; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3046E đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 9, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ ELT3212E và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ ELT3212E được cho; mã trả lời ELT3046E không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 12. `p8-temporal-2021-adjustment-11`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Mạng truyền thông máy tính 2 (mã cũ ELT3214E) là gì?
- Expected answer: `ELT3062E`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 2 đổi mã từ ELT3214E thành ELT3062E, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 10 ELT3214E Mạng truyền thông máy tính 2 3 ELT3062E Mạng truyền thông máy tính 2 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 10; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 10: cột hiện hành ghi ELT3214E, cột điều chỉnh ghi ELT3062E; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3062E đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 10: cột hiện hành ghi ELT3214E, cột điều chỉnh ghi ELT3062E; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold ELT3062E đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục II, dòng 10, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ ELT3214E và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ ELT3214E được cho; mã trả lời ELT3062E không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 13. `p8-temporal-2021-adjustment-12`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Giới thiệu về Hàng không Vũ trụ: mã mới thay AER1002 là mã nào?
- Expected answer: `AER1001`
- Gold claim: Theo đính chính năm 2021, học phần Giới thiệu về Hàng không Vũ trụ đổi mã từ AER1002 thành AER1001, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`, page 2, range [2, 2].
- Source row: 1 AER1002 Giới thiệu về Hàng không Vũ trụ 3 AER1001 Giới thiệu về Hàng không Vũ trụ 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 1; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 1: cột hiện hành ghi AER1002, cột điều chỉnh ghi AER1001; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold AER1001 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 2, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 1: cột hiện hành ghi AER1002, cột điều chỉnh ghi AER1001; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold AER1001 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 1, PDF trang 2; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER1002 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER1002 được cho; mã trả lời AER1001 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 14. `p8-temporal-2021-adjustment-13`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, AER2002 được đổi thành mã nào cho học phần Cơ học chất lỏng?
- Expected answer: `EMA2008`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học chất lỏng đổi mã từ AER2002 thành EMA2008, giữ nguyên 4 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`, page 3, range [3, 3].
- Source row: 2 AER2002 Cơ học chất lỏng 4 EMA2008 Cơ học chất lỏng 4
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 2; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 2: cột hiện hành ghi AER2002, cột điều chỉnh ghi EMA2008; cùng học phần và cùng 4 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA2008 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 2: cột hiện hành ghi AER2002, cột điều chỉnh ghi EMA2008; cùng học phần và cùng 4 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA2008 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 2, PDF trang 3; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER2002 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER2002 được cho; mã trả lời EMA2008 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 15. `p8-temporal-2021-adjustment-14`

- Question: Với học phần Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ, mã điều chỉnh theo văn bản UET năm 2021 là gì (mã trước đính chính: AER2009)?
- Expected answer: `AER2005`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ đổi mã từ AER2009 thành AER2005, giữ nguyên 4 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`, page 3, range [3, 3].
- Source row: 3 AER2009 Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ 4 AER2005 Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ 4
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 3; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 3: cột hiện hành ghi AER2009, cột điều chỉnh ghi AER2005; cùng học phần và cùng 4 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold AER2005 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 3: cột hiện hành ghi AER2009, cột điều chỉnh ghi AER2005; cùng học phần và cùng 4 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold AER2005 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 3, PDF trang 3; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER2009 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER2009 được cho; mã trả lời AER2005 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **PASS** — Đã đối chiếu v3 và PDF gốc: chỉ question thay đổi, gold/claims/evidence giữ nguyên. V4 hỏi mã mới AER2005 thay vì đòi cả cặp mã; mã cũ AER2009 được nêu làm điều kiện. Đây là sửa lệch phạm vi câu hỏi/đáp án, không hợp thức hóa gold sai.

## 16. `p8-temporal-2021-adjustment-15`

- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Hình hoạ kỹ thuật và CAD, khi cột hiện hành ghi AER2006?
- Expected answer: `EMA2032`
- Gold claim: Theo đính chính năm 2021, học phần Hình hoạ kỹ thuật và CAD đổi mã từ AER2006 thành EMA2032, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`, page 3, range [3, 3].
- Source row: 4 AER2006 Hình hoạ kỹ thuật và CAD 3 EMA2032 Hình hoạ kỹ thuật và CAD 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 4; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 4: cột hiện hành ghi AER2006, cột điều chỉnh ghi EMA2032; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA2032 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 4: cột hiện hành ghi AER2006, cột điều chỉnh ghi EMA2032; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA2032 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 4, PDF trang 3; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER2006 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER2006 được cho; mã trả lời EMA2032 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 17. `p8-temporal-2021-adjustment-16`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Hệ thống đẩy (mã cũ AER3039) là gì?
- Expected answer: `AER3003`
- Gold claim: Theo đính chính năm 2021, học phần Hệ thống đẩy đổi mã từ AER3039 thành AER3003, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`, page 3, range [3, 3].
- Source row: 5 AER3039 Hệ thống đẩy 3 AER3003 Hệ thống đẩy 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 5; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 5: cột hiện hành ghi AER3039, cột điều chỉnh ghi AER3003; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold AER3003 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 5: cột hiện hành ghi AER3039, cột điều chỉnh ghi AER3003; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold AER3003 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 5, PDF trang 3; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER3039 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER3039 được cho; mã trả lời AER3003 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 18. `p8-temporal-2021-adjustment-17`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Thử nghiệm kết cấu thiết bị không gian: mã mới thay AER3040 là mã nào?
- Expected answer: `EMA3048`
- Gold claim: Theo đính chính năm 2021, học phần Thử nghiệm kết cấu thiết bị không gian đổi mã từ AER3040 thành EMA3048, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`, page 3, range [3, 3].
- Source row: 6 AER3040 Thử nghiệm kết cấu thiết bị không gian 3 EMA3048 Thử nghiệm kết cấu thiết bị không gian 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 6; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 6: cột hiện hành ghi AER3040, cột điều chỉnh ghi EMA3048; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA3048 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 6: cột hiện hành ghi AER3040, cột điều chỉnh ghi EMA3048; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA3048 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 6, PDF trang 3; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER3040 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER3040 được cho; mã trả lời EMA3048 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 19. `p8-temporal-2021-adjustment-18`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, AER3037 được đổi thành mã nào cho học phần Cơ học quỹ đạo bay?
- Expected answer: `EMA3014`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học quỹ đạo bay đổi mã từ AER3037 thành EMA3014, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`, page 3, range [3, 3].
- Source row: 7 AER3037 Cơ học quỹ đạo bay 3 EMA3014 Cơ học quỹ đạo bay 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 7; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 7: cột hiện hành ghi AER3037, cột điều chỉnh ghi EMA3014; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA3014 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 7: cột hiện hành ghi AER3037, cột điều chỉnh ghi EMA3014; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA3014 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 7, PDF trang 3; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER3037 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER3037 được cho; mã trả lời EMA3014 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu hỏi không thuộc bốn câu thay đổi ở v4; vẫn được review từ nguồn gốc.

## 20. `p8-temporal-2021-adjustment-19`

- Question: Với học phần Điều khiển điện thủy khí, mã điều chỉnh theo văn bản UET năm 2021 là gì (mã trước đính chính: AER3041)?
- Expected answer: `EMA3064`
- Gold claim: Theo đính chính năm 2021, học phần Điều khiển điện thủy khí đổi mã từ AER3041 thành EMA3064, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`, page 3, range [3, 3].
- Source row: 8 AER3041 Điều khiển điện thủy khí 3 EMA3064 Điều khiển điện thủy khí 3
- Source check: QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 8; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 8: cột hiện hành ghi AER3041, cột điều chỉnh ghi EMA3064; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA3064 đúng chiều đối chiếu.
- question_answer_correctness: **PASS** — PDF gốc trang 3, QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 8: cột hiện hành ghi AER3041, cột điều chỉnh ghi EMA3064; cùng học phần và cùng 3 tín chỉ. Câu hỏi yêu cầu mã điều chỉnh, nên gold EMA3064 đúng chiều đối chiếu.
- evidence_support: **PASS** — QĐ 641/QĐ-ĐT ngày 27/08/2021, mục III, dòng 8, PDF trang 3; đã đối chiếu quote trong chunk fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Tên học phần, mã cũ AER3041 và mốc đính chính 2021 xác định dòng cần tra; không hỏi mã đang có hiệu lực năm 2026.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Chỉ mã cũ AER3041 được cho; mã trả lời EMA3064 không có trong câu hỏi. Không nhầm mã E với mã không E.
- v4_revision_integrity: **PASS** — Đã đối chiếu v3 và PDF gốc: chỉ question thay đổi, gold/claims/evidence giữ nguyên. V4 hỏi mã mới EMA3064 thay vì đòi cả cặp mã; mã cũ AER3041 được nêu làm điều kiện. Đây là sửa lệch phạm vi câu hỏi/đáp án, không hợp thức hóa gold sai.

## 21. `p8-fact-awards-effective-date`

- Question: Theo Điều 2 của Quyết định khen thưởng ban hành năm 2023, quy định được áp dụng từ tháng/năm nào?
- Expected answer: `09/2023`
- Gold claim: 09/2023
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p1_s8_c1`, page 1, range [1, 1].
- Source row: được áp dụng từ tháng 09 năm 2023.
- Source check: Quyết định 798/QĐ-ĐHCN, Điều 2; physical PDF page 1.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 2 phân biệt ngày có hiệu lực (ngày ký 15/08/2023) với tháng áp dụng (09/2023). Câu hỏi hỏi tháng áp dụng nên gold 09/2023 đúng; không được chấm 08/2023 là đáp án tương đương.
- question_answer_correctness: **PASS** — Điều 2 phân biệt ngày có hiệu lực (ngày ký 15/08/2023) với tháng áp dụng (09/2023). Câu hỏi hỏi tháng áp dụng nên gold 09/2023 đúng; không được chấm 08/2023 là đáp án tương đương.
- evidence_support: **PASS** — Quyết định 798/QĐ-ĐHCN, Điều 2, PDF trang 1; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p1_s8_c1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Câu hỏi ghi năm 2023 và hỏi tháng/năm áp dụng, phân biệt rõ với ngày ký.
- schema_and_corpus: **PASS** — Schema v1, split test, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Câu hỏi chỉ cho năm văn bản, không cho tháng 09; vẫn cần đọc Điều 2.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## 22. `p8-fact-valedictorian-average`

- Question: Theo Điều 3 của Quy định khen thưởng UET năm 2023, khi xét danh hiệu dành cho sinh viên có điểm trung bình toàn khóa cao nhất, điểm đó được so sánh trong phạm vi nào?
- Expected answer: `Trong ngành học.`
- Gold claim: Trong ngành học.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`, page 2, range [2, 3].
- Source row: có điểm trung bình toàn khóa học cao nhất trong ngành học
- Source check: Quy định kèm QĐ 798, Điều 3; physical PDF page 2.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 3 ở trang 2 ghi điểm trung bình toàn khóa cao nhất trong ngành học. Câu mới bỏ tên danh hiệu có chứa phạm vi trả lời; vẫn hỏi chính phạm vi so sánh trong điều khoản, nên gold Trong ngành học không đổi. Không hỏi điểm số hay đổi đối tượng so sánh.
- question_answer_correctness: **PASS** — Điều 3 ở trang 2 ghi điểm trung bình toàn khóa cao nhất trong ngành học. Câu mới bỏ tên danh hiệu có chứa phạm vi trả lời; vẫn hỏi chính phạm vi so sánh trong điều khoản, nên gold Trong ngành học không đổi. Không hỏi điểm số hay đổi đối tượng so sánh.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 3, PDF trang 2; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Nêu văn bản, năm và Điều 3; hỏi phạm vi so sánh điểm toàn khóa, không dùng tên danh hiệu để gợi phạm vi.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Cụm ngành học và tên danh hiệu Thủ khoa ngành học đều đã bỏ khỏi câu hỏi; câu hỏi không liệt kê lựa chọn chứa đáp án.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.
- v5_repair_review: **PASS** — Chỉ sửa question để bỏ leakage đã bị Reject; kiểm tra lại điều khoản gốc và giữ nguyên gold, evidence, qid, split. Không dùng output model để lựa chọn cách sửa.

## 23. `p8-fact-excellent-student-floor`

- Question: Theo Điều 4, sinh viên đạt danh hiệu Sinh viên Xuất sắc không được có học phần nào dưới mức điểm nào?
- Expected answer: `C+.`
- Gold claim: C+.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`, page 2, range [2, 3].
- Source row: không có học phần nào có điểm dưới C+
- Source check: Quy định kèm QĐ 798, Điều 4; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 4 ghi không có học phần nào dưới C+. Gold C+ là ngưỡng từng học phần, không nhầm với xếp loại học tập/rèn luyện Xuất sắc hoặc điểm GPA.
- question_answer_correctness: **PASS** — Điều 4 ghi không có học phần nào dưới C+. Gold C+ là ngưỡng từng học phần, không nhầm với xếp loại học tập/rèn luyện Xuất sắc hoặc điểm GPA.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 4, PDF trang 3; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1 và trang gốc. page=2 là trang đầu chunk kéo dài [2,3]; điều khoản trả lời thực tế nằm trang 3.
- clarity: **PASS** — Câu hỏi xác định danh hiệu và điều kiện điểm thấp nhất của từng học phần.
- schema_and_corpus: **PASS** — Schema v1, split test, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Tên danh hiệu Xuất sắc không cho biết ngưỡng C+; ngưỡng không có trong câu hỏi.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## 24. `p8-fact-good-student-conduct`

- Question: Theo Điều 5, kết quả rèn luyện tối thiểu để đạt danh hiệu Sinh viên Giỏi là mức nào?
- Expected answer: `Tốt trở lên.`
- Gold claim: Tốt trở lên.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`, page 2, range [2, 3].
- Source row: kết quả rèn luyện đạt loại Tốt trở lên
- Source check: Quy định kèm QĐ 798, Điều 5; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 5 tách học tập loại Giỏi trở lên và rèn luyện loại Tốt trở lên. Gold Tốt trở lên đúng cho rèn luyện; câu hỏi không yêu cầu liệt kê mọi điều kiện của danh hiệu.
- question_answer_correctness: **PASS** — Điều 5 tách học tập loại Giỏi trở lên và rèn luyện loại Tốt trở lên. Gold Tốt trở lên đúng cho rèn luyện; câu hỏi không yêu cầu liệt kê mọi điều kiện của danh hiệu.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 5, PDF trang 3; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1 và trang gốc. page=2 là trang đầu chunk kéo dài [2,3]; điều khoản trả lời thực tế nằm trang 3.
- clarity: **PASS** — Chỉ rõ kết quả rèn luyện, tránh nhầm với kết quả học tập loại Giỏi.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Câu hỏi nêu danh hiệu Giỏi nhưng không nêu mức rèn luyện Tốt.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## 25. `p8-fact-collective-contribution-gpa`

- Question: Theo Điều 6, điểm trung bình học tập tối thiểu để xét danh hiệu Sinh viên có đóng góp cho công tác tập thể là bao nhiêu?
- Expected answer: `Từ 3.0 trở lên.`
- Gold claim: Từ 3.0 trở lên.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`, page 2, range [2, 3].
- Source row: kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên
- Source check: Quy định kèm QĐ 798, Điều 6; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 6 ghi kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên. Gold giữ cả ngưỡng và chiều bất đẳng thức; các điều kiện khác không bị trình bày như đã được thỏa mãn.
- question_answer_correctness: **PASS** — Điều 6 ghi kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên. Gold giữ cả ngưỡng và chiều bất đẳng thức; các điều kiện khác không bị trình bày như đã được thỏa mãn.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 6, PDF trang 3; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1 và trang gốc. page=2 là trang đầu chunk kéo dài [2,3]; điều khoản trả lời thực tế nằm trang 3.
- clarity: **PASS** — Hỏi riêng điểm trung bình tối thiểu, không suy diễn đây là điều kiện đủ duy nhất.
- schema_and_corpus: **PASS** — Schema v1, split test, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Số 3.0 không xuất hiện trong câu hỏi.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## 26. `p8-fact-thesis-excellence-result`

- Question: Theo Điều 7 của Quy định khen thưởng UET năm 2023, Hội đồng chấm phải công nhận kết quả bảo vệ khóa luận/đồ án ở mức nào để sinh viên được xét danh hiệu quy định tại điều này?
- Expected answer: `Xuất sắc.`
- Gold claim: Xuất sắc.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`, page 2, range [2, 3].
- Source row: được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc
- Source check: Quy định kèm QĐ 798, Điều 7; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 7 ở trang 3 yêu cầu Hội đồng công nhận kết quả bảo vệ khóa luận/đồ án Xuất sắc. Câu mới hỏi đúng mức kết quả này nhưng bỏ tên danh hiệu làm lộ mức xếp loại. Gold Xuất sắc và nguồn giữ nguyên; không biến một điều kiện thành toàn bộ điều kiện đủ.
- question_answer_correctness: **PASS** — Điều 7 ở trang 3 yêu cầu Hội đồng công nhận kết quả bảo vệ khóa luận/đồ án Xuất sắc. Câu mới hỏi đúng mức kết quả này nhưng bỏ tên danh hiệu làm lộ mức xếp loại. Gold Xuất sắc và nguồn giữ nguyên; không biến một điều kiện thành toàn bộ điều kiện đủ.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 7, PDF trang 3; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2 và trang gốc. page=2 là trang đầu chunk kéo dài [2,3]; điều khoản trả lời thực tế nằm trang 3.
- clarity: **PASS** — Xác định Điều 7 của quy định khen thưởng 2023 và kết quả do Hội đồng chấm công nhận; không cần tên danh hiệu trong câu hỏi.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Từ Xuất sắc đã bỏ hoàn toàn khỏi câu hỏi; tên văn bản và số điều chỉ định nguồn, không cho biết mức đánh giá.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.
- v5_repair_review: **PASS** — Chỉ sửa question để bỏ leakage đã bị Reject; kiểm tra lại điều khoản gốc và giữ nguyên gold, evidence, qid, split. Không dùng output model để lựa chọn cách sửa.

## 27. `p8-fact-collective-advanced-share`

- Question: Theo Điều 8, tối thiểu bao nhiêu phần trăm sinh viên của tập thể phải đạt học tập và rèn luyện loại Khá trở lên?
- Expected answer: `70%.`
- Gold claim: 70%.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`, page 2, range [2, 3].
- Source row: Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên
- Source check: Quy định kèm QĐ 798, Điều 8; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 8 về Tập thể Tiên tiến ghi “Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên”. Gold 70% là tỷ lệ điều kiện; “tối thiểu” diễn đạt ngưỡng đạt tiêu chuẩn, không bổ sung một mức khác.
- question_answer_correctness: **PASS** — Điều 8 về Tập thể Tiên tiến ghi “Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên”. Gold 70% là tỷ lệ điều kiện; “tối thiểu” diễn đạt ngưỡng đạt tiêu chuẩn, không bổ sung một mức khác.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 8, PDF trang 3; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2 và trang gốc. page=2 là trang đầu chunk kéo dài [2,3]; điều khoản trả lời thực tế nằm trang 3.
- clarity: **PASS** — Hỏi tỷ lệ sinh viên đạt đồng thời học tập và rèn luyện Khá trở lên; không nhầm tỷ lệ Giỏi tại Điều 9.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Câu hỏi không chứa tỷ lệ 70%.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## 28. `p8-fact-collective-excellent-share`

- Question: Theo Điều 9, tỷ lệ tối thiểu sinh viên đạt danh hiệu Sinh viên Giỏi trong tập thể Xuất sắc là bao nhiêu?
- Expected answer: `10%.`
- Gold claim: 10%.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`, page 2, range [2, 3].
- Source row: có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên Giỏi”
- Source check: Quy định kèm QĐ 798, Điều 9; physical PDF page 3.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 9 ghi có từ 10% sinh viên trở lên đạt danh hiệu Sinh viên Giỏi; gold 10% đúng ngưỡng hỏi. Không nhầm với 70% tại Điều 8 hoặc điều kiện có sinh viên Xuất sắc.
- question_answer_correctness: **PASS** — Điều 9 ghi có từ 10% sinh viên trở lên đạt danh hiệu Sinh viên Giỏi; gold 10% đúng ngưỡng hỏi. Không nhầm với 70% tại Điều 8 hoặc điều kiện có sinh viên Xuất sắc.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 9, PDF trang 3; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2 và trang gốc. page=2 là trang đầu chunk kéo dài [2,3]; điều khoản trả lời thực tế nằm trang 3.
- clarity: **PASS** — Nêu rõ tập thể Xuất sắc và tỷ lệ sinh viên Giỏi cần hỏi.
- schema_and_corpus: **PASS** — Schema v1, split holdout, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Hai tên danh hiệu chỉ xác định đối tượng; không tiết lộ tỷ lệ 10%.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## 29. `p8-fact-entrance-award-amount`

- Question: Theo Điều 10, phần thưởng cho sinh viên đạt tiêu chí thành tích tuyển sinh tương đương khoản học phí của thời gian nào?
- Expected answer: `Năm học đầu tiên trong khóa học.`
- Gold claim: Năm học đầu tiên trong khóa học.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p4_s18_c1`, page 4, range [4, 4].
- Source row: bằng học phí của năm học đầu tiên trong khóa học
- Source check: Quy định kèm QĐ 798, Điều 10; physical PDF page 4.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điều 10 quy định phần thưởng bằng học phí năm học đầu tiên trong khóa học. Gold trả lời khoảng thời gian, không bịa số tiền; câu hỏi điều kiện hóa việc đã đạt tiêu chí tuyển sinh.
- question_answer_correctness: **PASS** — Điều 10 quy định phần thưởng bằng học phí năm học đầu tiên trong khóa học. Gold trả lời khoảng thời gian, không bịa số tiền; câu hỏi điều kiện hóa việc đã đạt tiêu chí tuyển sinh.
- evidence_support: **PASS** — Quy định kèm QĐ 798, Điều 10, PDF trang 4; đã đối chiếu quote trong chunk 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p4_s18_c1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Hỏi thời gian học phí tương đương nên không cần suy ra mức học phí bằng tiền.
- schema_and_corpus: **PASS** — Schema v1, split test, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Khoảng thời gian năm học đầu tiên không được cho trong câu hỏi.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## 30. `p8-fact-exam-warning-deduction`

- Question: Theo trích đoạn Quy chế đào tạo 2014, sinh viên bị khiển trách do nhìn bài người khác hoặc trao đổi bài trong giờ thi bị trừ bao nhiêu phần trăm điểm bài thi?
- Expected answer: `25%.`
- Gold claim: 25%.
- Evidence: `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1`, chunk `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`, page 1, range [1, 1].
- Source row: bị trừ 25% số điểm đạt được của bài thi học phần đó
- Source check: Trích Quy chế 5115/QĐ-ĐHQGHN (2014), Điều 32.4(a); physical PDF page 1.
- Decision: [x] Accept  [ ] Reject
- Reviewer note: Điểm (a) khiển trách trừ 25% số điểm bài thi học phần; điểm (b) cảnh cáo mới trừ 50%. Gold 25% khớp đúng mức kỷ luật đã nêu, không cần suy diễn tái phạm.
- question_answer_correctness: **PASS** — Điểm (a) khiển trách trừ 25% số điểm bài thi học phần; điểm (b) cảnh cáo mới trừ 50%. Gold 25% khớp đúng mức kỷ luật đã nêu, không cần suy diễn tái phạm.
- evidence_support: **PASS** — Trích Quy chế 5115/QĐ-ĐHQGHN (2014), Điều 32.4(a), PDF trang 1; đã đối chiếu quote trong chunk 3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1 và trang gốc. Trang/điều khoản hỗ trợ đúng giá trị trả lời.
- clarity: **PASS** — Nêu rõ đã bị khiển trách; phân biệt với cảnh cáo. Thiếu từ lần đầu trong mô tả lỗi không đổi mức kỷ luật đã xác định.
- schema_and_corpus: **PASS** — Schema v1, split test, answer_grounded, claim/evidence thống nhất; PDF SHA-256 thuộc corpus manifest. Câu hỏi xác định chủ đề/điều khoản có trong corpus.
- no_answer_leakage: **PASS** — Câu hỏi không chứa 25% hay 50%.
- v4_revision_integrity: **NOT_APPLICABLE** — Câu factual không thay đổi giữa v3 và v4; đã đối chiếu điều khoản gốc.

## Review disposition

- Human signature: NOT_PROVIDED.
- OFFICIALLY_APPROVED: false; Phase 8 PASS: false.
- Owner-delegated AI review is complete. The separate freeze records only the immutable regression-evaluation population, not human approval or product quality.
- A gate explicitly requiring human signoff remains PENDING_HUMAN_APPROVAL; this report cannot satisfy it.
