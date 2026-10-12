# Phase 8 temporal/comparison review

**Status: OWNER REVIEW REQUIRED. This packet is not approved or frozen.**

- Draft JSONL SHA-256: `950b7df8da1f63147d5b1749a746889df3b101da5f8e1c445b7a270ab2ae22f9`
- Source PDF SHA-256: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`
- Combined 300-row qid-set SHA-256: `3b0cbbee8ae4384822be781c75a31c979593301bee1212f76b58cf4d3ee5e2d2`
- Connected groups / largest / cross-split: `107` / `23` / `0`
- Query type counts: `{"prerequisite_or_multi_hop": 38, "single_hop_fact": 0, "table_or_calculation": 142, "temporal_or_comparison": 20, "unanswerable_or_adversarial": 158}`
- Missing required query types: `single_hop_fact`
- Historical exact-code overlap: 13/20 facts.
- The source PDF was previously in the retrieval index; do not call this fresh validation.
- Review each question, answer, and evidence row. Mark exactly one decision per row.

## 01. `p8-temporal-2021-adjustment-01`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Truyền thông quang (mã cũ ELT3213) là gì?
- Expected answer: `ELT3067`
- Gold claim: Theo đính chính năm 2021, học phần Truyền thông quang đổi mã từ ELT3213 thành ELT3067, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 1 ELT3213 Truyền thông quang 3 ELT3067 Truyền thông quang 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 02. `p8-temporal-2021-adjustment-02`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Mạng truyền thông máy tính 2: mã mới thay ELT3214 là mã nào?
- Expected answer: `ELT3062`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 2 đổi mã từ ELT3214 thành ELT3062, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 2 ELT3214 Mạng truyền thông máy tính 2 3 ELT3062 Mạng truyền thông máy tính 2 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 03. `p8-temporal-2021-adjustment-03`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, ELT3215 được đổi thành mã nào cho học phần Mạng truyền thông di động?
- Expected answer: `ELT3163`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông di động đổi mã từ ELT3215 thành ELT3163, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 3 ELT3215 Mạng truyền thông di động 3 ELT3163 Mạng truyền thông di động 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 04. `p8-temporal-2021-adjustment-04a`

- Question: Phụ lục đính chính ngày 27/08/2021 bổ sung mã học phần nào cho Khóa luận tốt nghiệp của chương trình CNTT định hướng thị trường Nhật Bản?
- Expected answer: `INT4050`
- Gold claim: Đính chính năm 2021 bổ sung mã INT4050 cho Khóa luận tốt nghiệp 7 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 4  Khóa luận tốt nghiệp 7 INT4050 Khóa luận tốt nghiệp 7
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 05. `p8-temporal-2021-adjustment-04`

- Question: Với học phần Trải nghiệm và Khám phá về Robot, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: RBE1003).
- Expected answer: `RBE1001`
- Gold claim: Theo đính chính năm 2021, học phần Trải nghiệm và Khám phá về Robot đổi mã từ RBE1003 thành RBE1001, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 1 RBE1003 Trải nghiệm và Khám phá về Robot 2 RBE1001 Trải nghiệm và Khám phá về Robot 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 06. `p8-temporal-2021-adjustment-05`

- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Thực hành thiết kế và xây dựng Robot 1, khi cột hiện hành ghi RBE2023?
- Expected answer: `RBE2021`
- Gold claim: Theo đính chính năm 2021, học phần Thực hành thiết kế và xây dựng Robot 1 đổi mã từ RBE2023 thành RBE2021, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 2 RBE2023 Thực hành thiết kế và xây dựng Robot 1 2 RBE2021 Thực hành thiết kế và xây dựng Robot 1 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 07. `p8-temporal-2021-adjustment-06`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Thực hành thiết kế và xây dựng Robot 2 (mã cũ RBE2024) là gì?
- Expected answer: `RBE2022`
- Gold claim: Theo đính chính năm 2021, học phần Thực hành thiết kế và xây dựng Robot 2 đổi mã từ RBE2024 thành RBE2022, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 3 RBE2024 Thực hành thiết kế và xây dựng Robot 2 2 RBE2022 Thực hành thiết kế và xây dựng Robot 2 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 08. `p8-temporal-2021-adjustment-07`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Đồ án 1: Thiết kế và xây dựng Robot 1: mã mới thay RBE3023 là mã nào?
- Expected answer: `RBE3021`
- Gold claim: Theo đính chính năm 2021, học phần Đồ án 1: Thiết kế và xây dựng Robot 1 đổi mã từ RBE3023 thành RBE3021, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 4 RBE3023 Đồ án 1: Thiết kế và xây dựng Robot 1 2 RBE3021 Đồ án 1: Thiết kế và xây dựng Robot 1 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 09. `p8-temporal-2021-adjustment-08`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, RBE3024 được đổi thành mã nào cho học phần Đồ án 2: Thiết kế và xây dựng Robot 2?
- Expected answer: `RBE3022`
- Gold claim: Theo đính chính năm 2021, học phần Đồ án 2: Thiết kế và xây dựng Robot 2 đổi mã từ RBE3024 thành RBE3022, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 5 RBE3024 Đồ án 2: Thiết kế và xây dựng Robot 2 2 RBE3022 Đồ án 2: Thiết kế và xây dựng Robot 2 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 10. `p8-temporal-2021-adjustment-09`

- Question: Với học phần Thiết kế kiểu dáng công nghiệp, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: REB3016).
- Expected answer: `RBE3016`
- Gold claim: Theo đính chính năm 2021, học phần Thiết kế kiểu dáng công nghiệp đổi mã từ REB3016 thành RBE3016, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 6 REB3016 Thiết kế kiểu dáng công nghiệp 3 RBE3016 Thiết kế kiểu dáng công nghiệp 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 11. `p8-temporal-2021-adjustment-10`

- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Mạng truyền thông máy tính 1, khi cột hiện hành ghi ELT3212E?
- Expected answer: `ELT3046E`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 1 đổi mã từ ELT3212E thành ELT3046E, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 9 ELT3212E Mạng truyền thông máy tính 1 3 ELT3046E Mạng truyền thông máy tính 1 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 12. `p8-temporal-2021-adjustment-11`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Mạng truyền thông máy tính 2 (mã cũ ELT3214E) là gì?
- Expected answer: `ELT3062E`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 2 đổi mã từ ELT3214E thành ELT3062E, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 10 ELT3214E Mạng truyền thông máy tính 2 3 ELT3062E Mạng truyền thông máy tính 2 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 13. `p8-temporal-2021-adjustment-12`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Giới thiệu về Hàng không Vũ trụ: mã mới thay AER1002 là mã nào?
- Expected answer: `AER1001`
- Gold claim: Theo đính chính năm 2021, học phần Giới thiệu về Hàng không Vũ trụ đổi mã từ AER1002 thành AER1001, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 1 AER1002 Giới thiệu về Hàng không Vũ trụ 3 AER1001 Giới thiệu về Hàng không Vũ trụ 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 14. `p8-temporal-2021-adjustment-13`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, AER2002 được đổi thành mã nào cho học phần Cơ học chất lỏng?
- Expected answer: `EMA2008`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học chất lỏng đổi mã từ AER2002 thành EMA2008, giữ nguyên 4 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 2 AER2002 Cơ học chất lỏng 4 EMA2008 Cơ học chất lỏng 4
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 15. `p8-temporal-2021-adjustment-14`

- Question: Với học phần Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: AER2009).
- Expected answer: `AER2005`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ đổi mã từ AER2009 thành AER2005, giữ nguyên 4 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 3 AER2009 Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ 4 AER2005 Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ 4
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 16. `p8-temporal-2021-adjustment-15`

- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Hình hoạ kỹ thuật và CAD, khi cột hiện hành ghi AER2006?
- Expected answer: `EMA2032`
- Gold claim: Theo đính chính năm 2021, học phần Hình hoạ kỹ thuật và CAD đổi mã từ AER2006 thành EMA2032, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 4 AER2006 Hình hoạ kỹ thuật và CAD 3 EMA2032 Hình hoạ kỹ thuật và CAD 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 17. `p8-temporal-2021-adjustment-16`

- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Hệ thống đẩy (mã cũ AER3039) là gì?
- Expected answer: `AER3003`
- Gold claim: Theo đính chính năm 2021, học phần Hệ thống đẩy đổi mã từ AER3039 thành AER3003, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 5 AER3039 Hệ thống đẩy 3 AER3003 Hệ thống đẩy 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 18. `p8-temporal-2021-adjustment-17`

- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Thử nghiệm kết cấu thiết bị không gian: mã mới thay AER3040 là mã nào?
- Expected answer: `EMA3048`
- Gold claim: Theo đính chính năm 2021, học phần Thử nghiệm kết cấu thiết bị không gian đổi mã từ AER3040 thành EMA3048, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 6 AER3040 Thử nghiệm kết cấu thiết bị không gian 3 EMA3048 Thử nghiệm kết cấu thiết bị không gian 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 19. `p8-temporal-2021-adjustment-18`

- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, AER3037 được đổi thành mã nào cho học phần Cơ học quỹ đạo bay?
- Expected answer: `EMA3014`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học quỹ đạo bay đổi mã từ AER3037 thành EMA3014, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 7 AER3037 Cơ học quỹ đạo bay 3 EMA3014 Cơ học quỹ đạo bay 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 20. `p8-temporal-2021-adjustment-19`

- Question: Với học phần Điều khiển điện thủy khí, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: AER3041).
- Expected answer: `EMA3064`
- Gold claim: Theo đính chính năm 2021, học phần Điều khiển điện thủy khí đổi mã từ AER3041 thành EMA3064, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 8 AER3041 Điều khiển điện thủy khí 3 EMA3064 Điều khiển điện thủy khí 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## Review disposition

- Reviewer identity:
- Reviewed JSONL SHA-256 (must match above):
- All 20 rows reviewed: [ ]
- Source exposure classification acknowledged: [ ]
- Overall decision: [ ] Accept for regression benchmark  [ ] Reject
- Signature/date:

Approval here does not claim fresh validation; provider egress logs remain outside the retained-file exposure scan.
