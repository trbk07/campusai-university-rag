# Phase 8 supplemental benchmark owner review

**Status: OWNER REVIEW REQUIRED. This packet is not approved or frozen.**

- Temporal draft JSONL SHA-256: `950b7df8da1f63147d5b1749a746889df3b101da5f8e1c445b7a270ab2ae22f9`
- Factual draft JSONL SHA-256: `0e147cbc9b229b98b89a95ecf2be28d8f71141c10271476f3cf88e4387e12633`
- Exact combined benchmark JSONL SHA-256: `b51e5c5adb6680716378e98448515309edd0ad7635edbdf791b7b5c550f72113`
- Source PDF SHA-256 values: `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1, 7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b, fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79`
- Combined 300-row qid-set SHA-256: `2e36cfdb7f605b8f57a99d20ea33a619b95e977dcff69e4d35d5f0a2deac2796`
- Connected groups / largest / cross-split: `117` / `22` / `0`
- Query type counts: `{"prerequisite_or_multi_hop": 33, "single_hop_fact": 10, "table_or_calculation": 135, "temporal_or_comparison": 20, "unanswerable_or_adversarial": 155}`
- Missing required query types: `none`
- Historical exact-code overlap in temporal draft: 13/20 facts.
- Both source PDFs were previously indexed; provider egress logs are not audited. Do not call this fresh validation.
- Review each question, answer, and evidence row. Mark exactly one decision per row.

## 01. `p8-temporal-2021-adjustment-01`

- Type: `temporal/comparison`; split: `holdout`
- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Truyền thông quang (mã cũ ELT3213) là gì?
- Expected answer: `ELT3067`
- Gold claim: Theo đính chính năm 2021, học phần Truyền thông quang đổi mã từ ELT3213 thành ELT3067, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, range `[1, 1]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 1 ELT3213 Truyền thông quang 3 ELT3067 Truyền thông quang 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 02. `p8-temporal-2021-adjustment-02`

- Type: `temporal/comparison`; split: `holdout`
- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Mạng truyền thông máy tính 2: mã mới thay ELT3214 là mã nào?
- Expected answer: `ELT3062`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 2 đổi mã từ ELT3214 thành ELT3062, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, range `[1, 1]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 2 ELT3214 Mạng truyền thông máy tính 2 3 ELT3062 Mạng truyền thông máy tính 2 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 03. `p8-temporal-2021-adjustment-03`

- Type: `temporal/comparison`; split: `holdout`
- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, ELT3215 được đổi thành mã nào cho học phần Mạng truyền thông di động?
- Expected answer: `ELT3163`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông di động đổi mã từ ELT3215 thành ELT3163, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, range `[1, 1]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 3 ELT3215 Mạng truyền thông di động 3 ELT3163 Mạng truyền thông di động 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 04. `p8-temporal-2021-adjustment-04a`

- Type: `temporal/comparison`; split: `holdout`
- Question: Phụ lục đính chính ngày 27/08/2021 bổ sung mã học phần nào cho Khóa luận tốt nghiệp của chương trình CNTT định hướng thị trường Nhật Bản?
- Expected answer: `INT4050`
- Gold claim: Đính chính năm 2021 bổ sung mã INT4050 cho Khóa luận tốt nghiệp 7 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, range `[1, 1]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 4  Khóa luận tốt nghiệp 7 INT4050 Khóa luận tốt nghiệp 7
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 05. `p8-temporal-2021-adjustment-04`

- Type: `temporal/comparison`; split: `holdout`
- Question: Với học phần Trải nghiệm và Khám phá về Robot, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: RBE1003).
- Expected answer: `RBE1001`
- Gold claim: Theo đính chính năm 2021, học phần Trải nghiệm và Khám phá về Robot đổi mã từ RBE1003 thành RBE1001, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 1, range `[1, 1]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p1_t1`
- Source row: 1 RBE1003 Trải nghiệm và Khám phá về Robot 2 RBE1001 Trải nghiệm và Khám phá về Robot 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 06. `p8-temporal-2021-adjustment-05`

- Type: `temporal/comparison`; split: `holdout`
- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Thực hành thiết kế và xây dựng Robot 1, khi cột hiện hành ghi RBE2023?
- Expected answer: `RBE2021`
- Gold claim: Theo đính chính năm 2021, học phần Thực hành thiết kế và xây dựng Robot 1 đổi mã từ RBE2023 thành RBE2021, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 2 RBE2023 Thực hành thiết kế và xây dựng Robot 1 2 RBE2021 Thực hành thiết kế và xây dựng Robot 1 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 07. `p8-temporal-2021-adjustment-06`

- Type: `temporal/comparison`; split: `holdout`
- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Thực hành thiết kế và xây dựng Robot 2 (mã cũ RBE2024) là gì?
- Expected answer: `RBE2022`
- Gold claim: Theo đính chính năm 2021, học phần Thực hành thiết kế và xây dựng Robot 2 đổi mã từ RBE2024 thành RBE2022, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 3 RBE2024 Thực hành thiết kế và xây dựng Robot 2 2 RBE2022 Thực hành thiết kế và xây dựng Robot 2 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 08. `p8-temporal-2021-adjustment-07`

- Type: `temporal/comparison`; split: `holdout`
- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Đồ án 1: Thiết kế và xây dựng Robot 1: mã mới thay RBE3023 là mã nào?
- Expected answer: `RBE3021`
- Gold claim: Theo đính chính năm 2021, học phần Đồ án 1: Thiết kế và xây dựng Robot 1 đổi mã từ RBE3023 thành RBE3021, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 4 RBE3023 Đồ án 1: Thiết kế và xây dựng Robot 1 2 RBE3021 Đồ án 1: Thiết kế và xây dựng Robot 1 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 09. `p8-temporal-2021-adjustment-08`

- Type: `temporal/comparison`; split: `holdout`
- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, RBE3024 được đổi thành mã nào cho học phần Đồ án 2: Thiết kế và xây dựng Robot 2?
- Expected answer: `RBE3022`
- Gold claim: Theo đính chính năm 2021, học phần Đồ án 2: Thiết kế và xây dựng Robot 2 đổi mã từ RBE3024 thành RBE3022, giữ nguyên 2 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 5 RBE3024 Đồ án 2: Thiết kế và xây dựng Robot 2 2 RBE3022 Đồ án 2: Thiết kế và xây dựng Robot 2 2
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 10. `p8-temporal-2021-adjustment-09`

- Type: `temporal/comparison`; split: `holdout`
- Question: Với học phần Thiết kế kiểu dáng công nghiệp, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: REB3016).
- Expected answer: `RBE3016`
- Gold claim: Theo đính chính năm 2021, học phần Thiết kế kiểu dáng công nghiệp đổi mã từ REB3016 thành RBE3016, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 6 REB3016 Thiết kế kiểu dáng công nghiệp 3 RBE3016 Thiết kế kiểu dáng công nghiệp 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 11. `p8-temporal-2021-adjustment-10`

- Type: `temporal/comparison`; split: `holdout`
- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Mạng truyền thông máy tính 1, khi cột hiện hành ghi ELT3212E?
- Expected answer: `ELT3046E`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 1 đổi mã từ ELT3212E thành ELT3046E, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 9 ELT3212E Mạng truyền thông máy tính 1 3 ELT3046E Mạng truyền thông máy tính 1 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 12. `p8-temporal-2021-adjustment-11`

- Type: `temporal/comparison`; split: `holdout`
- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Mạng truyền thông máy tính 2 (mã cũ ELT3214E) là gì?
- Expected answer: `ELT3062E`
- Gold claim: Theo đính chính năm 2021, học phần Mạng truyền thông máy tính 2 đổi mã từ ELT3214E thành ELT3062E, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 10 ELT3214E Mạng truyền thông máy tính 2 3 ELT3062E Mạng truyền thông máy tính 2 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 13. `p8-temporal-2021-adjustment-12`

- Type: `temporal/comparison`; split: `holdout`
- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Giới thiệu về Hàng không Vũ trụ: mã mới thay AER1002 là mã nào?
- Expected answer: `AER1001`
- Gold claim: Theo đính chính năm 2021, học phần Giới thiệu về Hàng không Vũ trụ đổi mã từ AER1002 thành AER1001, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 2, range `[2, 2]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p2_t1`
- Source row: 1 AER1002 Giới thiệu về Hàng không Vũ trụ 3 AER1001 Giới thiệu về Hàng không Vũ trụ 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 14. `p8-temporal-2021-adjustment-13`

- Type: `temporal/comparison`; split: `holdout`
- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, AER2002 được đổi thành mã nào cho học phần Cơ học chất lỏng?
- Expected answer: `EMA2008`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học chất lỏng đổi mã từ AER2002 thành EMA2008, giữ nguyên 4 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, range `[3, 3]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 2 AER2002 Cơ học chất lỏng 4 EMA2008 Cơ học chất lỏng 4
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 15. `p8-temporal-2021-adjustment-14`

- Type: `temporal/comparison`; split: `holdout`
- Question: Với học phần Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: AER2009).
- Expected answer: `AER2005`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ đổi mã từ AER2009 thành AER2005, giữ nguyên 4 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, range `[3, 3]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 3 AER2009 Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ 4 AER2005 Cơ học kỹ thuật cho Công nghệ Hàng không Vũ trụ 4
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 16. `p8-temporal-2021-adjustment-15`

- Type: `temporal/comparison`; split: `holdout`
- Question: Bản đính chính ngày 27 tháng 8 năm 2021 ghi mã nào ở cột điều chỉnh cho Hình hoạ kỹ thuật và CAD, khi cột hiện hành ghi AER2006?
- Expected answer: `EMA2032`
- Gold claim: Theo đính chính năm 2021, học phần Hình hoạ kỹ thuật và CAD đổi mã từ AER2006 thành EMA2032, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, range `[3, 3]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 4 AER2006 Hình hoạ kỹ thuật và CAD 3 EMA2032 Hình hoạ kỹ thuật và CAD 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 17. `p8-temporal-2021-adjustment-16`

- Type: `temporal/comparison`; split: `holdout`
- Question: Theo bảng đính chính ban hành ngày 27/08/2021, mã điều chỉnh của học phần Hệ thống đẩy (mã cũ AER3039) là gì?
- Expected answer: `AER3003`
- Gold claim: Theo đính chính năm 2021, học phần Hệ thống đẩy đổi mã từ AER3039 thành AER3003, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, range `[3, 3]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 5 AER3039 Hệ thống đẩy 3 AER3003 Hệ thống đẩy 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 18. `p8-temporal-2021-adjustment-17`

- Type: `temporal/comparison`; split: `holdout`
- Question: Đối chiếu cột khung hiện hành với cột thông tin điều chỉnh năm 2021 cho Thử nghiệm kết cấu thiết bị không gian: mã mới thay AER3040 là mã nào?
- Expected answer: `EMA3048`
- Gold claim: Theo đính chính năm 2021, học phần Thử nghiệm kết cấu thiết bị không gian đổi mã từ AER3040 thành EMA3048, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, range `[3, 3]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 6 AER3040 Thử nghiệm kết cấu thiết bị không gian 3 EMA3048 Thử nghiệm kết cấu thiết bị không gian 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 19. `p8-temporal-2021-adjustment-18`

- Type: `temporal/comparison`; split: `holdout`
- Question: Trong phụ lục đính chính chương trình đào tạo năm 2021, AER3037 được đổi thành mã nào cho học phần Cơ học quỹ đạo bay?
- Expected answer: `EMA3014`
- Gold claim: Theo đính chính năm 2021, học phần Cơ học quỹ đạo bay đổi mã từ AER3037 thành EMA3014, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, range `[3, 3]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 7 AER3037 Cơ học quỹ đạo bay 3 EMA3014 Cơ học quỹ đạo bay 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 20. `p8-temporal-2021-adjustment-19`

- Type: `temporal/comparison`; split: `holdout`
- Question: Với học phần Điều khiển điện thủy khí, hãy nêu mã trước và mã sau đính chính theo văn bản UET năm 2021 (trước: AER3041).
- Expected answer: `EMA3064`
- Gold claim: Theo đính chính năm 2021, học phần Điều khiển điện thủy khí đổi mã từ AER3041 thành EMA3064, giữ nguyên 3 tín chỉ.
- Evidence: `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` page 3, range `[3, 3]`, chunk `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79_p3_t1`
- Source row: 8 AER3041 Điều khiển điện thủy khí 3 EMA3064 Điều khiển điện thủy khí 3
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 21. `p8-fact-awards-effective-date`

- Type: `single-hop factual`; split: `test`
- Question: Theo Điều 2 của Quyết định khen thưởng ban hành năm 2023, quy định được áp dụng từ tháng/năm nào?
- Expected answer: `09/2023`
- Gold claim: 09/2023
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 1, range `[1, 1]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p1_s8_c1`
- Source row: được áp dụng từ tháng 09 năm 2023.
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 22. `p8-fact-valedictorian-average`

- Type: `single-hop factual`; split: `holdout`
- Question: Theo Điều 3, danh hiệu Thủ khoa ngành học dựa trên điểm trung bình toàn khóa cao nhất trong phạm vi nào?
- Expected answer: `Trong ngành học.`
- Gold claim: Trong ngành học.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 2, range `[2, 3]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`
- Source row: có điểm trung bình toàn khóa học cao nhất trong ngành học
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 23. `p8-fact-excellent-student-floor`

- Type: `single-hop factual`; split: `test`
- Question: Theo Điều 4, sinh viên đạt danh hiệu Sinh viên Xuất sắc không được có học phần nào dưới mức điểm nào?
- Expected answer: `C+.`
- Gold claim: C+.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 2, range `[2, 3]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`
- Source row: không có học phần nào có điểm dưới C+
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 24. `p8-fact-good-student-conduct`

- Type: `single-hop factual`; split: `holdout`
- Question: Theo Điều 5, kết quả rèn luyện tối thiểu để đạt danh hiệu Sinh viên Giỏi là mức nào?
- Expected answer: `Tốt trở lên.`
- Gold claim: Tốt trở lên.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 2, range `[2, 3]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`
- Source row: kết quả rèn luyện đạt loại Tốt trở lên
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 25. `p8-fact-collective-contribution-gpa`

- Type: `single-hop factual`; split: `test`
- Question: Theo Điều 6, điểm trung bình học tập tối thiểu để xét danh hiệu Sinh viên có đóng góp cho công tác tập thể là bao nhiêu?
- Expected answer: `Từ 3.0 trở lên.`
- Gold claim: Từ 3.0 trở lên.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 2, range `[2, 3]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`
- Source row: kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 26. `p8-fact-thesis-excellence-result`

- Type: `single-hop factual`; split: `holdout`
- Question: Theo Điều 7, Hội đồng chấm phải công nhận kết quả bảo vệ khóa luận/đồ án ở mức nào để đủ điều kiện danh hiệu Xuất sắc?
- Expected answer: `Xuất sắc.`
- Gold claim: Xuất sắc.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 2, range `[2, 3]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`
- Source row: được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 27. `p8-fact-collective-advanced-share`

- Type: `single-hop factual`; split: `holdout`
- Question: Theo Điều 8, tối thiểu bao nhiêu phần trăm sinh viên của tập thể phải đạt học tập và rèn luyện loại Khá trở lên?
- Expected answer: `70%.`
- Gold claim: 70%.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 2, range `[2, 3]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`
- Source row: Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 28. `p8-fact-collective-excellent-share`

- Type: `single-hop factual`; split: `holdout`
- Question: Theo Điều 9, tỷ lệ tối thiểu sinh viên đạt danh hiệu Sinh viên Giỏi trong tập thể Xuất sắc là bao nhiêu?
- Expected answer: `10%.`
- Gold claim: 10%.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 2, range `[2, 3]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`
- Source row: có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên Giỏi”
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 29. `p8-fact-entrance-award-amount`

- Type: `single-hop factual`; split: `test`
- Question: Theo Điều 10, phần thưởng cho sinh viên đạt tiêu chí thành tích tuyển sinh tương đương khoản học phí của thời gian nào?
- Expected answer: `Năm học đầu tiên trong khóa học.`
- Gold claim: Năm học đầu tiên trong khóa học.
- Evidence: `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` page 4, range `[4, 4]`, chunk `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p4_s18_c1`
- Source row: bằng học phí của năm học đầu tiên trong khóa học
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## 30. `p8-fact-exam-warning-deduction`

- Type: `single-hop factual`; split: `test`
- Question: Theo trích đoạn Quy chế đào tạo 2014, sinh viên bị khiển trách do nhìn bài người khác hoặc trao đổi bài trong giờ thi bị trừ bao nhiêu phần trăm điểm bài thi?
- Expected answer: `25%.`
- Gold claim: 25%.
- Evidence: `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1` page 1, range `[1, 1]`, chunk `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`
- Source row: bị trừ 25% số điểm đạt được của bài thi học phần đó
- Decision: [ ] Accept  [ ] Reject
- Reviewer note:

## Review disposition

- Reviewer identity:
- Reviewed combined benchmark JSONL SHA-256 (must match above):
- All 30 rows reviewed: [ ]
- Source exposure classification acknowledged: [ ]
- Overall decision: [ ] Accept for regression benchmark  [ ] Reject
- Signature/date:

Approval here does not claim fresh validation; provider egress logs remain outside the retained-file exposure scan.
