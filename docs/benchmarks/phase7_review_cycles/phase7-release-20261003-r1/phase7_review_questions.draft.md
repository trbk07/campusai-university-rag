# Hồ sơ duyệt từng câu Phase 7 — bản chờ owner review

Trạng thái: **CHỜ DUYỆT TỪNG RECORD**. Owner self-review được phép; chọn rõ vai trò `project_owner` và không gọi là independent. Đọc [hướng dẫn và quyết định chung](../../phase7_group_review.draft.md) trước khi ghi review.

Câu hỏi giữ nguyên; nhãn/gold dưới đây là đề xuất hiện có cần người review kiểm chứng.
Không có kết quả model, split hoặc quyết định nghiệm thu trong hồ sơ này.

## Danh mục tài liệu được index

Scope đề xuất cho negative là các tài liệu trong bảng này. PDF scan-only chưa index không nằm trong scope này.

| Mã | PDF | Năm | Trang | SHA-256 / doc ID |
|---|---|---|---:|---|
| D01 | [uet_masters_admission_2022.pdf](../../../../data/corpus/university/uet_masters_admission_2022.pdf) | 2022 | 18 | `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59` |
| D02 | [uet_training_regulation_2014.pdf](../../../../data/corpus/university/uet_training_regulation_2014.pdf) | 2014 | 1 | `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1` |
| D03 | [uet_mai_joint_curriculum_2022.pdf](../../../../data/corpus/university/uet_mai_joint_curriculum_2022.pdf) | 2022 | 3 | `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13` |
| D04 | [uet_student_rewards_2023.pdf](../../../../data/corpus/university/uet_student_rewards_2023.pdf) | 2023 | 4 | `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b` |
| D05 | [uet_electronics_course_map.pdf](../../../../data/corpus/university/uet_electronics_course_map.pdf) | 2023 | 1 | `b1fac148da7bd730e1ff68e6b591f6a4af05c2d87f417fef2e262a2276a79c7a` |
| D06 | [uet_cs_progression.pdf](../../../../data/corpus/university/uet_cs_progression.pdf) | 2019 | 1 | `c3220664c5737cd12e6fdaa1077d92ef7598ff3af25ca80e9f366b2f0021d0f8` |
| D07 | [uet_mechatronics_curriculum_2023.pdf](../../../../data/corpus/university/uet_mechatronics_curriculum_2023.pdf) | 2023 | 15 | `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850` |
| D08 | [uet_cs_curriculum_2019.pdf](../../../../data/corpus/university/uet_cs_curriculum_2019.pdf) | 2019 | 18 | `cadff7f7c9a0abd3b7178b2263b80115f78ae2e3a46006b112a32388774395bd` |
| D09 | [uet_electronics_program_2023.pdf](../../../../data/corpus/university/uet_electronics_program_2023.pdf) | 2023 | 13 | `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6` |
| D10 | [uet_program_adjustments_2021.pdf](../../../../data/corpus/university/uet_program_adjustments_2021.pdf) | 2021 | 3 | `fbeadda5107e0b43a293d245333e9565d531cd75a9f961df4b2ac516b5391d79` |

## 45 câu negative cần duyệt scope và hành vi

Scope `D01–D10` là **đề xuất**, không khẳng định tất cả câu đều negative trên corpus mở rộng.
Nếu có bằng chứng trả lời, ghi sửa nhãn/gold; nếu thiếu đối tượng/ngành/năm, ghi câu cần làm rõ.

| Câu | Câu hỏi nguyên văn | Hành vi hiện có | Scope đề xuất |
|---|---|---|---|
| [candidate-0001](#human-candidate-0001) | bao nhiêu tín thì được | `ask_clarification` | D01–D10 |
| [candidate-0002](#human-candidate-0002) | bn tc là đủ vậy | `ask_clarification` | D01–D10 |
| [candidate-0003](#human-candidate-0003) | mấy tín nhỉ | `ask_clarification` | D01–D10 |
| [candidate-0004](#human-candidate-0004) | credits cần bao nhiêu | `ask_clarification` | D01–D10 |
| [candidate-0005](#human-candidate-0005) | thế tổng là mấy | `ask_clarification` | D01–D10 |
| [candidate-0006](#human-candidate-0006) | ủa ít nhất bao nhiêu tín mới ok | `ask_clarification` | D01–D10 |
| [candidate-0007](#human-candidate-0007) | thế sinh viên năm 2 thì sao | `ask_clarification` | D01–D10 |
| [candidate-0008](#human-candidate-0008) | năm hai có khác ko | `ask_clarification` | D01–D10 |
| [candidate-0009](#human-candidate-0009) | còn sv năm 2 | `ask_clarification` | D01–D10 |
| [candidate-0010](#human-candidate-0010) | what about second-year students | `ask_clarification` | D01–D10 |
| [candidate-0011](#human-candidate-0011) | vậy n2 áp dụng kiểu gì | `ask_clarification` | D01–D10 |
| [candidate-0012](#human-candidate-0012) | em năm hai thì có được không | `ask_clarification` | D01–D10 |
| [candidate-0013](#human-candidate-0013) | mình có đủ điều kiện ko | `ask_clarification` | D01–D10 |
| [candidate-0014](#human-candidate-0014) | vậy em được chứ | `ask_clarification` | D01–D10 |
| [candidate-0015](#human-candidate-0015) | case t thì sao | `ask_clarification` | D01–D10 |
| [candidate-0016](#human-candidate-0016) | am I eligible vậy | `ask_clarification` | D01–D10 |
| [candidate-0017](#human-candidate-0017) | như của mình thì ok không bạn | `ask_clarification` | D01–D10 |
| [candidate-0018](#human-candidate-0018) | tính vậy em có bị gì không | `ask_clarification` | D01–D10 |
| [candidate-0019](#human-candidate-0019) | bằng này có dùng được không | `ask_clarification` | D01–D10 |
| [candidate-0020](#human-candidate-0020) | ielts này đủ chưa | `ask_clarification` | D01–D10 |
| [candidate-0021](#human-candidate-0021) | trường có quy định GPA tối thiểu để nhận học bổng khuyến khích học tập không | `abstain_no_evidence` | D01–D10 |
| [candidate-0022](#human-candidate-0022) | quy định nào nói một môn F ảnh hưởng học bổng khuyến khích học tập thế nào | `abstain_no_evidence` | D01–D10 |
| [candidate-0023](#human-candidate-0023) | cho em xin ngưỡng GPA khiến sinh viên bị cảnh báo học vụ | `abstain_no_evidence` | D01–D10 |
| [candidate-0024](#human-candidate-0024) | trường quy định thế nào về cảnh báo học vụ khi sinh viên không đạt hai học phần trong kỳ | `abstain_no_evidence` | D01–D10 |
| [candidate-0025](#human-candidate-0025) | khi học cải thiện thì điểm cũ được thay hay cả hai lần đều tính | `abstain_no_evidence` | D01–D10 |
| [candidate-0026](#human-candidate-0026) | bộ tài liệu mình gửi có quy định chuẩn tiếng Anh áp dụng chung toàn bộ khóa tuyển 2025 không | `abstain_no_evidence` | D01–D10 |
| [candidate-0027](#human-candidate-0027) | cho em ngưỡng điểm trung bình toàn khóa tối thiểu để được xét tốt nghiệp | `abstain_no_evidence` | D01–D10 |
| [candidate-0028](#human-candidate-0028) | xem file rồi cho mình biết GPA hiện tại của mình đi | `abstain_no_evidence` | D01–D10 |
| [candidate-0029](#human-candidate-0029) | pdf vừa up có nói điểm thi của t là mấy không | `abstain_no_evidence` | D01–D10 |
| [candidate-0030](#human-candidate-0030) | trong file này kết quả học tập cá nhân em thế nào | `abstain_no_evidence` | D01–D10 |
| [candidate-0031](#human-candidate-0031) | minimum GPA để get scholarship là bn | `abstain_no_evidence` | D01–D10 |
| [candidate-0032](#human-candidate-0032) | failed one subject thì scholarship eligibility còn không | `abstain_no_evidence` | D01–D10 |
| [candidate-0033](#human-candidate-0033) | two failed courses in a semester có academic warning không | `abstain_no_evidence` | D01–D10 |
| [candidate-0034](#human-candidate-0034) | minimum credits per semester là bao nhiêu | `abstain_no_evidence` | D01–D10 |
| [candidate-0035](#human-candidate-0035) | GPA 2.1 with one F có register 20 credits được không | `abstain_no_evidence` | D01–D10 |
| [candidate-0036](#human-candidate-0036) | gpa bn thì đc hb | `abstain_no_evidence` | D01–D10 |
| [candidate-0037](#human-candidate-0037) | 1 môn F thì còn xét hb kkht đc k | `abstain_no_evidence` | D01–D10 |
| [candidate-0038](#human-candidate-0038) | gpa bn là cbhv vậy | `abstain_no_evidence` | D01–D10 |
| [candidate-0039](#human-candidate-0039) | fail 2 môn/kì => cbhv k | `abstain_no_evidence` | D01–D10 |
| [candidate-0040](#human-candidate-0040) | 1 kỳ đăng kí ít nhất bn tín vậy | `abstain_no_evidence` | D01–D10 |
| [candidate-0041](#human-candidate-0041) | muốn lấy học bổng thì điểm phải cỡ nào vậy | `abstain_no_evidence` | D01–D10 |
| [candidate-0042](#human-candidate-0042) | điêm trung binh bao nhieu thi dc hoc bong | `abstain_no_evidence` | D01–D10 |
| [candidate-0043](#human-candidate-0043) | điểm tích lũy phải chạm mốc nào mới có tiền hỗ trợ học tập | `abstain_no_evidence` | D01–D10 |
| [candidate-0044](#human-candidate-0044) | rớt môn có bay học bổng ko | `abstain_no_evidence` | D01–D10 |
| [candidate-0045](#human-candidate-0045) | nếu điểm tổng em vẫn cao nhưng có một môn không đạt thì học bổng khuyến khích học tập tính sao | `abstain_no_evidence` | D01–D10 |

## Danh sách chưa rõ exposure

Cần ghi cycle/dataset/split, thời điểm, mục đích và hồ sơ liên quan; chưa biết không đồng nghĩa chưa dùng.
Các câu đã exposure được giữ nguyên trạng thái; nhóm chưa thể chọn held-out mới trước khi audit hoàn tất.

| Câu | ID nguồn | Connected group | Group đã exposure |
|---|---|---|---|
| [candidate-0001](#human-candidate-0001) | `q_061` | `family-ed077a2138b124064f32` | Chưa ghi nhận |
| [candidate-0002](#human-candidate-0002) | `q_062` | `family-ed077a2138b124064f32` | Chưa ghi nhận |
| [candidate-0003](#human-candidate-0003) | `q_063` | `family-ed077a2138b124064f32` | Chưa ghi nhận |
| [candidate-0004](#human-candidate-0004) | `q_064` | `family-ed077a2138b124064f32` | Chưa ghi nhận |
| [candidate-0005](#human-candidate-0005) | `q_065` | `family-ed077a2138b124064f32` | Chưa ghi nhận |
| [candidate-0006](#human-candidate-0006) | `q_066` | `family-ed077a2138b124064f32` | Chưa ghi nhận |
| [candidate-0013](#human-candidate-0013) | `q_073` | `family-632be74fa9b5f170acfa` | Chưa ghi nhận |
| [candidate-0014](#human-candidate-0014) | `q_074` | `family-632be74fa9b5f170acfa` | Chưa ghi nhận |
| [candidate-0015](#human-candidate-0015) | `q_075` | `family-632be74fa9b5f170acfa` | Chưa ghi nhận |
| [candidate-0016](#human-candidate-0016) | `q_076` | `family-632be74fa9b5f170acfa` | Chưa ghi nhận |
| [candidate-0017](#human-candidate-0017) | `q_077` | `family-632be74fa9b5f170acfa` | Chưa ghi nhận |
| [candidate-0018](#human-candidate-0018) | `q_078` | `family-632be74fa9b5f170acfa` | Chưa ghi nhận |
| [candidate-0019](#human-candidate-0019) | `q_079` | `family-541971345806babc8445` | Chưa ghi nhận |
| [candidate-0020](#human-candidate-0020) | `q_080` | `family-541971345806babc8445` | Chưa ghi nhận |
| [candidate-0022](#human-candidate-0022) | `q_012` | `family-6ce90bfd34eef8abe3c1` | Chưa ghi nhận |
| [candidate-0023](#human-candidate-0023) | `q_018` | `family-560d22226f1bff6d10dd` | Chưa ghi nhận |
| [candidate-0025](#human-candidate-0025) | `q_042` | `family-38cb79dd8cbdcdfe512e` | Chưa ghi nhận |
| [candidate-0026](#human-candidate-0026) | `q_054` | `family-87374531c38ea4c499c0` | Chưa ghi nhận |
| [candidate-0027](#human-candidate-0027) | `q_060` | `family-dde4b2fde6a133e7d6c8` | Chưa ghi nhận |
| [candidate-0028](#human-candidate-0028) | `q_463` | `family-39f7405a535adaca9454` | Chưa ghi nhận |
| [candidate-0029](#human-candidate-0029) | `q_464` | `family-39f7405a535adaca9454` | Chưa ghi nhận |
| [candidate-0030](#human-candidate-0030) | `q_465` | `family-39f7405a535adaca9454` | Chưa ghi nhận |
| [candidate-0032](#human-candidate-0032) | `q_010` | `family-6ce90bfd34eef8abe3c1` | Chưa ghi nhận |
| [candidate-0034](#human-candidate-0034) | `q_028` | `family-f9366ec92bf12d644ff6` | Chưa ghi nhận |
| [candidate-0035](#human-candidate-0035) | `q_033` | `family-697d6d25a802fee4da10` | Chưa ghi nhận |
| [candidate-0037](#human-candidate-0037) | `q_008` | `family-6ce90bfd34eef8abe3c1` | Chưa ghi nhận |
| [candidate-0038](#human-candidate-0038) | `q_015` | `family-560d22226f1bff6d10dd` | Chưa ghi nhận |
| [candidate-0040](#human-candidate-0040) | `q_026` | `family-f9366ec92bf12d644ff6` | Chưa ghi nhận |
| [candidate-0044](#human-candidate-0044) | `q_007` | `family-6ce90bfd34eef8abe3c1` | Chưa ghi nhận |
| [candidate-0045](#human-candidate-0045) | `q_009` | `family-6ce90bfd34eef8abe3c1` | Chưa ghi nhận |
| [candidate-0052](#human-candidate-0052) | `q_198` | `family-a51e320fc04da9904c3a` | Chưa ghi nhận |
| [candidate-0053](#human-candidate-0053) | `q_216` | `family-d9a5b0a2e76107f944e2` | Chưa ghi nhận |
| [candidate-0054](#human-candidate-0054) | `q_252` | `family-c7dfd744c4aa5d726479` | Chưa ghi nhận |
| [candidate-0055](#human-candidate-0055) | `q_324` | `family-732a1f9a5f89c0bf3f31` | Chưa ghi nhận |
| [candidate-0056](#human-candidate-0056) | `q_330` | `family-05d39038d7234dd8b4a1` | Chưa ghi nhận |
| [candidate-0057](#human-candidate-0057) | `q_342` | `family-0cf801fa92eca6d3c1a2` | Chưa ghi nhận |
| [candidate-0058](#human-candidate-0058) | `q_366` | `family-08433626f7a2bb69ddc7` | Chưa ghi nhận |
| [candidate-0059](#human-candidate-0059) | `q_384` | `family-e8e065950a239473fa46` | Chưa ghi nhận |
| [candidate-0064](#human-candidate-0064) | `q_217` | `family-64a1f59f724befd13a99` | Chưa ghi nhận |
| [candidate-0065](#human-candidate-0065) | `q_223` | `family-b3f576c04ba97aa7d0c5` | Chưa ghi nhận |
| [candidate-0066](#human-candidate-0066) | `q_236` | `family-859ef40ae8d4f5cd6cd3` | Chưa ghi nhận |
| [candidate-0067](#human-candidate-0067) | `q_271` | `family-fff2707a89c2f14e674a` | Chưa ghi nhận |
| [candidate-0068](#human-candidate-0068) | `q_290` | `family-4e01e5afc91cb5af0ee2` | Chưa ghi nhận |
| [candidate-0069](#human-candidate-0069) | `q_310` | `family-2e261a54e2fa689fd029` | Chưa ghi nhận |
| [candidate-0070](#human-candidate-0070) | `q_325` | `family-05d39038d7234dd8b4a1` | Chưa ghi nhận |
| [candidate-0071](#human-candidate-0071) | `q_343` | `family-d7e8dc3ef916422d3ffd` | Chưa ghi nhận |
| [candidate-0072](#human-candidate-0072) | `q_361` | `family-08433626f7a2bb69ddc7` | Chưa ghi nhận |
| [candidate-0073](#human-candidate-0073) | `q_367` | `family-97c1edbeab4dc64fbb89` | Chưa ghi nhận |
| [candidate-0075](#human-candidate-0075) | `q_409` | `family-64dd2f8b0f77663200e9` | Chưa ghi nhận |
| [candidate-0076](#human-candidate-0076) | `q_439` | `family-28d0a97d7a72131acd70` | Chưa ghi nhận |
| [candidate-0078](#human-candidate-0078) | `q_457` | `family-adf2da95ba447007abbe` | Chưa ghi nhận |
| [candidate-0095](#human-candidate-0095) | `q_410` | `family-64dd2f8b0f77663200e9` | Chưa ghi nhận |
| [candidate-0096](#human-candidate-0096) | `q_411` | `family-64dd2f8b0f77663200e9` | Chưa ghi nhận |
| [candidate-0097](#human-candidate-0097) | `q_412` | `family-64dd2f8b0f77663200e9` | Chưa ghi nhận |
| [candidate-0098](#human-candidate-0098) | `q_413` | `family-64dd2f8b0f77663200e9` | Chưa ghi nhận |
| [candidate-0118](#human-candidate-0118) | `q_204` | `family-deb7c4d2324acbd7c0c5` | Chưa ghi nhận |
| [candidate-0121](#human-candidate-0121) | `q_188` | `family-1793a321d0f86c98eead` | Chưa ghi nhận |
| [candidate-0122](#human-candidate-0122) | `q_206` | `family-7a548e1da444c68163d9` | Chưa ghi nhận |
| [candidate-0123](#human-candidate-0123) | `q_261` | `family-27a3cb822c498ca3b731` | Chưa ghi nhận |
| [candidate-0124](#human-candidate-0124) | `q_268` | `family-ddd31568f0514dc180d5` | Chưa ghi nhận |
| [candidate-0125](#human-candidate-0125) | `q_272` | `family-fff2707a89c2f14e674a` | Chưa ghi nhận |
| [candidate-0126](#human-candidate-0126) | `q_278` | `family-adfd7e93bd052189a754` | Chưa ghi nhận |
| [candidate-0145](#human-candidate-0145) | `q_192` | `family-1793a321d0f86c98eead` | Chưa ghi nhận |
| [candidate-0146](#human-candidate-0146) | `q_210` | `family-7a548e1da444c68163d9` | Chưa ghi nhận |
| [candidate-0147](#human-candidate-0147) | `q_222` | `family-64a1f59f724befd13a99` | Chưa ghi nhận |
| [candidate-0148](#human-candidate-0148) | `q_228` | `family-b3f576c04ba97aa7d0c5` | Chưa ghi nhận |
| [candidate-0156](#human-candidate-0156) | `phase6-test-001` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0157](#human-candidate-0157) | `phase6-test-002` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0158](#human-candidate-0158) | `phase6-test-006` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0159](#human-candidate-0159) | `phase6-test-010` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0160](#human-candidate-0160) | `phase6-test-018` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0161](#human-candidate-0161) | `phase6-test-022` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0162](#human-candidate-0162) | `phase6-test-026` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0163](#human-candidate-0163) | `phase6-test-030` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0164](#human-candidate-0164) | `phase6-test-033` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0165](#human-candidate-0165) | `phase6-test-034` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0166](#human-candidate-0166) | `phase6-test-036` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0167](#human-candidate-0167) | `phase6-test-037` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0168](#human-candidate-0168) | `phase6-test-038` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0169](#human-candidate-0169) | `phase6-test-039` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0170](#human-candidate-0170) | `phase6-test-043` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0171](#human-candidate-0171) | `phase6-test-045` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0172](#human-candidate-0172) | `phase6-test-047` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0173](#human-candidate-0173) | `phase6-test-051` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0174](#human-candidate-0174) | `phase6-test-053` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0175](#human-candidate-0175) | `phase6-test-057` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0176](#human-candidate-0176) | `phase6-test-058` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0177](#human-candidate-0177) | `phase6-test-074` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0178](#human-candidate-0178) | `phase6-test-075` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0179](#human-candidate-0179) | `phase6-test-076` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |
| [candidate-0180](#human-candidate-0180) | `phase6-test-079` | `family-f750befa59ae648ef4b1` | Chưa ghi nhận |

## Câu hỏi, context và bằng chứng

### human-candidate-0001

**Câu hỏi:** bao nhiêu tín thì được

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-ed077a2138b124064f32`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `204d277997c8ccf7a5f5324caa414028a2147defab49f7cdec7c3d36f77ff3f8`.

### human-candidate-0002

**Câu hỏi:** bn tc là đủ vậy

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-ed077a2138b124064f32`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `eebf907995f535fe73e94bd80fd1df434b560b99c00b8123b3a00e6466dfb5fb`.

### human-candidate-0003

**Câu hỏi:** mấy tín nhỉ

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-ed077a2138b124064f32`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d7f3a5674bcf994dbb967f2c2de5b2e15229369d17d280280d9cb43eb7f462d6`.

### human-candidate-0004

**Câu hỏi:** credits cần bao nhiêu

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-ed077a2138b124064f32`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `9ebd4c8864956f5271653420314f189e3e1c8b7a524e91e600480e53f1e208e9`.

### human-candidate-0005

**Câu hỏi:** thế tổng là mấy

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-ed077a2138b124064f32`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `87750d9f221310265da1ecc1aac36324062c1203372d91497559584528b1bc14`.

### human-candidate-0006

**Câu hỏi:** ủa ít nhất bao nhiêu tín mới ok

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-ed077a2138b124064f32`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f9a12a6345dae1953d8e9e62728bf335e9eb6518ddf9fd28482bee4038fbafa1`.

### human-candidate-0007

**Câu hỏi:** thế sinh viên năm 2 thì sao

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-e3f8db2a933aa0a2da10`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `060f0133ad5b5c08a13810e0cc2a8b864c85eec951d557602e294d12aec8868e`.

### human-candidate-0008

**Câu hỏi:** năm hai có khác ko

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-e3f8db2a933aa0a2da10`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `5f4171eef17b06b3cb1132aed186213a9c32d0f884dadf2703c4693c28ace1ba`.

### human-candidate-0009

**Câu hỏi:** còn sv năm 2

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-e3f8db2a933aa0a2da10`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `eaa672a60f6efcbb13156d04521ab483af9735cf653ba986aeaabc0893fa05d9`.

### human-candidate-0010

**Câu hỏi:** what about second-year students

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-e3f8db2a933aa0a2da10`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `10ff4bd2bbe1eae73e0d6ad808b5928519d40becf6f200e933e4bc59cd2b3464`.

### human-candidate-0011

**Câu hỏi:** vậy n2 áp dụng kiểu gì

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-e3f8db2a933aa0a2da10`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `6f26ef323ba113a35d8005260085e2c49a82b2a2a35b789c55dbd669183d82df`.

### human-candidate-0012

**Câu hỏi:** em năm hai thì có được không

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-e3f8db2a933aa0a2da10`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `111f537c2df1d22f3083b5ede6d6ac244db86b6b40ee06627ddd4d2db8285c08`.

### human-candidate-0013

**Câu hỏi:** mình có đủ điều kiện ko

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-632be74fa9b5f170acfa`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `310bf3d72a92ffb83e17eb39d9e3d047cc1df941c6e1f2ac1e54c1698dd21c14`.

### human-candidate-0014

**Câu hỏi:** vậy em được chứ

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-632be74fa9b5f170acfa`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `b527304c61c215945e8f7c7b3c050bead474829d8d2e546dd28031b2c38dd078`.

### human-candidate-0015

**Câu hỏi:** case t thì sao

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-632be74fa9b5f170acfa`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `1d648502af0571a35ff442a6e491da16aee9f61f6b879caafaf968e7bae4355c`.

### human-candidate-0016

**Câu hỏi:** am I eligible vậy

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-632be74fa9b5f170acfa`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `cebef6dd2440c13592e254cd1f5d0d7770430218251dee625ff31d672f40250c`.

### human-candidate-0017

**Câu hỏi:** như của mình thì ok không bạn

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-632be74fa9b5f170acfa`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `bee86906f954f778f5023ac642a8623e0b5004a7a4e802b4fd918bdd1fbecce5`.

### human-candidate-0018

**Câu hỏi:** tính vậy em có bị gì không

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-632be74fa9b5f170acfa`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `3b7ba47fd11d0b563aa56b0c4c79ed3811b5e26ee360f39c6e40f929271b7a90`.

### human-candidate-0019

**Câu hỏi:** bằng này có dùng được không

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-541971345806babc8445`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `13c0988a19154318cb2e190fab43060f5c8d63517a5a0cee36319cc65c5bf798`.

### human-candidate-0020

**Câu hỏi:** ielts này đủ chưa

Nhãn hiện có: negative; `hard`; hành vi `ask_clarification`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-541971345806babc8445`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `06c06698887d392b6db70d942650ea81d2b7dd25c3c19b7385026f641b80fd2c`.

### human-candidate-0021

**Câu hỏi:** trường có quy định GPA tối thiểu để nhận học bổng khuyến khích học tập không

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-5d51618526c84936feb0`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `316b0fe9fdc6b6b5b47ef7eddeb822ccd8e6149f4c540e089dc6be701e20f605`.

### human-candidate-0022

**Câu hỏi:** quy định nào nói một môn F ảnh hưởng học bổng khuyến khích học tập thế nào

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-6ce90bfd34eef8abe3c1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `7a0cb92dee1b40912ad8552116c0e3b2b0de3bb2729cf97fa08bc8ef50a9ebac`.

### human-candidate-0023

**Câu hỏi:** cho em xin ngưỡng GPA khiến sinh viên bị cảnh báo học vụ

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-560d22226f1bff6d10dd`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d704acd73c48d42d5496e29c964ecc8e5bbf4e45f5f3a64850f998a78c3aa2ce`.

### human-candidate-0024

**Câu hỏi:** trường quy định thế nào về cảnh báo học vụ khi sinh viên không đạt hai học phần trong kỳ

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-637dd41d7eee5ff3ab44`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `9e1c20c1607221ddaae1e039876c812a8bd4842145fa2472bedf511ede0c9b24`.

### human-candidate-0025

**Câu hỏi:** khi học cải thiện thì điểm cũ được thay hay cả hai lần đều tính

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-38cb79dd8cbdcdfe512e`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `3944bfa99b19ce8396f8535b492bbafcb165d775a6a7133cadeed363f1b73480`.

### human-candidate-0026

**Câu hỏi:** bộ tài liệu mình gửi có quy định chuẩn tiếng Anh áp dụng chung toàn bộ khóa tuyển 2025 không

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-87374531c38ea4c499c0`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a1085e61a1b05d1c0501a7d5c4f3dc20d9f50201673364e88f80efc1f19677c5`.

### human-candidate-0027

**Câu hỏi:** cho em ngưỡng điểm trung bình toàn khóa tối thiểu để được xét tốt nghiệp

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-dde4b2fde6a133e7d6c8`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e58a625a0efc2a634f7db649314c6de5552f7523eab9067303eb20bd0aa22547`.

### human-candidate-0028

**Câu hỏi:** xem file rồi cho mình biết GPA hiện tại của mình đi

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-39f7405a535adaca9454`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `c37285a80146fa60deefe9148b14e101349811d6f0c6c3761d98c447d9d5e5ed`.

### human-candidate-0029

**Câu hỏi:** pdf vừa up có nói điểm thi của t là mấy không

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-39f7405a535adaca9454`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `9b0934c2362168095f7fddbae0a6d914eedfe3fe2d99da76486d4ed4573be8ff`.

### human-candidate-0030

**Câu hỏi:** trong file này kết quả học tập cá nhân em thế nào

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-39f7405a535adaca9454`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `622523ca9b66715b4f52178bf3b80eaedd13ed52d2a1f6dd3fde393f0082028f`.

### human-candidate-0031

**Câu hỏi:** minimum GPA để get scholarship là bn

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-5d51618526c84936feb0`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ebdf178116d93a4172ea7218ec188707bd0df4e7f2e9e8366ce4bc424216a17c`.

### human-candidate-0032

**Câu hỏi:** failed one subject thì scholarship eligibility còn không

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-6ce90bfd34eef8abe3c1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `599aa30ef80bb0dbf8df1c0fd02365ff211108a2454ad5b56acf112371da17e7`.

### human-candidate-0033

**Câu hỏi:** two failed courses in a semester có academic warning không

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-637dd41d7eee5ff3ab44`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `c032c8c63c777c0258f338e067f789561edb97ad693a7be8604af3a773f84e1b`.

### human-candidate-0034

**Câu hỏi:** minimum credits per semester là bao nhiêu

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-f9366ec92bf12d644ff6`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `b628076f9fcd11eefe9797d0a5c29963d8bc4fd3d7dc790768a119d4fe76f5c5`.

### human-candidate-0035

**Câu hỏi:** GPA 2.1 with one F có register 20 credits được không

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-697d6d25a802fee4da10`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `9f4fb90beeb8430ab1e674346987b4e85f84f6fcb64408c56933201d3b7e6b3c`.

### human-candidate-0036

**Câu hỏi:** gpa bn thì đc hb

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-5d51618526c84936feb0`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2356dca98e0c764eafe0f3a6bdc8306c182a59eb44237a2a23cf8463f45adfbe`.

### human-candidate-0037

**Câu hỏi:** 1 môn F thì còn xét hb kkht đc k

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-6ce90bfd34eef8abe3c1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d279103635f555271d1f49cceea59951d5cad3d9cc0aa47efd9f1c44a138de1b`.

### human-candidate-0038

**Câu hỏi:** gpa bn là cbhv vậy

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-560d22226f1bff6d10dd`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `4a8204eb188b1d908be758adeaf7264a39b03b0edb69b71cc2018107e0f1452a`.

### human-candidate-0039

**Câu hỏi:** fail 2 môn/kì => cbhv k

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-637dd41d7eee5ff3ab44`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `52e4e63cfb80b90056781f6f82988df694280a60b3cf4b753ad267239b2329c9`.

### human-candidate-0040

**Câu hỏi:** 1 kỳ đăng kí ít nhất bn tín vậy

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-f9366ec92bf12d644ff6`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a5b68b94f141d86812301b903051cadd9caf3925c1f1b23641c4f26071fb3286`.

### human-candidate-0041

**Câu hỏi:** muốn lấy học bổng thì điểm phải cỡ nào vậy

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-5d51618526c84936feb0`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `4fd2b169bb5e60a38c969182465fb93c21df2b58344825078689030c849a25d4`.

### human-candidate-0042

**Câu hỏi:** điêm trung binh bao nhieu thi dc hoc bong

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-5d51618526c84936feb0`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `cdb053a772adb3cd3f16f0ed41c9e9765a3c08eede0a686987d2058dd4643914`.

### human-candidate-0043

**Câu hỏi:** điểm tích lũy phải chạm mốc nào mới có tiền hỗ trợ học tập

Nhãn hiện có: negative; `medium`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-5d51618526c84936feb0`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `68dc7f91056de03fb8a450f3f197e942e647fc7e62bc385cfb4db8fbf1bbc7a2`.

### human-candidate-0044

**Câu hỏi:** rớt môn có bay học bổng ko

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-6ce90bfd34eef8abe3c1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `7ee40144f2d3cb3ea2060808517f8d102447e555a0197bf547e1aba0c6d670a5`.

### human-candidate-0045

**Câu hỏi:** nếu điểm tổng em vẫn cao nhưng có một môn không đạt thì học bổng khuyến khích học tập tính sao

Nhãn hiện có: negative; `hard`; hành vi `abstain_no_evidence`.
Scope đề xuất cần duyệt: D01, D02, D03, D04, D05, D06, D07, D08, D09, D10. Filters: `{}`.
Nhóm: `family-6ce90bfd34eef8abe3c1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold hiện có:** không có. Reviewer cần kiểm tra phạm vi và lý do abstain/clarification; không suy no-evidence chỉ từ gold rỗng.

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `7cbd2630d096ec0ba720e19dfd484dc9ac3e0d3ccdfaa5ff9d99dc331e3812e9`.

### human-candidate-0046

**Câu hỏi:** thế hôm nào em phải đi phỏng vấn

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-a63be3d1ddd1777e114b`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em đang xem thông báo tuyển thạc sĩ theo file đang mở.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s32_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.2.  Thời gian phỏng vấn: ngày 17/09/2022. | Page: 5]

6.2.  Thời gian phỏng vấn: ngày 17/09/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d41fca0f1cc8af59d86a281e3a43b16654c2e4a903f871c6552df2fbc80f85ba`.

### human-candidate-0047

**Câu hỏi:** phải đóng mấy tiền vậy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7d281ffb83fa79952944`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em muốn đăng ký tuyển thạc sĩ theo file đang mở.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `b558b9aba490533b735b66fa39ecb8a48d46a353992e1882c9cadb3620bec94b`.

### human-candidate-0048

**Câu hỏi:** chuyển khoản được chứ hay phải tới nộp

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7fd4f74b898637c6ad7f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em đang chuẩn bị lệ phí dự tuyển thạc sĩ theo file đang mở.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2ce39522fa04a7af56746d5afdbb0ec11b191608e50520a4a85908bf156ea370`.

### human-candidate-0049

**Câu hỏi:** vậy đầu vào cần bậc mấy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-59a3b661cc05e4fbbb28`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em đang đọc điều kiện ngoại ngữ tuyển thạc sĩ.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D01, trang 1**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p1_s9_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.2. Điều kiện về văn bằng | Page: 1]

1.2. Điều kiện về văn bằng
-
Đã tốt nghiệp hoặc đã đủ điều kiện công nhận tốt nghiệp đại học (hoặc trình độ tương
đương trở lên) ngành phù hợp từ hạng tốt nghiệp loại Khá trở lên hoặc có công bố
khoa học (sách, giáo trình, bài báo đăng trên các tạp chí khoa học chuyên ngành hoặc
các báo cáo đăng trên kỷ yếu hội nghị, hội thảo khoa học chuyên ngành) liên quan
đến lĩnh vực học tập, nghiên cứu.
-
Có năng lực ngoại ngữ từ Bậc 3 trở lên theo Khung năng lực ngoại ngữ 6 bậc dùng
cho Việt Nam đáp ứng yêu cầu về ngoại ngữ của CTĐT (lưu ý các khóa đào tạo thạc
sĩ tuyển sinh từ năm 2022 có chuẩn đầu ra đối với trình độ ngoại ngữ đạt từ Bậc 4 trở
lên hoặc tương đương theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam).
-
Văn bằng đại học do cơ sở giáo dục nước ngoài cấp phải thực hiện thủ tục công nhận
theo quy định hiện hành.
-
Đối với chương trình đào tạo chuẩn quốc tế, văn bằng đại học phải là văn bằng
chương trình đào tạo chính quy.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `45df1bd9f23705315202aef2e0c39b0f70916e5ac95bbf86b8dfc92220b65542`.

### human-candidate-0050

**Câu hỏi:** còn lúc ra trường thì sao

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-01a645838218197e6353`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em hỏi chuẩn ngoại ngữ của khóa thạc sĩ nêu trong file.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D01, trang 1**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p1_s9_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.2. Điều kiện về văn bằng | Page: 1]

1.2. Điều kiện về văn bằng
-
Đã tốt nghiệp hoặc đã đủ điều kiện công nhận tốt nghiệp đại học (hoặc trình độ tương
đương trở lên) ngành phù hợp từ hạng tốt nghiệp loại Khá trở lên hoặc có công bố
khoa học (sách, giáo trình, bài báo đăng trên các tạp chí khoa học chuyên ngành hoặc
các báo cáo đăng trên kỷ yếu hội nghị, hội thảo khoa học chuyên ngành) liên quan
đến lĩnh vực học tập, nghiên cứu.
-
Có năng lực ngoại ngữ từ Bậc 3 trở lên theo Khung năng lực ngoại ngữ 6 bậc dùng
cho Việt Nam đáp ứng yêu cầu về ngoại ngữ của CTĐT (lưu ý các khóa đào tạo thạc
sĩ tuyển sinh từ năm 2022 có chuẩn đầu ra đối với trình độ ngoại ngữ đạt từ Bậc 4 trở
lên hoặc tương đương theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam).
-
Văn bằng đại học do cơ sở giáo dục nước ngoài cấp phải thực hiện thủ tục công nhận
theo quy định hiện hành.
-
Đối với chương trình đào tạo chuẩn quốc tế, văn bằng đại học phải là văn bằng
chương trình đào tạo chính quy.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ac8d409750e16f2c6a5ef6893580bbf25d0dc3ea665a1d3730e5720431ddde8e`.

### human-candidate-0051

**Câu hỏi:** chưa có giấy chứng minh thì nộp sau được không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-e8ab114bb11c67ef7330`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em hỏi điều kiện ngoại ngữ dự tuyển thạc sĩ theo file đang mở.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D01, trang 2**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p2_s10_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.3. Điều kiện về năng lực ngoại ngữ | Page: 2]

1.3. Điều kiện về năng lực ngoại ngữ
-
Có bằng tốt nghiệp đại học, thạc sĩ, tiến sĩ được đào tạo toàn thời gian ở nước ngoài
bằng ngoại ngữ phù hợp với yêu cầu của chương trình đào tạo, được cơ quan có
thẩm quyền công nhận văn bằng theo quy định hiện hành.
-
Bằng tốt nghiệp trình độ đại học trở lên ngành ngôn ngữ nước ngoài, ngành sư
phạm ngôn ngữ nước ngoài hoặc bằng tốt nghiệp trình độ đại học trở lên mà các học
phần thuộc khối kiến thức cơ sở và chuyên ngành được thực hiện bằng ngôn ngữ
nước ngoài;
-
Bằng tốt nghiệp trình độ đại học trở lên do các đơn vị đào tạo trong ĐHQGHN cấp
trong thời gian không quá 2 năm có chuẩn đầu ra về ngoại ngữ đáp ứng yêu cầu về
năng lực ngoại ngữ để dự tuyển CTĐT thạc sĩ và thí sinh đã có chứng chỉ ngoại ngữ
đáp ứng chuẩn đầu ra trước khi tốt nghiệp CTĐT trình độ đại học;
-
Một trong các chứng chỉ ngoại ngữ đạt trình độ tương đương Bậc 3 trở lên theo
Khung năng lực Ngoại ngữ 6 bậc dùng cho Việt Nam và được ĐHQGHN công
nhận (phụ lục 1 và phụ lục 2), còn hiệu lực tính đến ngày đăng ký dự tuyển.
Ghi chú: Thí sinh có thể được nợ minh chứng về năng lực ngoại ngữ và được bổ
sung trước thời điểm Nhà trường ra quyết định trúng tuyển. Thời gian dự kiến tháng
11/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `28f3c5c48fd68dcafc4be8e974271c56d3369a5d874039ed12a0810372d6fa39`.

### human-candidate-0052

**Câu hỏi:** còn phần rèn luyện thì cần tới loại nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-a51e320fc04da9904c3a`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em đang xem điều kiện danh hiệu Sinh viên Giỏi trong quy định.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `8950e90b7427d8ef5ed9c40500476d62d4d73d897eea938940460e311ca7f07e`.

### human-candidate-0053

**Câu hỏi:** được nhận những gì thế

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-d9a5b0a2e76107f944e2`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em hỏi về danh hiệu Sinh viên Xuất sắc trong quy định khen thưởng.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `86fd7ae3fc7bc88c9f20d5325d4e5d450d5b90cb5e1f7ac8963d26821c90d57d`.

### human-candidate-0054

**Câu hỏi:** thưởng học phí của năm nào vậy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-c7dfd744c4aa5d726479`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Em đang xem diện khen sinh viên trúng tuyển xuất sắc trong quy định.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D04, trang 4**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p4_s18_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH TRONG KỲ THI TUYỂN SINH ĐẠI HỌC | Page: 4]

THÀNH TÍCH TRONG KỲ THI TUYỂN SINH ĐẠI HỌC
Điều 10: Các sinh viên đạt kết quả xuất sắc trong kỳ thi tuyển sinh đại học vào Trường
Đại học Công nghệ sẽ được tặng Giấy chứng nhận và phần thưởng bằng học phí của năm
học đầu tiên trong khóa học, cụ thể:
+ Là thủ khoa kỳ thi Tuyển sinh: Có điểm thi (chưa cộng điểm ưu tiên) cao nhất (theo
từng phương thức xét tuyển) trong số các thí sinh dự thi vào trường trong kỳ tuyển sinh năm đó;
+ Được tuyển thẳng vào trường trong kỳ thi tuyển sinh và đồng thời đạt giải chính
thức trong kỳ thi cấp Quốc tế trong năm đó;
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `0dee2e8aeee3dba1ba68ef20ec47741e1ed2b372dd5bec9cd8bf69b4cd2eb5d8`.

### human-candidate-0055

**Câu hỏi:** tiếng Anh lúc ra trường cần bậc nào

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D09. Filters: `{}`.
Nhóm: `family-732a1f9a5f89c0bf3f31`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Mình đang xem khung chương trình Công nghệ kỹ thuật điện tử viễn thông.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D09, trang 5**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p5_s22_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: 2. Chuẩn đầu ra về kỹ năng | Page: 5]

2. Chuẩn đầu ra về kỹ năng
PLO 5: Phát hiện, mô tả, phản biện vấn đề và đề xuất giải pháp về lĩnh vực chuyên
môn bằng cách áp dụng các kiến thức khoa học, CNTT, các công cụ và công nghệ hiện đại.
PLO 6: Thiết kế, thực thi/thí nghiệm giải pháp, phân tích dữ liệu và kết quả, đánh
giá kỹ thuật để rút ra kết luận.
PLO 7: Giao tiếp hiệu quả với nhiều đối tượng; lập kế hoạch, điều phối, quản lý
nhóm làm việc hiệu quả.
PLO 8: Tư duy logic, biện chứng để giải quyết vấn đề thực tế hiệu quả và sáng tạo.
PLO 9: Vận dụng được kiến thức cơ bản về tiếng Anh tương đương trình độ 3/6
Khung năng lực ngoại ngữ Việt Nam
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `4914b996fde0846f56caa24149f1dd1ee1bc83f7394508ef37ba22b24ae76cf7`.

### human-candidate-0056

**Câu hỏi:** cần học gì trước và mấy tín vậy

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D09. Filters: `{}`.
Nhóm: `family-05d39038d7234dd8b4a1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Mình hỏi môn Cấu trúc dữ liệu và giải thuật thuộc khung điện tử viễn thông.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D09, trang 8**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p8_s56_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: INT2210 | Page: 8]

INT2210
Cấu trúc dữ liệu và giải thuật
Data structure and algorithms
4
45
15
````

</details>

**Gold: D09, trang 8**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p8_s57_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: INT1008 | Page: 8]

INT1008
21
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `3045feef1e7f44530f4ca439c775e740b23f5b4bd9a5ee6aac3f3d4d96ed161b`.

### human-candidate-0057

**Câu hỏi:** môn này mấy tín nhỉ

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D09. Filters: `{}`.
Nhóm: `family-0cf801fa92eca6d3c1a2`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Mình hỏi môn Thực tập điện tử số ở chương trình điện tử viễn thông.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D09, trang 9**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p9_s68_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: ELT3103 | Page: 9]

ELT3103
Thực tập điện tử số
Digital Electronics Lab
2
30
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `7d935c7f08027c5fb4e8776fc9503d02d897b450e50f731232e623efcef51f54`.

### human-candidate-0058

**Câu hỏi:** cần học trước những môn nào nhỉ

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-08433626f7a2bb69ddc7`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Mình đang xem môn Matlab và ứng dụng của cơ điện tử trong PDF đang mở.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s45_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2006E | Page: 4]

EMA2006E
Matlab và ứng dụng *
Matlab and Applications
3
30
15
````

</details>

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s46_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: INT1006 | Page: 4]

INT1006
````

</details>

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s47_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1093 | Page: 4]

MAT1093
````

</details>

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s48_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1042 | Page: 4]

MAT1042
24.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f2c6e07f945c93f1123d80f752c23f2a96637d390a20962e6e4e47227c79ee94`.

### human-candidate-0059

**Câu hỏi:** mấy tín vậy bạn

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-e8e065950a239473fa46`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Mình đang hỏi môn Cơ sở thiết kế máy trong khung cơ điện tử trong file.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s57_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2033 | Page: 4]

EMA2033
Cơ sở thiết kế máy
Fundamental of Machine
Design
4
40
20
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f5822a20e40f63363660c02380ffc42f4b5b7c81c102c57cc8747acdbc7064f9`.

### human-candidate-0060

**Câu hỏi:** kỳ 5 thì bên nào phụ trách

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-41a638d5bc72a8f38510`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Context/selection cần review cùng câu hỏi:**

```json
{
  "context": [
    {
      "content": "Mình đang xem chương trình liên kết chương trình liên kết.",
      "role": "user"
    }
  ],
  "selected_text": null
}
```

**Gold: D03, trang 2**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p2_t3`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 2]
Table headers: 3 | Technology of Structure Materials | 3 | VNU-UET

{"headers": ["3", "Technology of Structure Materials", "3", "VNU-UET"], "rows": [["4", "Thermodynamic Engineering", "3", "VNU-UET"], ["5", "Physical Education", "1", "VNU-UET"], ["6", "System Dynamic & Vibration", "3", "VNU-UET"], ["7", "Aerodynamics 1", "4", "VNU-UET"], ["8", "Applied Ecology", "2", "VNU-UET"], ["9", "Measurement Science, Standardization and Certification", "3", "VNU-UET"], ["", "Credits per semester", "24", ""], ["", "Semester 5", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Economics", "3", "MAI"], ["4", "Informational Support of Product Life Cycle", "3", "MAI"], ["5.1", "Aerodynamics 2", "4", "MAI"], ["5.2", "Aerohydrodynamics", "4", "MAI"], ["6.1", "Structural Mechanics and Aircraft Durability", "5", "MAI"], ["6.2", "Structural Mechanics &Aerostructure and Systems\nDurability", "5", "MAI"], ["7.1", "Numeral Methods", "4", "MAI"], ["7.2", "Numeral Mathematics", "4", "MAI"], ["8", "Mathematical Model Methods", "3", "MAI"], ["9", "Machine Elements & Principles of Design", "4", "MAI"], ["", "Credits per semester", "30", ""], ["Semester 6", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Informational Support of Product Life Cycle", "3", "MAI"], ["4", "Dynamics & Flightpath Control Laboratory Workshop", "2", "MAI"], ["5.1", "Flight Dynamics", "3", "MAI"], ["5.2", "Airplane Performance Computation", "3", "MAI"], ["6", "Health & Wellness Fundamentals", "2", "MAI"], ["7", "Industrial Economics & Organization", "3", "MAI"], ["8", "Aircraft Manufacturing Technology", "2", "MAI"], ["9", "Details & Modules Construction", "3", "MAI"], ["10", "Aircraft Construction", "4", "MAI"], ["11", "Engineering and Manufacturing Practice II", "6", "MAI"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `5d9ef2c2f0a1be182fdb5c7097eefefdcb232d3735981f07870ba390c8cf964a`.

### human-candidate-0061

**Câu hỏi:** cao học trong thông báo cho nợ minh chứng ngoại ngữ không, nếu được thì hạn trước mốc nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-e8ab114bb11c67ef7330`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 2**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p2_s10_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.3. Điều kiện về năng lực ngoại ngữ | Page: 2]

1.3. Điều kiện về năng lực ngoại ngữ
-
Có bằng tốt nghiệp đại học, thạc sĩ, tiến sĩ được đào tạo toàn thời gian ở nước ngoài
bằng ngoại ngữ phù hợp với yêu cầu của chương trình đào tạo, được cơ quan có
thẩm quyền công nhận văn bằng theo quy định hiện hành.
-
Bằng tốt nghiệp trình độ đại học trở lên ngành ngôn ngữ nước ngoài, ngành sư
phạm ngôn ngữ nước ngoài hoặc bằng tốt nghiệp trình độ đại học trở lên mà các học
phần thuộc khối kiến thức cơ sở và chuyên ngành được thực hiện bằng ngôn ngữ
nước ngoài;
-
Bằng tốt nghiệp trình độ đại học trở lên do các đơn vị đào tạo trong ĐHQGHN cấp
trong thời gian không quá 2 năm có chuẩn đầu ra về ngoại ngữ đáp ứng yêu cầu về
năng lực ngoại ngữ để dự tuyển CTĐT thạc sĩ và thí sinh đã có chứng chỉ ngoại ngữ
đáp ứng chuẩn đầu ra trước khi tốt nghiệp CTĐT trình độ đại học;
-
Một trong các chứng chỉ ngoại ngữ đạt trình độ tương đương Bậc 3 trở lên theo
Khung năng lực Ngoại ngữ 6 bậc dùng cho Việt Nam và được ĐHQGHN công
nhận (phụ lục 1 và phụ lục 2), còn hiệu lực tính đến ngày đăng ký dự tuyển.
Ghi chú: Thí sinh có thể được nợ minh chứng về năng lực ngoại ngữ và được bổ
sung trước thời điểm Nhà trường ra quyết định trúng tuyển. Thời gian dự kiến tháng
11/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a8947dfdbc7fc0b5f6e1e6c84736cf74156ce1a55e1cfbf4fd7b336ad81c38a6`.

### human-candidate-0062

**Câu hỏi:** có cả giải nghiên cứu với bài báo thì xét tuyển thẳng thạc sĩ cộng tối đa được bao nhiêu

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7bd487e2a33f91e366dc`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s15_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.1. XÉT TUYỂN THẲNG > 2.1.2. Điểm thưởng thành tích nghiên cứu khoa học | Page: 3]

2.1.2. Điểm thưởng thành tích nghiên cứu khoa học
-  Đối với công trình nghiên cứu khoa học sinh viên:
+ Đạt giải thưởng cấp ĐHQGHN hoặc cấp Bộ Giáo dục và Đào tạo: giải nhất: 0.2
điểm, giải nhì 0.15 điểm, giải ba 0.1 điểm, giải khuyến khích 0.07 điểm.
+ Đạt giải thưởng cấp trường hoặc cấp khoa trực thuộc: giải nhất 0.1 điểm, giải nhì
````

</details>

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ac153265c985270835c108dd366ff382986a6bf0a1acedd4f2a97728376d3a73`.

### human-candidate-0063

**Câu hỏi:** tuyển thẳng cao học trong thông báo xét ngày nào rồi bao giờ biết kết quả

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-fa8ab7404ea45210a57a`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s20_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022 | Page: 4]

2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022
````

</details>

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s21_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022 | Page: 4]

2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `3fb2142d4255451fb4acca81145fbf2c2891e2fd78399a967d463b67eea9df8a`.

### human-candidate-0064

**Câu hỏi:** quy định xét sinh viên đóng góp tập thể cần điểm bao nhiêu và có phải làm cán bộ lớp không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-64a1f59f724befd13a99`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

t nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 7: Danh hiệu “Sinh viên bảo vệ khóa luận/đồ án tốt nghiệp Xuất sắc” được trao
cho các sinh viên tốt nghiệp đúng hoặc trước thời hạn đào tạo chuẩn, có kết quả học tập và
rèn luyện toàn khóa học đạt từ loại Khá trở lên và có kết quả bảo vệ khóa luận/đồ án tốt
nghiệp được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc.

Sinh viên đạt
danh hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 8: Danh hiệu “Tập thể Tiên tiến” được trao cho các tập thể đạt các tiêu chuẩn
sau: Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên; Không có sinh viên
xếp loại học tập và rèn luyện loại Yếu trở xuống (không tính các trường hợp sinh viên đã tự
ý nghỉ học/bỏ học hoặc thuộc diện không tương tác); Tập thể đoàn kết, giúp đỡ lẫn nhau
trong học tập, rèn luyện, tổ chức nhiều hoạt động thi đua và tích cực hưởng ứng các phong
trào thi đua trong Nhà trường.

Tập thể đạt danh hiệu “Tập thể Tiên tiến” sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 9: Danh hiệu “Tập thể Xuất sắc” được trao cho các tập thể đạt các tiêu chuẩn
của danh hiệu “Tập thể Tiên tiến” và có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên
Giỏi” và có sinh viên đạt danh hiệu “Sinh viên Xuất sắc”.

Tập thể đạt Danh hiệu “Tập thể
Xuất sắc” sẽ được tặng Giấy khen của Hiệu trưởng Nhà trường và tiền thưởng theo quy định
hiện hành của Đại học Quốc gia Hà Nội và của Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `1e39b86f77e92fb377a63747af1a0971408072b7b1cdc103e70f9016c73a278b`.

### human-candidate-0065

**Câu hỏi:** muốn được thưởng khóa luận xuất sắc theo quy định thì ngoài điểm bảo vệ cần điều kiện gì

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-b3f576c04ba97aa7d0c5`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

t nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 7: Danh hiệu “Sinh viên bảo vệ khóa luận/đồ án tốt nghiệp Xuất sắc” được trao
cho các sinh viên tốt nghiệp đúng hoặc trước thời hạn đào tạo chuẩn, có kết quả học tập và
rèn luyện toàn khóa học đạt từ loại Khá trở lên và có kết quả bảo vệ khóa luận/đồ án tốt
nghiệp được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc.

Sinh viên đạt
danh hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 8: Danh hiệu “Tập thể Tiên tiến” được trao cho các tập thể đạt các tiêu chuẩn
sau: Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên; Không có sinh viên
xếp loại học tập và rèn luyện loại Yếu trở xuống (không tính các trường hợp sinh viên đã tự
ý nghỉ học/bỏ học hoặc thuộc diện không tương tác); Tập thể đoàn kết, giúp đỡ lẫn nhau
trong học tập, rèn luyện, tổ chức nhiều hoạt động thi đua và tích cực hưởng ứng các phong
trào thi đua trong Nhà trường.

Tập thể đạt danh hiệu “Tập thể Tiên tiến” sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 9: Danh hiệu “Tập thể Xuất sắc” được trao cho các tập thể đạt các tiêu chuẩn
của danh hiệu “Tập thể Tiên tiến” và có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên
Giỏi” và có sinh viên đạt danh hiệu “Sinh viên Xuất sắc”.

Tập thể đạt Danh hiệu “Tập thể
Xuất sắc” sẽ được tặng Giấy khen của Hiệu trưởng Nhà trường và tiền thưởng theo quy định
hiện hành của Đại học Quốc gia Hà Nội và của Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `72a6399174e2434bb1964ee108c40b66a264b1606d1ecf0070582b8d07b58680`.

### human-candidate-0066

**Câu hỏi:** lớp xuất sắc phải vừa đạt Tiên tiến vừa có bao nhiêu sinh viên Giỏi và Xuất sắc

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-859ef40ae8d4f5cd6cd3`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

t nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 7: Danh hiệu “Sinh viên bảo vệ khóa luận/đồ án tốt nghiệp Xuất sắc” được trao
cho các sinh viên tốt nghiệp đúng hoặc trước thời hạn đào tạo chuẩn, có kết quả học tập và
rèn luyện toàn khóa học đạt từ loại Khá trở lên và có kết quả bảo vệ khóa luận/đồ án tốt
nghiệp được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc.

Sinh viên đạt
danh hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 8: Danh hiệu “Tập thể Tiên tiến” được trao cho các tập thể đạt các tiêu chuẩn
sau: Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên; Không có sinh viên
xếp loại học tập và rèn luyện loại Yếu trở xuống (không tính các trường hợp sinh viên đã tự
ý nghỉ học/bỏ học hoặc thuộc diện không tương tác); Tập thể đoàn kết, giúp đỡ lẫn nhau
trong học tập, rèn luyện, tổ chức nhiều hoạt động thi đua và tích cực hưởng ứng các phong
trào thi đua trong Nhà trường.

Tập thể đạt danh hiệu “Tập thể Tiên tiến” sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 9: Danh hiệu “Tập thể Xuất sắc” được trao cho các tập thể đạt các tiêu chuẩn
của danh hiệu “Tập thể Tiên tiến” và có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên
Giỏi” và có sinh viên đạt danh hiệu “Sinh viên Xuất sắc”.

Tập thể đạt Danh hiệu “Tập thể
Xuất sắc” sẽ được tặng Giấy khen của Hiệu trưởng Nhà trường và tiền thưởng theo quy định
hiện hành của Đại học Quốc gia Hà Nội và của Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `c5fd1121ae4fd1a56c7f66df004da5cf872b998c21e6531db167f2d6c39c1240`.

### human-candidate-0067

**Câu hỏi:** đình chỉ thi theo quy chế thì điểm bài là mấy và có phải ra khỏi phòng ngay không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D02. Filters: `{}`.
Nhóm: `family-fff2707a89c2f14e674a`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D02, trang 1**, `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: Điều 32. Nghĩa vụ của sinh viên | Page: 1]

Điều 32. Nghĩa vụ của sinh viên
4. Sinh viên có trách nhiệm thực hiện đúng các quy định về kỷ luật phòng thi,
nếu vi phạm sẽ bị kỷ luật ở các mức sau:
a) Khiển trách: áp dụng đối với sinh viên phạm lỗi 1 lần nhìn bài của
người khác, trao đổi bài, thảo luận bài trong giờ thi. Sinh viên bị khiển trách
trong khi thi học phần nào bị trừ 25% số điểm đạt được của bài thi học phần đó;
b) Cảnh cáo: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị khiển trách 1 lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Trao đổi bài làm, giấy nháp với người khác;
- Chép bài của người khác. Những bài thi đã có kết luận là giống nhau thì
xử lý như nhau trừ trường hợp nếu người bị xử lý có đủ bằng chứng chứng tỏ
mình thực sự bị quay cóp thì thủ trưởng đơn vị đào tạo có thể xem xét giảm từ
mức kỷ luật cảnh cáo xuống mức khiển trách.
Sinh viên bị cảnh cáo trong khi thi học phần nào sẽ bị trừ 50% số điểm
đạt được của bài thi học phần đó.
c) Đình chỉ thi: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị cảnh cáo một lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Sau khi đã bóc đề thi bị phát hiện mang theo những vật dụng không
được phép;
- Đưa đề thi ra ngoài hoặc nhận bài giải từ ngoài vào phòng thi.
Sinh viên bị kỷ luật đình chỉ thi sẽ bị điểm không (0) bài thi học phần đó
và phải ra khỏi phòng thi ngay sau khi có quyết định đình chỉ thi.
Các hình thức kỷ luật nói trên do cán bộ coi thi lập biên bản, thu tang vật
và ghi rõ hình thức kỷ luật.
d) Sinh viên thi hộ hoặc nhờ người thi hộ bị kỷ luật ở mức đình chỉ học tập 1
năm đối với trường hợp vi phạm lần thứ nhất và buộc thôi học đối với trường hợp
vi phạm lần thứ hai.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `33bcccf70efa0b26c509f1ccdaca8ade729b49ac1778a806dce5c20505e27fa1`.

### human-candidate-0068

**Câu hỏi:** theo quy chế khiển trách xong tái phạm thì sao, cảnh cáo xong vẫn tái phạm thì sao

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D02. Filters: `{}`.
Nhóm: `family-4e01e5afc91cb5af0ee2`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D02, trang 1**, `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: Điều 32. Nghĩa vụ của sinh viên | Page: 1]

Điều 32. Nghĩa vụ của sinh viên
4. Sinh viên có trách nhiệm thực hiện đúng các quy định về kỷ luật phòng thi,
nếu vi phạm sẽ bị kỷ luật ở các mức sau:
a) Khiển trách: áp dụng đối với sinh viên phạm lỗi 1 lần nhìn bài của
người khác, trao đổi bài, thảo luận bài trong giờ thi. Sinh viên bị khiển trách
trong khi thi học phần nào bị trừ 25% số điểm đạt được của bài thi học phần đó;
b) Cảnh cáo: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị khiển trách 1 lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Trao đổi bài làm, giấy nháp với người khác;
- Chép bài của người khác. Những bài thi đã có kết luận là giống nhau thì
xử lý như nhau trừ trường hợp nếu người bị xử lý có đủ bằng chứng chứng tỏ
mình thực sự bị quay cóp thì thủ trưởng đơn vị đào tạo có thể xem xét giảm từ
mức kỷ luật cảnh cáo xuống mức khiển trách.
Sinh viên bị cảnh cáo trong khi thi học phần nào sẽ bị trừ 50% số điểm
đạt được của bài thi học phần đó.
c) Đình chỉ thi: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị cảnh cáo một lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Sau khi đã bóc đề thi bị phát hiện mang theo những vật dụng không
được phép;
- Đưa đề thi ra ngoài hoặc nhận bài giải từ ngoài vào phòng thi.
Sinh viên bị kỷ luật đình chỉ thi sẽ bị điểm không (0) bài thi học phần đó
và phải ra khỏi phòng thi ngay sau khi có quyết định đình chỉ thi.
Các hình thức kỷ luật nói trên do cán bộ coi thi lập biên bản, thu tang vật
và ghi rõ hình thức kỷ luật.
d) Sinh viên thi hộ hoặc nhờ người thi hộ bị kỷ luật ở mức đình chỉ học tập 1
năm đối với trường hợp vi phạm lần thứ nhất và buộc thôi học đối với trường hợp
vi phạm lần thứ hai.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `9051f16c2a1731208d69cf9218a8000697a4e0b44566b6f0e31e8c97c440d327`.

### human-candidate-0069

**Câu hỏi:** khung ĐTVT tổng bao nhiêu tín, đã tính thể chất quốc phòng chưa

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D09. Filters: `{}`.
Nhóm: `family-2e261a54e2fa689fd029`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D09, trang 7**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p7_s25_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: 1. Tóm tắt yêu cầu chương trình đào tạo | Page: 7]

1. Tóm tắt yêu cầu chương trình đào tạo
Tổng số tín chỉ của chương trình đào tạo (Chưa tính các học phần Giáo dục thể chất,
Giáo dục quốc phòng-an ninh, Kỹ năng bổ trợ):
````

</details>

**Gold: D09, trang 7**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p7_s26_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: 135 tín chỉ | Page: 7]

135 tín chỉ
- Khối kiến thức chung:
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ee638533f6c1d4443ca0038e724a31c2192bf9d247c715f2ede9c000f103f715`.

### human-candidate-0070

**Câu hỏi:** cấu trúc dữ liệu trong khung ĐTVT bao nhiêu tín và học trước môn gì

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D09. Filters: `{}`.
Nhóm: `family-05d39038d7234dd8b4a1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D09, trang 8**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p8_s56_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: INT2210 | Page: 8]

INT2210
Cấu trúc dữ liệu và giải thuật
Data structure and algorithms
4
45
15
````

</details>

**Gold: D09, trang 8**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p8_s57_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: INT1008 | Page: 8]

INT1008
21
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `68e10412b71cdb024c9e7eddd910188d40b93bd5c0b82810fa00aab8e31f7e0d`.

### human-candidate-0071

**Câu hỏi:** xử lý tín hiệu số ĐTVT khung mấy tín, cần qua môn nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D09. Filters: `{}`.
Nhóm: `family-d7e8dc3ef916422d3ffd`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D09, trang 9**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p9_s70_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: ELT3144 | Page: 9]

ELT3144
Xử lý tín hiệu số
Digital Signal Processing
4
45
15
````

</details>

**Gold: D09, trang 9**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p9_s71_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: ELT2035 | Page: 9]

ELT2035
30
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `de089e7282a700bb0f848867e6661c3aa4c6e630589387204e067ba937fc3880`.

### human-candidate-0072

**Câu hỏi:** Matlab và ứng dụng khung cơ điện tử trong file có mấy tín và cần qua những môn nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-08433626f7a2bb69ddc7`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s45_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2006E | Page: 4]

EMA2006E
Matlab và ứng dụng *
Matlab and Applications
3
30
15
````

</details>

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s46_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: INT1006 | Page: 4]

INT1006
````

</details>

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s47_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1093 | Page: 4]

MAT1093
````

</details>

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s48_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1042 | Page: 4]

MAT1042
24.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `6d370a963545799f97329fec1dca4b9495f8791a5b1551ae322de15a0fd094a5`.

### human-candidate-0073

**Câu hỏi:** Giải tích 2 cơ điện tử trong file bao nhiêu tín, học trước gì

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-97c1edbeab4dc64fbb89`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 3**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p3_s29_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1042 | Page: 3]

MAT1042
Giải tích 2
Analytics 2
4
30
30
````

</details>

**Gold: D07, trang 3**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p3_s30_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1041 | Page: 3]

MAT1041
17.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `1656a259e36e597c36aaa85ca32e684955c59b769e3f9a862bc9d03ea15b10bc`.

### human-candidate-0074

**Câu hỏi:** Final State Attestation chương trình liên kết có mấy tín và kỳ nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-de9ca3c468709acb7aee`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 3**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 3]
Table headers: Credits per semester | 32

{"headers": ["", "Credits per semester", "32", ""], "rows": [["Semester7", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Management Fundamental", "2", "MAI"], ["2", "Social Science", "2", "MAI"], ["3.1", "Engineering Task Simulation", "2", "MAI"], ["3.2", "Engineering Problem Solution with the Electronic\nComputing Machine", "2", "MAI"], ["4", "Electrical Engineering & Electronics", "3", "MAI"], ["5", "Aircraft Manufacturing Technology", "4", "MAI"], ["6", "Details & Modules Construction", "1", "MAI"], ["7", "Aviation Equipment Certification", "3", "MAI"], ["8", "Glider Units Design (Airframe Design)", "5", "MAI"], ["9.1", "Mechanical Equipment Systems", "4", "MAI"], ["9.2", "Life-Support & Safety Systems for Crew Members of\nAircraft", "4", "MAI"], ["10.1", "Flight Instrumental Equipment Systems", "3", "MAI"], ["10.2", "Flight Instrumental Complexes", "3", "MAI"], ["11.1", "Aircraft Propulsion Unit", "2", "MAI"], ["11.2", "Aircraft Propulsion Unit Formation", "2", "MAI"], ["", "Credits per semester", "31", ""], ["Semester8", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Glider Units Design (Airframe Design)", "1", "MAI"], ["2", "Landing Gear & Power Plant Unit Design", "4", "MAI"], ["3", "Quality Control Management", "2", "MAI"], ["4.1", "Aircraft Design", "4", "MAI"], ["4.2", "Theoretical Basis of Flight Vehicle Design", "4", "MAI"], ["5.1", "Maintainability &Reliability", "3", "MAI"], ["5.2", "Aircraft Performance Rating Characteristics", "3", "MAI"], ["6", "Pre-Graduation Practice", "6", "MAI"], ["7", "Final State Attestation", "9", "MAI"], ["", "Credits per semester", "29", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `08059f6de72b77520479538646e1cd0578efa2a12005c55f07c046f8b279b64d`.

### human-candidate-0075

**Câu hỏi:** AI nâng cao với NLP trong hướng dẫn thạc sĩ KHMT học ở kỳ nào vậy

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D06. Filters: `{}`.
Nhóm: `family-64dd2f8b0f77663200e9`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D06, trang 1**, `c3220664c5737cd12e6fdaa1077d92ef7598ff3af25ca80e9f366b2f0021d0f8_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Page: 1]
Table headers: STT | Mã học
phần | Tên học phần
(tiếng Việt và tiếng Anh) | Số
tín
chỉ | Học
kỳ | Ghi
chú

{"headers": ["STT", "Mã học\nphần", "Tên học phần\n(tiếng Việt và tiếng Anh)", "Số\ntín\nchỉ", "Học\nkỳ", "Ghi\nchú"], "rows": [["I", "Khối kiến thức chung", "", "7", "", ""], ["1", "PHI 5001", "Triết học\nPhilosophy", "3", "1", ""], ["2", "ENG\n5001", "Tiếng Anh cơ bản\nGeneral English", "4", "1", ""], ["II", "Khối kiến thức cơ sở và chuyên ngành", "", "39", "", ""], ["II.1", "Các học phần bắt buộc", "", "15", "", ""], ["3", "INT 6120", "Phương pháp luận nghiên cứu khoa học\nScientific Research Methodology", "3", "1", ""], ["4", "INT 6146", "Trí tuệ nhân tạo nâng cao\nAdvanced Artificial Intelligence", "3", "1", ""], ["5", "INT 6151", "Học máy thống kê\nStatistical Machine Learning", "3", "1", ""], ["6", "INT 6152", "Xử lý ngôn ngữ tự nhiên và ứng dụng\nNatural Language Processing and\nApplications", "3", "2", ""], ["7", "INT 6009", "Các vấn đề hiện đại của Khoa học Máy\ntính\nAdvanced Topics in Computer Science", "3", "2", ""], ["II.2", "Các học phần tự chọn", "", "24/60", "", ""], ["8", "", "Học phần tự chọn 1", "3", "2", ""], ["9", "", "Học phần tự chọn 2", "3", "2", ""], ["10", "", "Học phần tự chọn 3", "3", "2", ""], ["11", "", "Học phần tự chọn 4", "3", "3", ""], ["12", "", "Học phần tự chọn 5", "3", "3", ""], ["13", "", "Học phần tự chọn 6", "3", "3", ""], ["14", "", "Học phần tự chọn 7", "3", "3", ""], ["15", "", "Học phần tự chọn 8", "3", "3", ""], ["16", "INT 7208", "Luận văn", "18", "3, 4", ""], ["17", "", "Tổng cộng", "64", "", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `405265a6439f5328e83bd68de3b2bead98c26e2507c781f5cbec6a54df9bca62`.

### human-candidate-0076

**Câu hỏi:** khiển trách với cảnh cáo trong đoạn mình chọn khác nhau chỗ nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D02. Filters: `{}`.
Nhóm: `family-28d0a97d7a72131acd70`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D02, trang 1**, `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: Điều 32. Nghĩa vụ của sinh viên | Page: 1]

Điều 32. Nghĩa vụ của sinh viên
4. Sinh viên có trách nhiệm thực hiện đúng các quy định về kỷ luật phòng thi,
nếu vi phạm sẽ bị kỷ luật ở các mức sau:
a) Khiển trách: áp dụng đối với sinh viên phạm lỗi 1 lần nhìn bài của
người khác, trao đổi bài, thảo luận bài trong giờ thi. Sinh viên bị khiển trách
trong khi thi học phần nào bị trừ 25% số điểm đạt được của bài thi học phần đó;
b) Cảnh cáo: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị khiển trách 1 lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Trao đổi bài làm, giấy nháp với người khác;
- Chép bài của người khác. Những bài thi đã có kết luận là giống nhau thì
xử lý như nhau trừ trường hợp nếu người bị xử lý có đủ bằng chứng chứng tỏ
mình thực sự bị quay cóp thì thủ trưởng đơn vị đào tạo có thể xem xét giảm từ
mức kỷ luật cảnh cáo xuống mức khiển trách.
Sinh viên bị cảnh cáo trong khi thi học phần nào sẽ bị trừ 50% số điểm
đạt được của bài thi học phần đó.
c) Đình chỉ thi: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị cảnh cáo một lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Sau khi đã bóc đề thi bị phát hiện mang theo những vật dụng không
được phép;
- Đưa đề thi ra ngoài hoặc nhận bài giải từ ngoài vào phòng thi.
Sinh viên bị kỷ luật đình chỉ thi sẽ bị điểm không (0) bài thi học phần đó
và phải ra khỏi phòng thi ngay sau khi có quyết định đình chỉ thi.
Các hình thức kỷ luật nói trên do cán bộ coi thi lập biên bản, thu tang vật
và ghi rõ hình thức kỷ luật.
d) Sinh viên thi hộ hoặc nhờ người thi hộ bị kỷ luật ở mức đình chỉ học tập 1
năm đối với trường hợp vi phạm lần thứ nhất và buộc thôi học đối với trường hợp
vi phạm lần thứ hai.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f2054a913f65e66f27873c3f5681ef96477ae83272f98c9790d82f8899da0d1f`.

### human-candidate-0077

**Câu hỏi:** trong bảng mình chọn kỳ 7 với kỳ 8 tổng mấy tín

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-e6a30a0cba6640b4108b`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 3**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 3]
Table headers: Credits per semester | 32

{"headers": ["", "Credits per semester", "32", ""], "rows": [["Semester7", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Management Fundamental", "2", "MAI"], ["2", "Social Science", "2", "MAI"], ["3.1", "Engineering Task Simulation", "2", "MAI"], ["3.2", "Engineering Problem Solution with the Electronic\nComputing Machine", "2", "MAI"], ["4", "Electrical Engineering & Electronics", "3", "MAI"], ["5", "Aircraft Manufacturing Technology", "4", "MAI"], ["6", "Details & Modules Construction", "1", "MAI"], ["7", "Aviation Equipment Certification", "3", "MAI"], ["8", "Glider Units Design (Airframe Design)", "5", "MAI"], ["9.1", "Mechanical Equipment Systems", "4", "MAI"], ["9.2", "Life-Support & Safety Systems for Crew Members of\nAircraft", "4", "MAI"], ["10.1", "Flight Instrumental Equipment Systems", "3", "MAI"], ["10.2", "Flight Instrumental Complexes", "3", "MAI"], ["11.1", "Aircraft Propulsion Unit", "2", "MAI"], ["11.2", "Aircraft Propulsion Unit Formation", "2", "MAI"], ["", "Credits per semester", "31", ""], ["Semester8", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Glider Units Design (Airframe Design)", "1", "MAI"], ["2", "Landing Gear & Power Plant Unit Design", "4", "MAI"], ["3", "Quality Control Management", "2", "MAI"], ["4.1", "Aircraft Design", "4", "MAI"], ["4.2", "Theoretical Basis of Flight Vehicle Design", "4", "MAI"], ["5.1", "Maintainability &Reliability", "3", "MAI"], ["5.2", "Aircraft Performance Rating Characteristics", "3", "MAI"], ["6", "Pre-Graduation Practice", "6", "MAI"], ["7", "Final State Attestation", "9", "MAI"], ["", "Credits per semester", "29", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d50f26a3b041a6b3e759aafe0ba17960b44e0ea9cd6e9363186096c2031016d2`.

### human-candidate-0078

**Câu hỏi:** so hai file vừa tải lên thì tổng tín chỉ mỗi chương trình là bao nhiêu

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07, D09. Filters: `{}`.
Nhóm: `family-adf2da95ba447007abbe`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 1**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p1_s3_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: 155 tín chỉ | Page: 1]

155 tín chỉ
-  Khối kiến thức chung:
````

</details>

**Gold: D09, trang 7**, `cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6_p7_s26_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2004, 2012, 2013, 2014, 2018, 2021, 2022, 2023, 2030, 2032, 2035, 2036, 2040, 2041 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Tên ngành đào tạo | Section: 135 tín chỉ | Page: 7]

135 tín chỉ
- Khối kiến thức chung:
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `7f4759826209fbc6a023b545e31f07c621f34c5e41e26d53df3be9a3a213723e`.

### human-candidate-0079

**Câu hỏi:** chương trình liên kết học kỳ một tổng mấy tín

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-1e28d3e487de5bcf1531`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 1**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: MOSCOW AVIATION INSTITUTE - VIETNAM | Page: 1]
Table headers: № | Discipline | Credits | Resources

{"headers": ["№", "Discipline", "Credits", "Resources"], "rows": [["Semester 1", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Introduction to Information Technology", "3", "VNU-UET"], ["2", "Introduction to Aerospace Engineering", "3", "VNU-UET"], ["3", "General Physics 1", "2", "VNU-UET"], ["4", "Analytics 1", "4", "VNU-UET"], ["5", "Algebra", "4", "VNU-UET"], ["6", "Marxist – Leninst Philosophy", "3", "VNU-UET"], ["7", "English 1", "3", "VNU-UET"], ["8", "Physical education", "1", "VNU-UET"], ["9", "Chemistry", "3", "VNU-UET"], ["10", "Geometric Engineering and CAD 1", "4", "VNU-UET"], ["", "Creditsper semester", "30", ""], ["", "Semester 2", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Marx-Lenin Political Economy", "2", "VNU-UET"], ["2", "Ho Chi Minh Ideology", "2", "VNU-UET"], ["3", "Introduction to Programming", "3", "VNU-UET"], ["4", "Analytics 2", "4", "VNU-UET"], ["5", "General Physics 2", "2", "VNU-UET"], ["6", "English 2", "2", "VNU-UET"], ["7", "Physical education", "1", "VNU-UET"], ["8", "Signals and Systems", "3", "VNU-UET"], ["9", "Theoretical mechanics", "3", "VNU-UET"], ["", "Credits per semester", "23", ""], ["Semester 3", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Engineering Mechanics for Aerospace Eng", "3", "VNU-UET"], ["2", "Scientific Socialism", "2", "VNU-UET"], ["3", "Physical Education", "1", "VNU-UET"], ["4", "Ordinary and Partial Differential Equations", "3", "VNU-UET"], ["5", "English 3", "3", "VNU-UET"], ["6", "General materials", "3", "VNU-UET"], ["7", "Machine mechanisms", "3", "VNU-UET"], ["8", "Probability and Statistics", "3", "VNU-UET"], ["9", "Solid mechanics", "3", "VNU-UET"], ["10", "Russian Conversation for Beginners", "3", "VNU-UET"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `607225ca0a597068a09f6e2827122fa9e36dfedc98e29e0e2a6f112f77715991`.

### human-candidate-0080

**Câu hỏi:** chương trình liên kết hk1 bn tc

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-1e28d3e487de5bcf1531`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 1**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: MOSCOW AVIATION INSTITUTE - VIETNAM | Page: 1]
Table headers: № | Discipline | Credits | Resources

{"headers": ["№", "Discipline", "Credits", "Resources"], "rows": [["Semester 1", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Introduction to Information Technology", "3", "VNU-UET"], ["2", "Introduction to Aerospace Engineering", "3", "VNU-UET"], ["3", "General Physics 1", "2", "VNU-UET"], ["4", "Analytics 1", "4", "VNU-UET"], ["5", "Algebra", "4", "VNU-UET"], ["6", "Marxist – Leninst Philosophy", "3", "VNU-UET"], ["7", "English 1", "3", "VNU-UET"], ["8", "Physical education", "1", "VNU-UET"], ["9", "Chemistry", "3", "VNU-UET"], ["10", "Geometric Engineering and CAD 1", "4", "VNU-UET"], ["", "Creditsper semester", "30", ""], ["", "Semester 2", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Marx-Lenin Political Economy", "2", "VNU-UET"], ["2", "Ho Chi Minh Ideology", "2", "VNU-UET"], ["3", "Introduction to Programming", "3", "VNU-UET"], ["4", "Analytics 2", "4", "VNU-UET"], ["5", "General Physics 2", "2", "VNU-UET"], ["6", "English 2", "2", "VNU-UET"], ["7", "Physical education", "1", "VNU-UET"], ["8", "Signals and Systems", "3", "VNU-UET"], ["9", "Theoretical mechanics", "3", "VNU-UET"], ["", "Credits per semester", "23", ""], ["Semester 3", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Engineering Mechanics for Aerospace Eng", "3", "VNU-UET"], ["2", "Scientific Socialism", "2", "VNU-UET"], ["3", "Physical Education", "1", "VNU-UET"], ["4", "Ordinary and Partial Differential Equations", "3", "VNU-UET"], ["5", "English 3", "3", "VNU-UET"], ["6", "General materials", "3", "VNU-UET"], ["7", "Machine mechanisms", "3", "VNU-UET"], ["8", "Probability and Statistics", "3", "VNU-UET"], ["9", "Solid mechanics", "3", "VNU-UET"], ["10", "Russian Conversation for Beginners", "3", "VNU-UET"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `22bc30c8bac843901ea2a4f30cbc099d55494af1e81e86c7ec97b6530d1929b4`.

### human-candidate-0081

**Câu hỏi:** semester 1 total credits chương trình liên kết curriculum là bao nhiêu

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-1e28d3e487de5bcf1531`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 1**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: MOSCOW AVIATION INSTITUTE - VIETNAM | Page: 1]
Table headers: № | Discipline | Credits | Resources

{"headers": ["№", "Discipline", "Credits", "Resources"], "rows": [["Semester 1", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Introduction to Information Technology", "3", "VNU-UET"], ["2", "Introduction to Aerospace Engineering", "3", "VNU-UET"], ["3", "General Physics 1", "2", "VNU-UET"], ["4", "Analytics 1", "4", "VNU-UET"], ["5", "Algebra", "4", "VNU-UET"], ["6", "Marxist – Leninst Philosophy", "3", "VNU-UET"], ["7", "English 1", "3", "VNU-UET"], ["8", "Physical education", "1", "VNU-UET"], ["9", "Chemistry", "3", "VNU-UET"], ["10", "Geometric Engineering and CAD 1", "4", "VNU-UET"], ["", "Creditsper semester", "30", ""], ["", "Semester 2", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Marx-Lenin Political Economy", "2", "VNU-UET"], ["2", "Ho Chi Minh Ideology", "2", "VNU-UET"], ["3", "Introduction to Programming", "3", "VNU-UET"], ["4", "Analytics 2", "4", "VNU-UET"], ["5", "General Physics 2", "2", "VNU-UET"], ["6", "English 2", "2", "VNU-UET"], ["7", "Physical education", "1", "VNU-UET"], ["8", "Signals and Systems", "3", "VNU-UET"], ["9", "Theoretical mechanics", "3", "VNU-UET"], ["", "Credits per semester", "23", ""], ["Semester 3", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Engineering Mechanics for Aerospace Eng", "3", "VNU-UET"], ["2", "Scientific Socialism", "2", "VNU-UET"], ["3", "Physical Education", "1", "VNU-UET"], ["4", "Ordinary and Partial Differential Equations", "3", "VNU-UET"], ["5", "English 3", "3", "VNU-UET"], ["6", "General materials", "3", "VNU-UET"], ["7", "Machine mechanisms", "3", "VNU-UET"], ["8", "Probability and Statistics", "3", "VNU-UET"], ["9", "Solid mechanics", "3", "VNU-UET"], ["10", "Russian Conversation for Beginners", "3", "VNU-UET"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ed37eb8d2f796de0fa774eba6e0ac6b3c67e3d124fc108b286cb413125588dda`.

### human-candidate-0082

**Câu hỏi:** học chương trình với MAI theo bản đang mở thì kỳ đầu ôm bao nhiêu tín vậy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-1e28d3e487de5bcf1531`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 1**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: MOSCOW AVIATION INSTITUTE - VIETNAM | Page: 1]
Table headers: № | Discipline | Credits | Resources

{"headers": ["№", "Discipline", "Credits", "Resources"], "rows": [["Semester 1", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Introduction to Information Technology", "3", "VNU-UET"], ["2", "Introduction to Aerospace Engineering", "3", "VNU-UET"], ["3", "General Physics 1", "2", "VNU-UET"], ["4", "Analytics 1", "4", "VNU-UET"], ["5", "Algebra", "4", "VNU-UET"], ["6", "Marxist – Leninst Philosophy", "3", "VNU-UET"], ["7", "English 1", "3", "VNU-UET"], ["8", "Physical education", "1", "VNU-UET"], ["9", "Chemistry", "3", "VNU-UET"], ["10", "Geometric Engineering and CAD 1", "4", "VNU-UET"], ["", "Creditsper semester", "30", ""], ["", "Semester 2", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Marx-Lenin Political Economy", "2", "VNU-UET"], ["2", "Ho Chi Minh Ideology", "2", "VNU-UET"], ["3", "Introduction to Programming", "3", "VNU-UET"], ["4", "Analytics 2", "4", "VNU-UET"], ["5", "General Physics 2", "2", "VNU-UET"], ["6", "English 2", "2", "VNU-UET"], ["7", "Physical education", "1", "VNU-UET"], ["8", "Signals and Systems", "3", "VNU-UET"], ["9", "Theoretical mechanics", "3", "VNU-UET"], ["", "Credits per semester", "23", ""], ["Semester 3", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Engineering Mechanics for Aerospace Eng", "3", "VNU-UET"], ["2", "Scientific Socialism", "2", "VNU-UET"], ["3", "Physical Education", "1", "VNU-UET"], ["4", "Ordinary and Partial Differential Equations", "3", "VNU-UET"], ["5", "English 3", "3", "VNU-UET"], ["6", "General materials", "3", "VNU-UET"], ["7", "Machine mechanisms", "3", "VNU-UET"], ["8", "Probability and Statistics", "3", "VNU-UET"], ["9", "Solid mechanics", "3", "VNU-UET"], ["10", "Russian Conversation for Beginners", "3", "VNU-UET"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f23d73ff9bc8666c7459fd68c06d72cceb6e83697b044b051f816d7b3d38ae7c`.

### human-candidate-0083

**Câu hỏi:** khối lượng học tập của học kỳ mở đầu chương trình liên kết chương trình liên kết trong bảng là gì

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-1e28d3e487de5bcf1531`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 1**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: MOSCOW AVIATION INSTITUTE - VIETNAM | Page: 1]
Table headers: № | Discipline | Credits | Resources

{"headers": ["№", "Discipline", "Credits", "Resources"], "rows": [["Semester 1", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Introduction to Information Technology", "3", "VNU-UET"], ["2", "Introduction to Aerospace Engineering", "3", "VNU-UET"], ["3", "General Physics 1", "2", "VNU-UET"], ["4", "Analytics 1", "4", "VNU-UET"], ["5", "Algebra", "4", "VNU-UET"], ["6", "Marxist – Leninst Philosophy", "3", "VNU-UET"], ["7", "English 1", "3", "VNU-UET"], ["8", "Physical education", "1", "VNU-UET"], ["9", "Chemistry", "3", "VNU-UET"], ["10", "Geometric Engineering and CAD 1", "4", "VNU-UET"], ["", "Creditsper semester", "30", ""], ["", "Semester 2", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Marx-Lenin Political Economy", "2", "VNU-UET"], ["2", "Ho Chi Minh Ideology", "2", "VNU-UET"], ["3", "Introduction to Programming", "3", "VNU-UET"], ["4", "Analytics 2", "4", "VNU-UET"], ["5", "General Physics 2", "2", "VNU-UET"], ["6", "English 2", "2", "VNU-UET"], ["7", "Physical education", "1", "VNU-UET"], ["8", "Signals and Systems", "3", "VNU-UET"], ["9", "Theoretical mechanics", "3", "VNU-UET"], ["", "Credits per semester", "23", ""], ["Semester 3", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Engineering Mechanics for Aerospace Eng", "3", "VNU-UET"], ["2", "Scientific Socialism", "2", "VNU-UET"], ["3", "Physical Education", "1", "VNU-UET"], ["4", "Ordinary and Partial Differential Equations", "3", "VNU-UET"], ["5", "English 3", "3", "VNU-UET"], ["6", "General materials", "3", "VNU-UET"], ["7", "Machine mechanisms", "3", "VNU-UET"], ["8", "Probability and Statistics", "3", "VNU-UET"], ["9", "Solid mechanics", "3", "VNU-UET"], ["10", "Russian Conversation for Beginners", "3", "VNU-UET"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `c60931fe00659ca1960c833b006d11c4505e926ef29f55b991f646031bce9ff2`.

### human-candidate-0084

**Câu hỏi:** chuong trinh lien ket hoc ky 1 tong bao nhiu tin

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-1e28d3e487de5bcf1531`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 1**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: MOSCOW AVIATION INSTITUTE - VIETNAM | Page: 1]
Table headers: № | Discipline | Credits | Resources

{"headers": ["№", "Discipline", "Credits", "Resources"], "rows": [["Semester 1", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Introduction to Information Technology", "3", "VNU-UET"], ["2", "Introduction to Aerospace Engineering", "3", "VNU-UET"], ["3", "General Physics 1", "2", "VNU-UET"], ["4", "Analytics 1", "4", "VNU-UET"], ["5", "Algebra", "4", "VNU-UET"], ["6", "Marxist – Leninst Philosophy", "3", "VNU-UET"], ["7", "English 1", "3", "VNU-UET"], ["8", "Physical education", "1", "VNU-UET"], ["9", "Chemistry", "3", "VNU-UET"], ["10", "Geometric Engineering and CAD 1", "4", "VNU-UET"], ["", "Creditsper semester", "30", ""], ["", "Semester 2", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Marx-Lenin Political Economy", "2", "VNU-UET"], ["2", "Ho Chi Minh Ideology", "2", "VNU-UET"], ["3", "Introduction to Programming", "3", "VNU-UET"], ["4", "Analytics 2", "4", "VNU-UET"], ["5", "General Physics 2", "2", "VNU-UET"], ["6", "English 2", "2", "VNU-UET"], ["7", "Physical education", "1", "VNU-UET"], ["8", "Signals and Systems", "3", "VNU-UET"], ["9", "Theoretical mechanics", "3", "VNU-UET"], ["", "Credits per semester", "23", ""], ["Semester 3", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Engineering Mechanics for Aerospace Eng", "3", "VNU-UET"], ["2", "Scientific Socialism", "2", "VNU-UET"], ["3", "Physical Education", "1", "VNU-UET"], ["4", "Ordinary and Partial Differential Equations", "3", "VNU-UET"], ["5", "English 3", "3", "VNU-UET"], ["6", "General materials", "3", "VNU-UET"], ["7", "Machine mechanisms", "3", "VNU-UET"], ["8", "Probability and Statistics", "3", "VNU-UET"], ["9", "Solid mechanics", "3", "VNU-UET"], ["10", "Russian Conversation for Beginners", "3", "VNU-UET"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `466a8258a973bc4e1dfad2fa6762751ef64c3489ea7b670cb8685e9b2bd9c956`.

### human-candidate-0085

**Câu hỏi:** chương trình liên kết kỳ 5 học phần do trường nào phụ trách

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-41a638d5bc72a8f38510`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 2**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p2_t3`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 2]
Table headers: 3 | Technology of Structure Materials | 3 | VNU-UET

{"headers": ["3", "Technology of Structure Materials", "3", "VNU-UET"], "rows": [["4", "Thermodynamic Engineering", "3", "VNU-UET"], ["5", "Physical Education", "1", "VNU-UET"], ["6", "System Dynamic & Vibration", "3", "VNU-UET"], ["7", "Aerodynamics 1", "4", "VNU-UET"], ["8", "Applied Ecology", "2", "VNU-UET"], ["9", "Measurement Science, Standardization and Certification", "3", "VNU-UET"], ["", "Credits per semester", "24", ""], ["", "Semester 5", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Economics", "3", "MAI"], ["4", "Informational Support of Product Life Cycle", "3", "MAI"], ["5.1", "Aerodynamics 2", "4", "MAI"], ["5.2", "Aerohydrodynamics", "4", "MAI"], ["6.1", "Structural Mechanics and Aircraft Durability", "5", "MAI"], ["6.2", "Structural Mechanics &Aerostructure and Systems\nDurability", "5", "MAI"], ["7.1", "Numeral Methods", "4", "MAI"], ["7.2", "Numeral Mathematics", "4", "MAI"], ["8", "Mathematical Model Methods", "3", "MAI"], ["9", "Machine Elements & Principles of Design", "4", "MAI"], ["", "Credits per semester", "30", ""], ["Semester 6", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Informational Support of Product Life Cycle", "3", "MAI"], ["4", "Dynamics & Flightpath Control Laboratory Workshop", "2", "MAI"], ["5.1", "Flight Dynamics", "3", "MAI"], ["5.2", "Airplane Performance Computation", "3", "MAI"], ["6", "Health & Wellness Fundamentals", "2", "MAI"], ["7", "Industrial Economics & Organization", "3", "MAI"], ["8", "Aircraft Manufacturing Technology", "2", "MAI"], ["9", "Details & Modules Construction", "3", "MAI"], ["10", "Aircraft Construction", "4", "MAI"], ["11", "Engineering and Manufacturing Practice II", "6", "MAI"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `78f17a4e556c4c21c5578678ee3641528d60d4576776946042e6874e554eac32`.

### human-candidate-0086

**Câu hỏi:** chương trình liên kết hk5 bên nào dạy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-41a638d5bc72a8f38510`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 2**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p2_t3`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 2]
Table headers: 3 | Technology of Structure Materials | 3 | VNU-UET

{"headers": ["3", "Technology of Structure Materials", "3", "VNU-UET"], "rows": [["4", "Thermodynamic Engineering", "3", "VNU-UET"], ["5", "Physical Education", "1", "VNU-UET"], ["6", "System Dynamic & Vibration", "3", "VNU-UET"], ["7", "Aerodynamics 1", "4", "VNU-UET"], ["8", "Applied Ecology", "2", "VNU-UET"], ["9", "Measurement Science, Standardization and Certification", "3", "VNU-UET"], ["", "Credits per semester", "24", ""], ["", "Semester 5", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Economics", "3", "MAI"], ["4", "Informational Support of Product Life Cycle", "3", "MAI"], ["5.1", "Aerodynamics 2", "4", "MAI"], ["5.2", "Aerohydrodynamics", "4", "MAI"], ["6.1", "Structural Mechanics and Aircraft Durability", "5", "MAI"], ["6.2", "Structural Mechanics &Aerostructure and Systems\nDurability", "5", "MAI"], ["7.1", "Numeral Methods", "4", "MAI"], ["7.2", "Numeral Mathematics", "4", "MAI"], ["8", "Mathematical Model Methods", "3", "MAI"], ["9", "Machine Elements & Principles of Design", "4", "MAI"], ["", "Credits per semester", "30", ""], ["Semester 6", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Informational Support of Product Life Cycle", "3", "MAI"], ["4", "Dynamics & Flightpath Control Laboratory Workshop", "2", "MAI"], ["5.1", "Flight Dynamics", "3", "MAI"], ["5.2", "Airplane Performance Computation", "3", "MAI"], ["6", "Health & Wellness Fundamentals", "2", "MAI"], ["7", "Industrial Economics & Organization", "3", "MAI"], ["8", "Aircraft Manufacturing Technology", "2", "MAI"], ["9", "Details & Modules Construction", "3", "MAI"], ["10", "Aircraft Construction", "4", "MAI"], ["11", "Engineering and Manufacturing Practice II", "6", "MAI"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2fc6e6b74b6260f831789b5c295f42b55f30e85dcac4b47ba748fc0ef17ec411`.

### human-candidate-0087

**Câu hỏi:** semester 5 courses chương trình liên kết taught by which institution

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-41a638d5bc72a8f38510`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 2**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p2_t3`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 2]
Table headers: 3 | Technology of Structure Materials | 3 | VNU-UET

{"headers": ["3", "Technology of Structure Materials", "3", "VNU-UET"], "rows": [["4", "Thermodynamic Engineering", "3", "VNU-UET"], ["5", "Physical Education", "1", "VNU-UET"], ["6", "System Dynamic & Vibration", "3", "VNU-UET"], ["7", "Aerodynamics 1", "4", "VNU-UET"], ["8", "Applied Ecology", "2", "VNU-UET"], ["9", "Measurement Science, Standardization and Certification", "3", "VNU-UET"], ["", "Credits per semester", "24", ""], ["", "Semester 5", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Economics", "3", "MAI"], ["4", "Informational Support of Product Life Cycle", "3", "MAI"], ["5.1", "Aerodynamics 2", "4", "MAI"], ["5.2", "Aerohydrodynamics", "4", "MAI"], ["6.1", "Structural Mechanics and Aircraft Durability", "5", "MAI"], ["6.2", "Structural Mechanics &Aerostructure and Systems\nDurability", "5", "MAI"], ["7.1", "Numeral Methods", "4", "MAI"], ["7.2", "Numeral Mathematics", "4", "MAI"], ["8", "Mathematical Model Methods", "3", "MAI"], ["9", "Machine Elements & Principles of Design", "4", "MAI"], ["", "Credits per semester", "30", ""], ["Semester 6", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Informational Support of Product Life Cycle", "3", "MAI"], ["4", "Dynamics & Flightpath Control Laboratory Workshop", "2", "MAI"], ["5.1", "Flight Dynamics", "3", "MAI"], ["5.2", "Airplane Performance Computation", "3", "MAI"], ["6", "Health & Wellness Fundamentals", "2", "MAI"], ["7", "Industrial Economics & Organization", "3", "MAI"], ["8", "Aircraft Manufacturing Technology", "2", "MAI"], ["9", "Details & Modules Construction", "3", "MAI"], ["10", "Aircraft Construction", "4", "MAI"], ["11", "Engineering and Manufacturing Practice II", "6", "MAI"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e5256f0c5ceb43bc0abb8521d07e97f0b70b99df73da7c844ede997f7ba9c034`.

### human-candidate-0088

**Câu hỏi:** bản chương trình liên kết tới kỳ năm thì học bên hay bên MAI vậy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-41a638d5bc72a8f38510`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 2**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p2_t3`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 2]
Table headers: 3 | Technology of Structure Materials | 3 | VNU-UET

{"headers": ["3", "Technology of Structure Materials", "3", "VNU-UET"], "rows": [["4", "Thermodynamic Engineering", "3", "VNU-UET"], ["5", "Physical Education", "1", "VNU-UET"], ["6", "System Dynamic & Vibration", "3", "VNU-UET"], ["7", "Aerodynamics 1", "4", "VNU-UET"], ["8", "Applied Ecology", "2", "VNU-UET"], ["9", "Measurement Science, Standardization and Certification", "3", "VNU-UET"], ["", "Credits per semester", "24", ""], ["", "Semester 5", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Economics", "3", "MAI"], ["4", "Informational Support of Product Life Cycle", "3", "MAI"], ["5.1", "Aerodynamics 2", "4", "MAI"], ["5.2", "Aerohydrodynamics", "4", "MAI"], ["6.1", "Structural Mechanics and Aircraft Durability", "5", "MAI"], ["6.2", "Structural Mechanics &Aerostructure and Systems\nDurability", "5", "MAI"], ["7.1", "Numeral Methods", "4", "MAI"], ["7.2", "Numeral Mathematics", "4", "MAI"], ["8", "Mathematical Model Methods", "3", "MAI"], ["9", "Machine Elements & Principles of Design", "4", "MAI"], ["", "Credits per semester", "30", ""], ["Semester 6", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Informational Support of Product Life Cycle", "3", "MAI"], ["4", "Dynamics & Flightpath Control Laboratory Workshop", "2", "MAI"], ["5.1", "Flight Dynamics", "3", "MAI"], ["5.2", "Airplane Performance Computation", "3", "MAI"], ["6", "Health & Wellness Fundamentals", "2", "MAI"], ["7", "Industrial Economics & Organization", "3", "MAI"], ["8", "Aircraft Manufacturing Technology", "2", "MAI"], ["9", "Details & Modules Construction", "3", "MAI"], ["10", "Aircraft Construction", "4", "MAI"], ["11", "Engineering and Manufacturing Practice II", "6", "MAI"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `26a90916dd8651199b3baae8460d922bc4ee0a5ebf36738ff8c8fd3f0eaa7283`.

### human-candidate-0089

**Câu hỏi:** cột đơn vị cung cấp môn học ở học kỳ thứ năm trong bảng chương trình liên kết ghi gì

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-41a638d5bc72a8f38510`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 2**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p2_t3`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 2]
Table headers: 3 | Technology of Structure Materials | 3 | VNU-UET

{"headers": ["3", "Technology of Structure Materials", "3", "VNU-UET"], "rows": [["4", "Thermodynamic Engineering", "3", "VNU-UET"], ["5", "Physical Education", "1", "VNU-UET"], ["6", "System Dynamic & Vibration", "3", "VNU-UET"], ["7", "Aerodynamics 1", "4", "VNU-UET"], ["8", "Applied Ecology", "2", "VNU-UET"], ["9", "Measurement Science, Standardization and Certification", "3", "VNU-UET"], ["", "Credits per semester", "24", ""], ["", "Semester 5", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Economics", "3", "MAI"], ["4", "Informational Support of Product Life Cycle", "3", "MAI"], ["5.1", "Aerodynamics 2", "4", "MAI"], ["5.2", "Aerohydrodynamics", "4", "MAI"], ["6.1", "Structural Mechanics and Aircraft Durability", "5", "MAI"], ["6.2", "Structural Mechanics &Aerostructure and Systems\nDurability", "5", "MAI"], ["7.1", "Numeral Methods", "4", "MAI"], ["7.2", "Numeral Mathematics", "4", "MAI"], ["8", "Mathematical Model Methods", "3", "MAI"], ["9", "Machine Elements & Principles of Design", "4", "MAI"], ["", "Credits per semester", "30", ""], ["Semester 6", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Physical Training", "2", "MAI"], ["2", "Foreign Language", "2", "MAI"], ["3", "Informational Support of Product Life Cycle", "3", "MAI"], ["4", "Dynamics & Flightpath Control Laboratory Workshop", "2", "MAI"], ["5.1", "Flight Dynamics", "3", "MAI"], ["5.2", "Airplane Performance Computation", "3", "MAI"], ["6", "Health & Wellness Fundamentals", "2", "MAI"], ["7", "Industrial Economics & Organization", "3", "MAI"], ["8", "Aircraft Manufacturing Technology", "2", "MAI"], ["9", "Details & Modules Construction", "3", "MAI"], ["10", "Aircraft Construction", "4", "MAI"], ["11", "Engineering and Manufacturing Practice II", "6", "MAI"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `136685948465b60e12e11e5e565ae2d352a354a2d801d03caf8b28abdd70d439`.

### human-candidate-0090

**Câu hỏi:** chương trình liên kết FSA hk mấy bn tc

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-de9ca3c468709acb7aee`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 3**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 3]
Table headers: Credits per semester | 32

{"headers": ["", "Credits per semester", "32", ""], "rows": [["Semester7", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Management Fundamental", "2", "MAI"], ["2", "Social Science", "2", "MAI"], ["3.1", "Engineering Task Simulation", "2", "MAI"], ["3.2", "Engineering Problem Solution with the Electronic\nComputing Machine", "2", "MAI"], ["4", "Electrical Engineering & Electronics", "3", "MAI"], ["5", "Aircraft Manufacturing Technology", "4", "MAI"], ["6", "Details & Modules Construction", "1", "MAI"], ["7", "Aviation Equipment Certification", "3", "MAI"], ["8", "Glider Units Design (Airframe Design)", "5", "MAI"], ["9.1", "Mechanical Equipment Systems", "4", "MAI"], ["9.2", "Life-Support & Safety Systems for Crew Members of\nAircraft", "4", "MAI"], ["10.1", "Flight Instrumental Equipment Systems", "3", "MAI"], ["10.2", "Flight Instrumental Complexes", "3", "MAI"], ["11.1", "Aircraft Propulsion Unit", "2", "MAI"], ["11.2", "Aircraft Propulsion Unit Formation", "2", "MAI"], ["", "Credits per semester", "31", ""], ["Semester8", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Glider Units Design (Airframe Design)", "1", "MAI"], ["2", "Landing Gear & Power Plant Unit Design", "4", "MAI"], ["3", "Quality Control Management", "2", "MAI"], ["4.1", "Aircraft Design", "4", "MAI"], ["4.2", "Theoretical Basis of Flight Vehicle Design", "4", "MAI"], ["5.1", "Maintainability &Reliability", "3", "MAI"], ["5.2", "Aircraft Performance Rating Characteristics", "3", "MAI"], ["6", "Pre-Graduation Practice", "6", "MAI"], ["7", "Final State Attestation", "9", "MAI"], ["", "Credits per semester", "29", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `653693eb10ed6b7f79a0172d6881bb4f8cd9bfed7a866895b7eed4d028bd2a5e`.

### human-candidate-0091

**Câu hỏi:** final state attestation credits and semester in chương trình liên kết please

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-de9ca3c468709acb7aee`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 3**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 3]
Table headers: Credits per semester | 32

{"headers": ["", "Credits per semester", "32", ""], "rows": [["Semester7", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Management Fundamental", "2", "MAI"], ["2", "Social Science", "2", "MAI"], ["3.1", "Engineering Task Simulation", "2", "MAI"], ["3.2", "Engineering Problem Solution with the Electronic\nComputing Machine", "2", "MAI"], ["4", "Electrical Engineering & Electronics", "3", "MAI"], ["5", "Aircraft Manufacturing Technology", "4", "MAI"], ["6", "Details & Modules Construction", "1", "MAI"], ["7", "Aviation Equipment Certification", "3", "MAI"], ["8", "Glider Units Design (Airframe Design)", "5", "MAI"], ["9.1", "Mechanical Equipment Systems", "4", "MAI"], ["9.2", "Life-Support & Safety Systems for Crew Members of\nAircraft", "4", "MAI"], ["10.1", "Flight Instrumental Equipment Systems", "3", "MAI"], ["10.2", "Flight Instrumental Complexes", "3", "MAI"], ["11.1", "Aircraft Propulsion Unit", "2", "MAI"], ["11.2", "Aircraft Propulsion Unit Formation", "2", "MAI"], ["", "Credits per semester", "31", ""], ["Semester8", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Glider Units Design (Airframe Design)", "1", "MAI"], ["2", "Landing Gear & Power Plant Unit Design", "4", "MAI"], ["3", "Quality Control Management", "2", "MAI"], ["4.1", "Aircraft Design", "4", "MAI"], ["4.2", "Theoretical Basis of Flight Vehicle Design", "4", "MAI"], ["5.1", "Maintainability &Reliability", "3", "MAI"], ["5.2", "Aircraft Performance Rating Characteristics", "3", "MAI"], ["6", "Pre-Graduation Practice", "6", "MAI"], ["7", "Final State Attestation", "9", "MAI"], ["", "Credits per semester", "29", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `b215d2791cb024c579d58a96e937316fb377fc37bb727d112ddff4786f425800`.

### human-candidate-0092

**Câu hỏi:** phần đánh giá cuối chương trình ghi Final State Attestation trong bản chương trình liên kết học lúc nào và tính mấy tín

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-de9ca3c468709acb7aee`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 3**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 3]
Table headers: Credits per semester | 32

{"headers": ["", "Credits per semester", "32", ""], "rows": [["Semester7", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Management Fundamental", "2", "MAI"], ["2", "Social Science", "2", "MAI"], ["3.1", "Engineering Task Simulation", "2", "MAI"], ["3.2", "Engineering Problem Solution with the Electronic\nComputing Machine", "2", "MAI"], ["4", "Electrical Engineering & Electronics", "3", "MAI"], ["5", "Aircraft Manufacturing Technology", "4", "MAI"], ["6", "Details & Modules Construction", "1", "MAI"], ["7", "Aviation Equipment Certification", "3", "MAI"], ["8", "Glider Units Design (Airframe Design)", "5", "MAI"], ["9.1", "Mechanical Equipment Systems", "4", "MAI"], ["9.2", "Life-Support & Safety Systems for Crew Members of\nAircraft", "4", "MAI"], ["10.1", "Flight Instrumental Equipment Systems", "3", "MAI"], ["10.2", "Flight Instrumental Complexes", "3", "MAI"], ["11.1", "Aircraft Propulsion Unit", "2", "MAI"], ["11.2", "Aircraft Propulsion Unit Formation", "2", "MAI"], ["", "Credits per semester", "31", ""], ["Semester8", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Glider Units Design (Airframe Design)", "1", "MAI"], ["2", "Landing Gear & Power Plant Unit Design", "4", "MAI"], ["3", "Quality Control Management", "2", "MAI"], ["4.1", "Aircraft Design", "4", "MAI"], ["4.2", "Theoretical Basis of Flight Vehicle Design", "4", "MAI"], ["5.1", "Maintainability &Reliability", "3", "MAI"], ["5.2", "Aircraft Performance Rating Characteristics", "3", "MAI"], ["6", "Pre-Graduation Practice", "6", "MAI"], ["7", "Final State Attestation", "9", "MAI"], ["", "Credits per semester", "29", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d94af84fe3461bf68176d68c3e2442111202f42194594d927ec2586d7a5e1bad`.

### human-candidate-0093

**Câu hỏi:** mục kiểm định cuối khóa mang tên Final State Attestation trong bảng chương trình liên kết được xếp kỳ nào và có khối lượng tín chỉ bao nhiêu

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-de9ca3c468709acb7aee`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 3**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 3]
Table headers: Credits per semester | 32

{"headers": ["", "Credits per semester", "32", ""], "rows": [["Semester7", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Management Fundamental", "2", "MAI"], ["2", "Social Science", "2", "MAI"], ["3.1", "Engineering Task Simulation", "2", "MAI"], ["3.2", "Engineering Problem Solution with the Electronic\nComputing Machine", "2", "MAI"], ["4", "Electrical Engineering & Electronics", "3", "MAI"], ["5", "Aircraft Manufacturing Technology", "4", "MAI"], ["6", "Details & Modules Construction", "1", "MAI"], ["7", "Aviation Equipment Certification", "3", "MAI"], ["8", "Glider Units Design (Airframe Design)", "5", "MAI"], ["9.1", "Mechanical Equipment Systems", "4", "MAI"], ["9.2", "Life-Support & Safety Systems for Crew Members of\nAircraft", "4", "MAI"], ["10.1", "Flight Instrumental Equipment Systems", "3", "MAI"], ["10.2", "Flight Instrumental Complexes", "3", "MAI"], ["11.1", "Aircraft Propulsion Unit", "2", "MAI"], ["11.2", "Aircraft Propulsion Unit Formation", "2", "MAI"], ["", "Credits per semester", "31", ""], ["Semester8", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Glider Units Design (Airframe Design)", "1", "MAI"], ["2", "Landing Gear & Power Plant Unit Design", "4", "MAI"], ["3", "Quality Control Management", "2", "MAI"], ["4.1", "Aircraft Design", "4", "MAI"], ["4.2", "Theoretical Basis of Flight Vehicle Design", "4", "MAI"], ["5.1", "Maintainability &Reliability", "3", "MAI"], ["5.2", "Aircraft Performance Rating Characteristics", "3", "MAI"], ["6", "Pre-Graduation Practice", "6", "MAI"], ["7", "Final State Attestation", "9", "MAI"], ["", "Credits per semester", "29", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ae10dc63400d42ea2c00f68afbc4653651b630c018548fee71a83597e417f6ef`.

### human-candidate-0094

**Câu hỏi:** mình đang tra đúng bảng chương trình liên kết nhé, ở cuối có mục Final State Attestation nhưng cần hai thông tin để ghi kế hoạch: học kỳ và số tín chỉ của mục đó

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D03. Filters: `{}`.
Nhóm: `family-de9ca3c468709acb7aee`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D03, trang 3**, `667de97d9bc8cf4749eaac42a0f1ea3418c80544836708a576d545ecf5635e13_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Semester: 1, 2, 3 | Institution: UNIVERSITY OF | Section: VNU-UET | Page: 3]
Table headers: Credits per semester | 32

{"headers": ["", "Credits per semester", "32", ""], "rows": [["Semester7", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Management Fundamental", "2", "MAI"], ["2", "Social Science", "2", "MAI"], ["3.1", "Engineering Task Simulation", "2", "MAI"], ["3.2", "Engineering Problem Solution with the Electronic\nComputing Machine", "2", "MAI"], ["4", "Electrical Engineering & Electronics", "3", "MAI"], ["5", "Aircraft Manufacturing Technology", "4", "MAI"], ["6", "Details & Modules Construction", "1", "MAI"], ["7", "Aviation Equipment Certification", "3", "MAI"], ["8", "Glider Units Design (Airframe Design)", "5", "MAI"], ["9.1", "Mechanical Equipment Systems", "4", "MAI"], ["9.2", "Life-Support & Safety Systems for Crew Members of\nAircraft", "4", "MAI"], ["10.1", "Flight Instrumental Equipment Systems", "3", "MAI"], ["10.2", "Flight Instrumental Complexes", "3", "MAI"], ["11.1", "Aircraft Propulsion Unit", "2", "MAI"], ["11.2", "Aircraft Propulsion Unit Formation", "2", "MAI"], ["", "Credits per semester", "31", ""], ["Semester8", "", "", ""], ["", "Compulsory Subjects", "", ""], ["1", "Glider Units Design (Airframe Design)", "1", "MAI"], ["2", "Landing Gear & Power Plant Unit Design", "4", "MAI"], ["3", "Quality Control Management", "2", "MAI"], ["4.1", "Aircraft Design", "4", "MAI"], ["4.2", "Theoretical Basis of Flight Vehicle Design", "4", "MAI"], ["5.1", "Maintainability &Reliability", "3", "MAI"], ["5.2", "Aircraft Performance Rating Characteristics", "3", "MAI"], ["6", "Pre-Graduation Practice", "6", "MAI"], ["7", "Final State Attestation", "9", "MAI"], ["", "Credits per semester", "29", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `421d27b13606a92a7f7135b93f34c084aee3016012fb0807450889e4cc559f24`.

### human-candidate-0095

**Câu hỏi:** ths KHMT AI nâng cao/NLP hk mấy

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D06. Filters: `{}`.
Nhóm: `family-64dd2f8b0f77663200e9`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D06, trang 1**, `c3220664c5737cd12e6fdaa1077d92ef7598ff3af25ca80e9f366b2f0021d0f8_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Page: 1]
Table headers: STT | Mã học
phần | Tên học phần
(tiếng Việt và tiếng Anh) | Số
tín
chỉ | Học
kỳ | Ghi
chú

{"headers": ["STT", "Mã học\nphần", "Tên học phần\n(tiếng Việt và tiếng Anh)", "Số\ntín\nchỉ", "Học\nkỳ", "Ghi\nchú"], "rows": [["I", "Khối kiến thức chung", "", "7", "", ""], ["1", "PHI 5001", "Triết học\nPhilosophy", "3", "1", ""], ["2", "ENG\n5001", "Tiếng Anh cơ bản\nGeneral English", "4", "1", ""], ["II", "Khối kiến thức cơ sở và chuyên ngành", "", "39", "", ""], ["II.1", "Các học phần bắt buộc", "", "15", "", ""], ["3", "INT 6120", "Phương pháp luận nghiên cứu khoa học\nScientific Research Methodology", "3", "1", ""], ["4", "INT 6146", "Trí tuệ nhân tạo nâng cao\nAdvanced Artificial Intelligence", "3", "1", ""], ["5", "INT 6151", "Học máy thống kê\nStatistical Machine Learning", "3", "1", ""], ["6", "INT 6152", "Xử lý ngôn ngữ tự nhiên và ứng dụng\nNatural Language Processing and\nApplications", "3", "2", ""], ["7", "INT 6009", "Các vấn đề hiện đại của Khoa học Máy\ntính\nAdvanced Topics in Computer Science", "3", "2", ""], ["II.2", "Các học phần tự chọn", "", "24/60", "", ""], ["8", "", "Học phần tự chọn 1", "3", "2", ""], ["9", "", "Học phần tự chọn 2", "3", "2", ""], ["10", "", "Học phần tự chọn 3", "3", "2", ""], ["11", "", "Học phần tự chọn 4", "3", "3", ""], ["12", "", "Học phần tự chọn 5", "3", "3", ""], ["13", "", "Học phần tự chọn 6", "3", "3", ""], ["14", "", "Học phần tự chọn 7", "3", "3", ""], ["15", "", "Học phần tự chọn 8", "3", "3", ""], ["16", "INT 7208", "Luận văn", "18", "3, 4", ""], ["17", "", "Tổng cộng", "64", "", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `4ea7a1c5a302174158c0ebae3874e095062527243bf717fd4cf130218ac98612`.

### human-candidate-0096

**Câu hỏi:** Advanced AI and NLP semesters in CS master's progression là gì

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D06. Filters: `{}`.
Nhóm: `family-64dd2f8b0f77663200e9`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D06, trang 1**, `c3220664c5737cd12e6fdaa1077d92ef7598ff3af25ca80e9f366b2f0021d0f8_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Page: 1]
Table headers: STT | Mã học
phần | Tên học phần
(tiếng Việt và tiếng Anh) | Số
tín
chỉ | Học
kỳ | Ghi
chú

{"headers": ["STT", "Mã học\nphần", "Tên học phần\n(tiếng Việt và tiếng Anh)", "Số\ntín\nchỉ", "Học\nkỳ", "Ghi\nchú"], "rows": [["I", "Khối kiến thức chung", "", "7", "", ""], ["1", "PHI 5001", "Triết học\nPhilosophy", "3", "1", ""], ["2", "ENG\n5001", "Tiếng Anh cơ bản\nGeneral English", "4", "1", ""], ["II", "Khối kiến thức cơ sở và chuyên ngành", "", "39", "", ""], ["II.1", "Các học phần bắt buộc", "", "15", "", ""], ["3", "INT 6120", "Phương pháp luận nghiên cứu khoa học\nScientific Research Methodology", "3", "1", ""], ["4", "INT 6146", "Trí tuệ nhân tạo nâng cao\nAdvanced Artificial Intelligence", "3", "1", ""], ["5", "INT 6151", "Học máy thống kê\nStatistical Machine Learning", "3", "1", ""], ["6", "INT 6152", "Xử lý ngôn ngữ tự nhiên và ứng dụng\nNatural Language Processing and\nApplications", "3", "2", ""], ["7", "INT 6009", "Các vấn đề hiện đại của Khoa học Máy\ntính\nAdvanced Topics in Computer Science", "3", "2", ""], ["II.2", "Các học phần tự chọn", "", "24/60", "", ""], ["8", "", "Học phần tự chọn 1", "3", "2", ""], ["9", "", "Học phần tự chọn 2", "3", "2", ""], ["10", "", "Học phần tự chọn 3", "3", "2", ""], ["11", "", "Học phần tự chọn 4", "3", "3", ""], ["12", "", "Học phần tự chọn 5", "3", "3", ""], ["13", "", "Học phần tự chọn 6", "3", "3", ""], ["14", "", "Học phần tự chọn 7", "3", "3", ""], ["15", "", "Học phần tự chọn 8", "3", "3", ""], ["16", "INT 7208", "Luận văn", "18", "3, 4", ""], ["17", "", "Tổng cộng", "64", "", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `4dc015dbf770d10c91da6da0fd9b63439ea0cffdfdfd58e44586e49b87279255`.

### human-candidate-0097

**Câu hỏi:** hướng dẫn cao học khoa học máy tính xếp môn trí tuệ nhân tạo nâng cao trước hay sau môn xử lý ngôn ngữ tự nhiên

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D06. Filters: `{}`.
Nhóm: `family-64dd2f8b0f77663200e9`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D06, trang 1**, `c3220664c5737cd12e6fdaa1077d92ef7598ff3af25ca80e9f366b2f0021d0f8_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Page: 1]
Table headers: STT | Mã học
phần | Tên học phần
(tiếng Việt và tiếng Anh) | Số
tín
chỉ | Học
kỳ | Ghi
chú

{"headers": ["STT", "Mã học\nphần", "Tên học phần\n(tiếng Việt và tiếng Anh)", "Số\ntín\nchỉ", "Học\nkỳ", "Ghi\nchú"], "rows": [["I", "Khối kiến thức chung", "", "7", "", ""], ["1", "PHI 5001", "Triết học\nPhilosophy", "3", "1", ""], ["2", "ENG\n5001", "Tiếng Anh cơ bản\nGeneral English", "4", "1", ""], ["II", "Khối kiến thức cơ sở và chuyên ngành", "", "39", "", ""], ["II.1", "Các học phần bắt buộc", "", "15", "", ""], ["3", "INT 6120", "Phương pháp luận nghiên cứu khoa học\nScientific Research Methodology", "3", "1", ""], ["4", "INT 6146", "Trí tuệ nhân tạo nâng cao\nAdvanced Artificial Intelligence", "3", "1", ""], ["5", "INT 6151", "Học máy thống kê\nStatistical Machine Learning", "3", "1", ""], ["6", "INT 6152", "Xử lý ngôn ngữ tự nhiên và ứng dụng\nNatural Language Processing and\nApplications", "3", "2", ""], ["7", "INT 6009", "Các vấn đề hiện đại của Khoa học Máy\ntính\nAdvanced Topics in Computer Science", "3", "2", ""], ["II.2", "Các học phần tự chọn", "", "24/60", "", ""], ["8", "", "Học phần tự chọn 1", "3", "2", ""], ["9", "", "Học phần tự chọn 2", "3", "2", ""], ["10", "", "Học phần tự chọn 3", "3", "2", ""], ["11", "", "Học phần tự chọn 4", "3", "3", ""], ["12", "", "Học phần tự chọn 5", "3", "3", ""], ["13", "", "Học phần tự chọn 6", "3", "3", ""], ["14", "", "Học phần tự chọn 7", "3", "3", ""], ["15", "", "Học phần tự chọn 8", "3", "3", ""], ["16", "INT 7208", "Luận văn", "18", "3, 4", ""], ["17", "", "Tổng cộng", "64", "", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d608136328a5c32d9219a02299f2d441179bc69314737a05bb67806ba827bf55`.

### human-candidate-0098

**Câu hỏi:** hai môn về AI bậc nâng cao và xử lý văn bản ngôn ngữ trong lộ trình thạc sĩ KHMT được bố trí vào các kỳ nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D06. Filters: `{}`.
Nhóm: `family-64dd2f8b0f77663200e9`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D06, trang 1**, `c3220664c5737cd12e6fdaa1077d92ef7598ff3af25ca80e9f366b2f0021d0f8_p1_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Page: 1]
Table headers: STT | Mã học
phần | Tên học phần
(tiếng Việt và tiếng Anh) | Số
tín
chỉ | Học
kỳ | Ghi
chú

{"headers": ["STT", "Mã học\nphần", "Tên học phần\n(tiếng Việt và tiếng Anh)", "Số\ntín\nchỉ", "Học\nkỳ", "Ghi\nchú"], "rows": [["I", "Khối kiến thức chung", "", "7", "", ""], ["1", "PHI 5001", "Triết học\nPhilosophy", "3", "1", ""], ["2", "ENG\n5001", "Tiếng Anh cơ bản\nGeneral English", "4", "1", ""], ["II", "Khối kiến thức cơ sở và chuyên ngành", "", "39", "", ""], ["II.1", "Các học phần bắt buộc", "", "15", "", ""], ["3", "INT 6120", "Phương pháp luận nghiên cứu khoa học\nScientific Research Methodology", "3", "1", ""], ["4", "INT 6146", "Trí tuệ nhân tạo nâng cao\nAdvanced Artificial Intelligence", "3", "1", ""], ["5", "INT 6151", "Học máy thống kê\nStatistical Machine Learning", "3", "1", ""], ["6", "INT 6152", "Xử lý ngôn ngữ tự nhiên và ứng dụng\nNatural Language Processing and\nApplications", "3", "2", ""], ["7", "INT 6009", "Các vấn đề hiện đại của Khoa học Máy\ntính\nAdvanced Topics in Computer Science", "3", "2", ""], ["II.2", "Các học phần tự chọn", "", "24/60", "", ""], ["8", "", "Học phần tự chọn 1", "3", "2", ""], ["9", "", "Học phần tự chọn 2", "3", "2", ""], ["10", "", "Học phần tự chọn 3", "3", "2", ""], ["11", "", "Học phần tự chọn 4", "3", "3", ""], ["12", "", "Học phần tự chọn 5", "3", "3", ""], ["13", "", "Học phần tự chọn 6", "3", "3", ""], ["14", "", "Học phần tự chọn 7", "3", "3", ""], ["15", "", "Học phần tự chọn 8", "3", "3", ""], ["16", "INT 7208", "Luận văn", "18", "3, 4", ""], ["17", "", "Tổng cộng", "64", "", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e2767aac8ed3e34ac7010ef9f86dce39b454563b33d644f5bc804f97f41fde2e`.

### human-candidate-0099

**Câu hỏi:** master interview trong file này when vậy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-a63be3d1ddd1777e114b`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s32_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.2.  Thời gian phỏng vấn: ngày 17/09/2022. | Page: 5]

6.2.  Thời gian phỏng vấn: ngày 17/09/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `4ebc7db31bb5f04592700bc4af16d67cba2f1325f0e02dc1d37ff83c3821e36a`.

### human-candidate-0100

**Câu hỏi:** online application deadline for master's direct admission trong thông báo là lúc nào

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7693aa0ddf4dbfa5ce0f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s18_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ | Page: 3]

2.14. Thời gian thu nhận hồ sơ
- Thời gian đăng ký trực tuyến trên phần mềm tuyển sinh sau đại học của ĐHQGHN:
từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
- Thời gian nộp hồ sơ đăng ký xét tuyển thẳng tại Phòng Đào tạo, Trường Đại học
Công nghệ, ĐHQGHN: từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
Ghi chú: Đối với thí sinh đăng ký xét tuyển thẳng ngoài việc đăng ký trực tuyến trên
phần mềm tuyển sinh sau đại học của ĐHQGHN còn phải nộp đầy đủ hồ sơ bản cứng
tại Phòng Đào tạo, Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `94cbcae460832e397c935ad5485ff57ad582aa88ef56393d2f48a833e50d0956`.

### human-candidate-0101

**Câu hỏi:** application fee của master trong thông báo là bao nhiêu

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7d281ffb83fa79952944`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `6282d6283cc7d4335b460e4a62732eb56ef79067deadeca7e2bc0d8fdbd58c6f`.

### human-candidate-0102

**Câu hỏi:** direct admission master's trong thông báo có waive application fee không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-f6a40cbdefecdb88cc89`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f5df277a44341e402d9d5f65f1bf71ce82a8159297a6cf12024134e34d239b9d`.

### human-candidate-0103

**Câu hỏi:** application fee master's trong thông báo can I bank transfer

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7fd4f74b898637c6ad7f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `00af2b0117665c75b3e945b1fc83d1de9f1cb7d6f1022c4be9bba3a8995f10e0`.

### human-candidate-0104

**Câu hỏi:** master's annual tuition nêu trong thông báo là bao nhiêu

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-48236eb8c311d4613ba1`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s34_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: THÔNG TIN LỘ TRÌNH HỌC PHÍ TRONG QUÁ TRÌNH ĐÀO TẠO | Pages: 5-6]

THÔNG TIN LỘ TRÌNH HỌC PHÍ TRONG QUÁ TRÌNH ĐÀO TẠO
Theo Quyết định số 346/QĐ-KHTC ngày 16/05/2022 về việc Quy định, định mức
học phí đào tạo sau đại học năm học 2022-2023 của Hiệu trưởng Trường Đại học
Công nghệ, học phí đào tạo bậc thạc sĩ năm học 2022-2023 của Trường Đại học
Công nghệ là 30.000.000 đ/năm học (10 tháng).
Học phí, lộ trình tăng học phí tuân theo Nghị định 81/2021/NĐ-CP ngày
27/08/2021 "Quy định về cơ chế thu, quản lý học phí đối với cơ sở giáo dục thuộc
hệ thống giáo dục quốc dân và chính sách miễn, giảm học phí, hỗ trợ chi phí học
tập; giá dịch vụ trong lĩnh vực giáo dục, đào tạo" và Nghị định 60/2021/NĐ-CP
ngày 21/06/2021 "Quy định cơ chế tự chủ tài chính của đơn vị sự nghiệp công lập"
và các văn bản liên quan.
8.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a9897279c173686fcfd6bcb4356af61c0b6f10117c269ee6f262ea5504c4059e`.

### human-candidate-0105

**Câu hỏi:** duration of master theo uploaded notice là bao lâu

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-3182168da6478a7017c5`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 6**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p6_s35_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: THỜI GIAN CÔNG BỐ KÉT QUẢ THI,  THỜI GIAN ĐÀO TẠO | Page: 6]

THỜI GIAN CÔNG BỐ KÉT QUẢ THI,  THỜI GIAN ĐÀO TẠO
-
Thời gian công bố kết quả thi: trước 17h00 ngày 30/09/2022.
-
Thời gian đào tạo: 2 năm.
-
Hình thức đào tạo: chính qui
9.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `0dd149461a2ee9cd2e2d55af9c2633bf48ea70097ba40cae7683513c51e74b7d`.

### human-candidate-0106

**Câu hỏi:** master English entry level là level mấy

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-59a3b661cc05e4fbbb28`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 1**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p1_s9_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.2. Điều kiện về văn bằng | Page: 1]

1.2. Điều kiện về văn bằng
-
Đã tốt nghiệp hoặc đã đủ điều kiện công nhận tốt nghiệp đại học (hoặc trình độ tương
đương trở lên) ngành phù hợp từ hạng tốt nghiệp loại Khá trở lên hoặc có công bố
khoa học (sách, giáo trình, bài báo đăng trên các tạp chí khoa học chuyên ngành hoặc
các báo cáo đăng trên kỷ yếu hội nghị, hội thảo khoa học chuyên ngành) liên quan
đến lĩnh vực học tập, nghiên cứu.
-
Có năng lực ngoại ngữ từ Bậc 3 trở lên theo Khung năng lực ngoại ngữ 6 bậc dùng
cho Việt Nam đáp ứng yêu cầu về ngoại ngữ của CTĐT (lưu ý các khóa đào tạo thạc
sĩ tuyển sinh từ năm 2022 có chuẩn đầu ra đối với trình độ ngoại ngữ đạt từ Bậc 4 trở
lên hoặc tương đương theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam).
-
Văn bằng đại học do cơ sở giáo dục nước ngoài cấp phải thực hiện thủ tục công nhận
theo quy định hiện hành.
-
Đối với chương trình đào tạo chuẩn quốc tế, văn bằng đại học phải là văn bằng
chương trình đào tạo chính quy.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2c099471e91c98e97286e8b0841e6f3cbe7897deb6d50b0082d426e73fa4947e`.

### human-candidate-0107

**Câu hỏi:** master khóa nêu trong file English exit level là bao nhiêu

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-01a645838218197e6353`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 1**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p1_s9_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.2. Điều kiện về văn bằng | Page: 1]

1.2. Điều kiện về văn bằng
-
Đã tốt nghiệp hoặc đã đủ điều kiện công nhận tốt nghiệp đại học (hoặc trình độ tương
đương trở lên) ngành phù hợp từ hạng tốt nghiệp loại Khá trở lên hoặc có công bố
khoa học (sách, giáo trình, bài báo đăng trên các tạp chí khoa học chuyên ngành hoặc
các báo cáo đăng trên kỷ yếu hội nghị, hội thảo khoa học chuyên ngành) liên quan
đến lĩnh vực học tập, nghiên cứu.
-
Có năng lực ngoại ngữ từ Bậc 3 trở lên theo Khung năng lực ngoại ngữ 6 bậc dùng
cho Việt Nam đáp ứng yêu cầu về ngoại ngữ của CTĐT (lưu ý các khóa đào tạo thạc
sĩ tuyển sinh từ năm 2022 có chuẩn đầu ra đối với trình độ ngoại ngữ đạt từ Bậc 4 trở
lên hoặc tương đương theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam).
-
Văn bằng đại học do cơ sở giáo dục nước ngoài cấp phải thực hiện thủ tục công nhận
theo quy định hiện hành.
-
Đối với chương trình đào tạo chuẩn quốc tế, văn bằng đại học phải là văn bằng
chương trình đào tạo chính quy.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `80f1c82f04adcb1a0cd4e97be397496d19360fb238a0a04f48365cc0c31e1e95`.

### human-candidate-0108

**Câu hỏi:** language evidence pending khi apply master theo file đang mở, can submit later before what milestone

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-e8ab114bb11c67ef7330`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 2**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p2_s10_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.3. Điều kiện về năng lực ngoại ngữ | Page: 2]

1.3. Điều kiện về năng lực ngoại ngữ
-
Có bằng tốt nghiệp đại học, thạc sĩ, tiến sĩ được đào tạo toàn thời gian ở nước ngoài
bằng ngoại ngữ phù hợp với yêu cầu của chương trình đào tạo, được cơ quan có
thẩm quyền công nhận văn bằng theo quy định hiện hành.
-
Bằng tốt nghiệp trình độ đại học trở lên ngành ngôn ngữ nước ngoài, ngành sư
phạm ngôn ngữ nước ngoài hoặc bằng tốt nghiệp trình độ đại học trở lên mà các học
phần thuộc khối kiến thức cơ sở và chuyên ngành được thực hiện bằng ngôn ngữ
nước ngoài;
-
Bằng tốt nghiệp trình độ đại học trở lên do các đơn vị đào tạo trong ĐHQGHN cấp
trong thời gian không quá 2 năm có chuẩn đầu ra về ngoại ngữ đáp ứng yêu cầu về
năng lực ngoại ngữ để dự tuyển CTĐT thạc sĩ và thí sinh đã có chứng chỉ ngoại ngữ
đáp ứng chuẩn đầu ra trước khi tốt nghiệp CTĐT trình độ đại học;
-
Một trong các chứng chỉ ngoại ngữ đạt trình độ tương đương Bậc 3 trở lên theo
Khung năng lực Ngoại ngữ 6 bậc dùng cho Việt Nam và được ĐHQGHN công
nhận (phụ lục 1 và phụ lục 2), còn hiệu lực tính đến ngày đăng ký dự tuyển.
Ghi chú: Thí sinh có thể được nợ minh chứng về năng lực ngoại ngữ và được bổ
sung trước thời điểm Nhà trường ra quyết định trúng tuyển. Thời gian dự kiến tháng
11/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d8aa61792439c51ec159c709c3ec2a2be991588e502f5241c66e65eec66232e4`.

### human-candidate-0109

**Câu hỏi:** research bonus cap cho direct admission master là bao nhiêu

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7bd487e2a33f91e366dc`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s15_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.1. XÉT TUYỂN THẲNG > 2.1.2. Điểm thưởng thành tích nghiên cứu khoa học | Page: 3]

2.1.2. Điểm thưởng thành tích nghiên cứu khoa học
-  Đối với công trình nghiên cứu khoa học sinh viên:
+ Đạt giải thưởng cấp ĐHQGHN hoặc cấp Bộ Giáo dục và Đào tạo: giải nhất: 0.2
điểm, giải nhì 0.15 điểm, giải ba 0.1 điểm, giải khuyến khích 0.07 điểm.
+ Đạt giải thưởng cấp trường hoặc cấp khoa trực thuộc: giải nhất 0.1 điểm, giải nhì
````

</details>

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `697733e630b202cc45ba20c1a54467a9a3450824d76069f06ecdbf89ff3cdcff`.

### human-candidate-0110

**Câu hỏi:** ISI paper bonus for master's direct admission là bao nhiêu

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-22af1cc90c53f3f7dae2`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f9fb83a60fd55905b586e870f0ed6df241589a8efc337a5ab80f0e1a3613cfde`.

### human-candidate-0111

**Câu hỏi:** phong van thac sy dot 2 ngay nao

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-a63be3d1ddd1777e114b`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s32_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.2.  Thời gian phỏng vấn: ngày 17/09/2022. | Page: 5]

6.2.  Thời gian phỏng vấn: ngày 17/09/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a7b2ac3857973b6f7b203d5b10413052a8656178112fe751e08ad3d836b622a8`.

### human-candidate-0112

**Câu hỏi:** han dang ky truc tuyen tuyen thang thac si dot 2 la ngay nao

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7693aa0ddf4dbfa5ce0f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s18_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ | Page: 3]

2.14. Thời gian thu nhận hồ sơ
- Thời gian đăng ký trực tuyến trên phần mềm tuyển sinh sau đại học của ĐHQGHN:
từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
- Thời gian nộp hồ sơ đăng ký xét tuyển thẳng tại Phòng Đào tạo, Trường Đại học
Công nghệ, ĐHQGHN: từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
Ghi chú: Đối với thí sinh đăng ký xét tuyển thẳng ngoài việc đăng ký trực tuyến trên
phần mềm tuyển sinh sau đại học của ĐHQGHN còn phải nộp đầy đủ hồ sơ bản cứng
tại Phòng Đào tạo, Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2f8656747c4feb7fce85ac5aa2e42d37d90abd6489126a2104a99af61e28396a`.

### human-candidate-0113

**Câu hỏi:** phi du tuyen thac si dot 2 co chuyen khoan dc ko

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7fd4f74b898637c6ad7f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a3e8b2ae55e8f114cab7fa92935a4282fbb92760227ee0015c5f2746cd671acb`.

### human-candidate-0114

**Câu hỏi:** thac sy trong pdf dao tao may nam

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-3182168da6478a7017c5`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 6**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p6_s35_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: THỜI GIAN CÔNG BỐ KÉT QUẢ THI,  THỜI GIAN ĐÀO TẠO | Page: 6]

THỜI GIAN CÔNG BỐ KÉT QUẢ THI,  THỜI GIAN ĐÀO TẠO
-
Thời gian công bố kết quả thi: trước 17h00 ngày 30/09/2022.
-
Thời gian đào tạo: 2 năm.
-
Hình thức đào tạo: chính qui
9.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `91dc4c6d2065432ad9b98e340040570599f0b0a95ee8eaa74ab29321a157e8c7`.

### human-candidate-0115

**Câu hỏi:** bai bao isi cong may diem tuyen thag thac si

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-22af1cc90c53f3f7dae2`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `46b494a8eb8685f575beb0cecafc14a7edbec9eab386a3c8fc50887ca34b73e3`.

### human-candidate-0116

**Câu hỏi:** scopuss dc cong bn diem vao thac sy

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-ab46ef4055d290a45242`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `b31ab02ed3ab7d5108c128b0544316b2001f21af82200a5ca5cee45d1d251727`.

### human-candidate-0117

**Câu hỏi:** web dang ki thac si la trang nao

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-3b4f9d6e830d37c57d95`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s31_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 5.1. Nhiệm vụ của thí sinh | Page: 5]

5.1. Nhiệm vụ của thí sinh
-
Truy cập vào phần mềm tuyển sinh sau đại học của ĐHQGHN tại địa chỉ:
http://tssdh.vnu.edu.vn và thực hiện đăng kí dự thi trực tuyến theo hướng dẫn. Thí
sinh đã đăng ký tài khoản trong những kỳ tuyển sinh trước và chưa nhập học tại bất
kỳ đơn vị nào trong ĐHQGHN có thể sử dụng tài khoản đã có để đăng ký dự tuyển
trong năm 2022. Thí sinh phải cam kết và chịu trách nhiệm về tính trung thực trong
các thông tin khai báo.
-
Thời gian đăng kí: từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `257be74ee1e8630eeeeb7feba8404c23258648d4bb7acfe57d30574a8acd5381`.

### human-candidate-0118

**Câu hỏi:** thu khoa nganh hoc xet tung nghanh hay toan truong

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-deb7c4d2324acbd7c0c5`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `dbf25ae58dfda5d36e0ec1cc21885aacd2f9a2dd4141896fd7318fdafe6f60ae`.

### human-candidate-0119

**Câu hỏi:** deadline đăng ký tuyển thẳng cao học trong thông báo dí tới ngày nào

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7693aa0ddf4dbfa5ce0f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s18_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ | Page: 3]

2.14. Thời gian thu nhận hồ sơ
- Thời gian đăng ký trực tuyến trên phần mềm tuyển sinh sau đại học của ĐHQGHN:
từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
- Thời gian nộp hồ sơ đăng ký xét tuyển thẳng tại Phòng Đào tạo, Trường Đại học
Công nghệ, ĐHQGHN: từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
Ghi chú: Đối với thí sinh đăng ký xét tuyển thẳng ngoài việc đăng ký trực tuyến trên
phần mềm tuyển sinh sau đại học của ĐHQGHN còn phải nộp đầy đủ hồ sơ bản cứng
tại Phòng Đào tạo, Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `0dc36812f2011d691ab5dbeaf1e5f78909325ffd055a3987a01ce212faba86bf`.

### human-candidate-0120

**Câu hỏi:** đăng ký ths trong thông báo mà cert chưa về, có cho nợ tới lúc nào k

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-e8ab114bb11c67ef7330`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 2**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p2_s10_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.3. Điều kiện về năng lực ngoại ngữ | Page: 2]

1.3. Điều kiện về năng lực ngoại ngữ
-
Có bằng tốt nghiệp đại học, thạc sĩ, tiến sĩ được đào tạo toàn thời gian ở nước ngoài
bằng ngoại ngữ phù hợp với yêu cầu của chương trình đào tạo, được cơ quan có
thẩm quyền công nhận văn bằng theo quy định hiện hành.
-
Bằng tốt nghiệp trình độ đại học trở lên ngành ngôn ngữ nước ngoài, ngành sư
phạm ngôn ngữ nước ngoài hoặc bằng tốt nghiệp trình độ đại học trở lên mà các học
phần thuộc khối kiến thức cơ sở và chuyên ngành được thực hiện bằng ngôn ngữ
nước ngoài;
-
Bằng tốt nghiệp trình độ đại học trở lên do các đơn vị đào tạo trong ĐHQGHN cấp
trong thời gian không quá 2 năm có chuẩn đầu ra về ngoại ngữ đáp ứng yêu cầu về
năng lực ngoại ngữ để dự tuyển CTĐT thạc sĩ và thí sinh đã có chứng chỉ ngoại ngữ
đáp ứng chuẩn đầu ra trước khi tốt nghiệp CTĐT trình độ đại học;
-
Một trong các chứng chỉ ngoại ngữ đạt trình độ tương đương Bậc 3 trở lên theo
Khung năng lực Ngoại ngữ 6 bậc dùng cho Việt Nam và được ĐHQGHN công
nhận (phụ lục 1 và phụ lục 2), còn hiệu lực tính đến ngày đăng ký dự tuyển.
Ghi chú: Thí sinh có thể được nợ minh chứng về năng lực ngoại ngữ và được bổ
sung trước thời điểm Nhà trường ra quyết định trúng tuyển. Thời gian dự kiến tháng
11/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `68e2d1e77ceb6fdc70f740ce9c270b61cc1b7a6fd9dc9358cd8269958d037db6`.

### human-candidate-0121

**Câu hỏi:** có một môn dưới C+ là bay danh hiệu sv xuất sắc à

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-1793a321d0f86c98eead`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2be8245f0a10ef2e5dc93a65a3c9eaa568cc38c7a36d5e8b3cdefe6e07bf1be8`.

### human-candidate-0122

**Câu hỏi:** tn sớm có được chốt thủ khoa luôn k theo

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-7a548e1da444c68163d9`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `eb133671704d994f6aa0afd2954435cb0e3020eec01ea24452160c37fe31e6f3`.

### human-candidate-0123

**Câu hỏi:** dính khiển trách trong phòng thi theo bản quy chế này thì bay bao nhiêu điểm

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D02. Filters: `{}`.
Nhóm: `family-27a3cb822c498ca3b731`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D02, trang 1**, `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: Điều 32. Nghĩa vụ của sinh viên | Page: 1]

Điều 32. Nghĩa vụ của sinh viên
4. Sinh viên có trách nhiệm thực hiện đúng các quy định về kỷ luật phòng thi,
nếu vi phạm sẽ bị kỷ luật ở các mức sau:
a) Khiển trách: áp dụng đối với sinh viên phạm lỗi 1 lần nhìn bài của
người khác, trao đổi bài, thảo luận bài trong giờ thi. Sinh viên bị khiển trách
trong khi thi học phần nào bị trừ 25% số điểm đạt được của bài thi học phần đó;
b) Cảnh cáo: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị khiển trách 1 lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Trao đổi bài làm, giấy nháp với người khác;
- Chép bài của người khác. Những bài thi đã có kết luận là giống nhau thì
xử lý như nhau trừ trường hợp nếu người bị xử lý có đủ bằng chứng chứng tỏ
mình thực sự bị quay cóp thì thủ trưởng đơn vị đào tạo có thể xem xét giảm từ
mức kỷ luật cảnh cáo xuống mức khiển trách.
Sinh viên bị cảnh cáo trong khi thi học phần nào sẽ bị trừ 50% số điểm
đạt được của bài thi học phần đó.
c) Đình chỉ thi: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị cảnh cáo một lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Sau khi đã bóc đề thi bị phát hiện mang theo những vật dụng không
được phép;
- Đưa đề thi ra ngoài hoặc nhận bài giải từ ngoài vào phòng thi.
Sinh viên bị kỷ luật đình chỉ thi sẽ bị điểm không (0) bài thi học phần đó
và phải ra khỏi phòng thi ngay sau khi có quyết định đình chỉ thi.
Các hình thức kỷ luật nói trên do cán bộ coi thi lập biên bản, thu tang vật
và ghi rõ hình thức kỷ luật.
d) Sinh viên thi hộ hoặc nhờ người thi hộ bị kỷ luật ở mức đình chỉ học tập 1
năm đối với trường hợp vi phạm lần thứ nhất và buộc thôi học đối với trường hợp
vi phạm lần thứ hai.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e0d3d49a17968c24251957d9d583e234ec39e52011cbab8f59756931389dbe30`.

### human-candidate-0124

**Câu hỏi:** ăn cảnh cáo phòng thi bản là mất nửa điểm hả

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D02. Filters: `{}`.
Nhóm: `family-ddd31568f0514dc180d5`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D02, trang 1**, `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: Điều 32. Nghĩa vụ của sinh viên | Page: 1]

Điều 32. Nghĩa vụ của sinh viên
4. Sinh viên có trách nhiệm thực hiện đúng các quy định về kỷ luật phòng thi,
nếu vi phạm sẽ bị kỷ luật ở các mức sau:
a) Khiển trách: áp dụng đối với sinh viên phạm lỗi 1 lần nhìn bài của
người khác, trao đổi bài, thảo luận bài trong giờ thi. Sinh viên bị khiển trách
trong khi thi học phần nào bị trừ 25% số điểm đạt được của bài thi học phần đó;
b) Cảnh cáo: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị khiển trách 1 lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Trao đổi bài làm, giấy nháp với người khác;
- Chép bài của người khác. Những bài thi đã có kết luận là giống nhau thì
xử lý như nhau trừ trường hợp nếu người bị xử lý có đủ bằng chứng chứng tỏ
mình thực sự bị quay cóp thì thủ trưởng đơn vị đào tạo có thể xem xét giảm từ
mức kỷ luật cảnh cáo xuống mức khiển trách.
Sinh viên bị cảnh cáo trong khi thi học phần nào sẽ bị trừ 50% số điểm
đạt được của bài thi học phần đó.
c) Đình chỉ thi: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị cảnh cáo một lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Sau khi đã bóc đề thi bị phát hiện mang theo những vật dụng không
được phép;
- Đưa đề thi ra ngoài hoặc nhận bài giải từ ngoài vào phòng thi.
Sinh viên bị kỷ luật đình chỉ thi sẽ bị điểm không (0) bài thi học phần đó
và phải ra khỏi phòng thi ngay sau khi có quyết định đình chỉ thi.
Các hình thức kỷ luật nói trên do cán bộ coi thi lập biên bản, thu tang vật
và ghi rõ hình thức kỷ luật.
d) Sinh viên thi hộ hoặc nhờ người thi hộ bị kỷ luật ở mức đình chỉ học tập 1
năm đối với trường hợp vi phạm lần thứ nhất và buộc thôi học đối với trường hợp
vi phạm lần thứ hai.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `6b45fffc9cd2d37728d7f3b3889cd053f292a80880ed624f01652dce3f2d88e5`.

### human-candidate-0125

**Câu hỏi:** bị đình chỉ thi bản quy chế này là ăn 0 rồi ra ngoài luôn à

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D02. Filters: `{}`.
Nhóm: `family-fff2707a89c2f14e674a`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D02, trang 1**, `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: Điều 32. Nghĩa vụ của sinh viên | Page: 1]

Điều 32. Nghĩa vụ của sinh viên
4. Sinh viên có trách nhiệm thực hiện đúng các quy định về kỷ luật phòng thi,
nếu vi phạm sẽ bị kỷ luật ở các mức sau:
a) Khiển trách: áp dụng đối với sinh viên phạm lỗi 1 lần nhìn bài của
người khác, trao đổi bài, thảo luận bài trong giờ thi. Sinh viên bị khiển trách
trong khi thi học phần nào bị trừ 25% số điểm đạt được của bài thi học phần đó;
b) Cảnh cáo: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị khiển trách 1 lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Trao đổi bài làm, giấy nháp với người khác;
- Chép bài của người khác. Những bài thi đã có kết luận là giống nhau thì
xử lý như nhau trừ trường hợp nếu người bị xử lý có đủ bằng chứng chứng tỏ
mình thực sự bị quay cóp thì thủ trưởng đơn vị đào tạo có thể xem xét giảm từ
mức kỷ luật cảnh cáo xuống mức khiển trách.
Sinh viên bị cảnh cáo trong khi thi học phần nào sẽ bị trừ 50% số điểm
đạt được của bài thi học phần đó.
c) Đình chỉ thi: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị cảnh cáo một lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Sau khi đã bóc đề thi bị phát hiện mang theo những vật dụng không
được phép;
- Đưa đề thi ra ngoài hoặc nhận bài giải từ ngoài vào phòng thi.
Sinh viên bị kỷ luật đình chỉ thi sẽ bị điểm không (0) bài thi học phần đó
và phải ra khỏi phòng thi ngay sau khi có quyết định đình chỉ thi.
Các hình thức kỷ luật nói trên do cán bộ coi thi lập biên bản, thu tang vật
và ghi rõ hình thức kỷ luật.
d) Sinh viên thi hộ hoặc nhờ người thi hộ bị kỷ luật ở mức đình chỉ học tập 1
năm đối với trường hợp vi phạm lần thứ nhất và buộc thôi học đối với trường hợp
vi phạm lần thứ hai.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a5f6634efd4dbecd49a9d0b5c66a30b897797d11059ab40d65325acf8ca85f2b`.

### human-candidate-0126

**Câu hỏi:** thi hộ lần 1 theo bản quy chế này bị nghỉ học bao lâu

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D02. Filters: `{}`.
Nhóm: `family-adfd7e93bd052189a754`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D02, trang 1**, `3d2d91de10423ddd460d64aa7ddeea48af872d97a52eb8dfe716940da99748e1_p1_s4_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: Điều 32. Nghĩa vụ của sinh viên | Page: 1]

Điều 32. Nghĩa vụ của sinh viên
4. Sinh viên có trách nhiệm thực hiện đúng các quy định về kỷ luật phòng thi,
nếu vi phạm sẽ bị kỷ luật ở các mức sau:
a) Khiển trách: áp dụng đối với sinh viên phạm lỗi 1 lần nhìn bài của
người khác, trao đổi bài, thảo luận bài trong giờ thi. Sinh viên bị khiển trách
trong khi thi học phần nào bị trừ 25% số điểm đạt được của bài thi học phần đó;
b) Cảnh cáo: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị khiển trách 1 lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Trao đổi bài làm, giấy nháp với người khác;
- Chép bài của người khác. Những bài thi đã có kết luận là giống nhau thì
xử lý như nhau trừ trường hợp nếu người bị xử lý có đủ bằng chứng chứng tỏ
mình thực sự bị quay cóp thì thủ trưởng đơn vị đào tạo có thể xem xét giảm từ
mức kỷ luật cảnh cáo xuống mức khiển trách.
Sinh viên bị cảnh cáo trong khi thi học phần nào sẽ bị trừ 50% số điểm
đạt được của bài thi học phần đó.
c) Đình chỉ thi: áp dụng đối với sinh viên vi phạm một trong các lỗi:
- Đã bị cảnh cáo một lần nhưng trong giờ thi học phần đó vẫn tiếp tục vi
phạm quy định;
- Sau khi đã bóc đề thi bị phát hiện mang theo những vật dụng không
được phép;
- Đưa đề thi ra ngoài hoặc nhận bài giải từ ngoài vào phòng thi.
Sinh viên bị kỷ luật đình chỉ thi sẽ bị điểm không (0) bài thi học phần đó
và phải ra khỏi phòng thi ngay sau khi có quyết định đình chỉ thi.
Các hình thức kỷ luật nói trên do cán bộ coi thi lập biên bản, thu tang vật
và ghi rõ hình thức kỷ luật.
d) Sinh viên thi hộ hoặc nhờ người thi hộ bị kỷ luật ở mức đình chỉ học tập 1
năm đối với trường hợp vi phạm lần thứ nhất và buộc thôi học đối với trường hợp
vi phạm lần thứ hai.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `b9a19c9b9144ac64be0f63b3d89c8c42981d44efb2c95991bfa850187ede02bb`.

### human-candidate-0127

**Câu hỏi:** pv ths trong thông báo ngày bn

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-a63be3d1ddd1777e114b`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s32_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.2.  Thời gian phỏng vấn: ngày 17/09/2022. | Page: 5]

6.2.  Thời gian phỏng vấn: ngày 17/09/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e635bb292672a0655f82a52ade5e8a550fff9b65379956348632b3df968aa8c8`.

### human-candidate-0128

**Câu hỏi:** xtt ths đ2 chốt đk online bn h

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7693aa0ddf4dbfa5ce0f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s18_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ | Page: 3]

2.14. Thời gian thu nhận hồ sơ
- Thời gian đăng ký trực tuyến trên phần mềm tuyển sinh sau đại học của ĐHQGHN:
từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
- Thời gian nộp hồ sơ đăng ký xét tuyển thẳng tại Phòng Đào tạo, Trường Đại học
Công nghệ, ĐHQGHN: từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
Ghi chú: Đối với thí sinh đăng ký xét tuyển thẳng ngoài việc đăng ký trực tuyến trên
phần mềm tuyển sinh sau đại học của ĐHQGHN còn phải nộp đầy đủ hồ sơ bản cứng
tại Phòng Đào tạo, Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e16770b3acf3364cd75190d12bea3ac4574bcbb996c969a35672245bfebbbb1d`.

### human-candidate-0129

**Câu hỏi:** lp thi ths trong thông báo bn tiền

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7d281ffb83fa79952944`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f96bb2fa0702ad547cce9343784dfe1e058b51116063106e606f17a7e1cdfa88`.

### human-candidate-0130

**Câu hỏi:** xtt ths trong thông báo có mất lp k

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-f6a40cbdefecdb88cc89`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `66d8dce009cb27722d0fab903611fb0ce1c7758e88413de307cdeba90a14fead`.

### human-candidate-0131

**Câu hỏi:** hp ths nêu trong thông báo bn/năm

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-48236eb8c311d4613ba1`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s34_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: THÔNG TIN LỘ TRÌNH HỌC PHÍ TRONG QUÁ TRÌNH ĐÀO TẠO | Pages: 5-6]

THÔNG TIN LỘ TRÌNH HỌC PHÍ TRONG QUÁ TRÌNH ĐÀO TẠO
Theo Quyết định số 346/QĐ-KHTC ngày 16/05/2022 về việc Quy định, định mức
học phí đào tạo sau đại học năm học 2022-2023 của Hiệu trưởng Trường Đại học
Công nghệ, học phí đào tạo bậc thạc sĩ năm học 2022-2023 của Trường Đại học
Công nghệ là 30.000.000 đ/năm học (10 tháng).
Học phí, lộ trình tăng học phí tuân theo Nghị định 81/2021/NĐ-CP ngày
27/08/2021 "Quy định về cơ chế thu, quản lý học phí đối với cơ sở giáo dục thuộc
hệ thống giáo dục quốc dân và chính sách miễn, giảm học phí, hỗ trợ chi phí học
tập; giá dịch vụ trong lĩnh vực giáo dục, đào tạo" và Nghị định 60/2021/NĐ-CP
ngày 21/06/2021 "Quy định cơ chế tự chủ tài chính của đơn vị sự nghiệp công lập"
và các văn bản liên quan.
8.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `c3e59a6ca92b8e20d90fadfe6d212d63b75536b216558762edbaa7b2bd25e562`.

### human-candidate-0132

**Câu hỏi:** ths trong thông báo tg đào tạo bn năm

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-3182168da6478a7017c5`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 6**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p6_s35_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: THỜI GIAN CÔNG BỐ KÉT QUẢ THI,  THỜI GIAN ĐÀO TẠO | Page: 6]

THỜI GIAN CÔNG BỐ KÉT QUẢ THI,  THỜI GIAN ĐÀO TẠO
-
Thời gian công bố kết quả thi: trước 17h00 ngày 30/09/2022.
-
Thời gian đào tạo: 2 năm.
-
Hình thức đào tạo: chính qui
9.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `50a48532c54dd3a9dcc409ff36692745e1a223c75aa3f891b60526de4ba54802`.

### human-candidate-0133

**Câu hỏi:** ths NN đầu vào bậc bn

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-59a3b661cc05e4fbbb28`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 1**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p1_s9_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.2. Điều kiện về văn bằng | Page: 1]

1.2. Điều kiện về văn bằng
-
Đã tốt nghiệp hoặc đã đủ điều kiện công nhận tốt nghiệp đại học (hoặc trình độ tương
đương trở lên) ngành phù hợp từ hạng tốt nghiệp loại Khá trở lên hoặc có công bố
khoa học (sách, giáo trình, bài báo đăng trên các tạp chí khoa học chuyên ngành hoặc
các báo cáo đăng trên kỷ yếu hội nghị, hội thảo khoa học chuyên ngành) liên quan
đến lĩnh vực học tập, nghiên cứu.
-
Có năng lực ngoại ngữ từ Bậc 3 trở lên theo Khung năng lực ngoại ngữ 6 bậc dùng
cho Việt Nam đáp ứng yêu cầu về ngoại ngữ của CTĐT (lưu ý các khóa đào tạo thạc
sĩ tuyển sinh từ năm 2022 có chuẩn đầu ra đối với trình độ ngoại ngữ đạt từ Bậc 4 trở
lên hoặc tương đương theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam).
-
Văn bằng đại học do cơ sở giáo dục nước ngoài cấp phải thực hiện thủ tục công nhận
theo quy định hiện hành.
-
Đối với chương trình đào tạo chuẩn quốc tế, văn bằng đại học phải là văn bằng
chương trình đào tạo chính quy.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f6b8edbba28921043bf83abc97746337ad74a879af6291202cf47646b7c29144`.

### human-candidate-0134

**Câu hỏi:** ths khóa nêu trong file NN đầu ra bậc bn

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-01a645838218197e6353`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 1**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p1_s9_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.2. Điều kiện về văn bằng | Page: 1]

1.2. Điều kiện về văn bằng
-
Đã tốt nghiệp hoặc đã đủ điều kiện công nhận tốt nghiệp đại học (hoặc trình độ tương
đương trở lên) ngành phù hợp từ hạng tốt nghiệp loại Khá trở lên hoặc có công bố
khoa học (sách, giáo trình, bài báo đăng trên các tạp chí khoa học chuyên ngành hoặc
các báo cáo đăng trên kỷ yếu hội nghị, hội thảo khoa học chuyên ngành) liên quan
đến lĩnh vực học tập, nghiên cứu.
-
Có năng lực ngoại ngữ từ Bậc 3 trở lên theo Khung năng lực ngoại ngữ 6 bậc dùng
cho Việt Nam đáp ứng yêu cầu về ngoại ngữ của CTĐT (lưu ý các khóa đào tạo thạc
sĩ tuyển sinh từ năm 2022 có chuẩn đầu ra đối với trình độ ngoại ngữ đạt từ Bậc 4 trở
lên hoặc tương đương theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam).
-
Văn bằng đại học do cơ sở giáo dục nước ngoài cấp phải thực hiện thủ tục công nhận
theo quy định hiện hành.
-
Đối với chương trình đào tạo chuẩn quốc tế, văn bằng đại học phải là văn bằng
chương trình đào tạo chính quy.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `fccef7499e0c2a8b2517cf7862b98704e0f01ba3326958b263b092d473f2f517`.

### human-candidate-0135

**Câu hỏi:** xtt ths điểm NCKH cộng dồn cap bn

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7bd487e2a33f91e366dc`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s15_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.1. XÉT TUYỂN THẲNG > 2.1.2. Điểm thưởng thành tích nghiên cứu khoa học | Page: 3]

2.1.2. Điểm thưởng thành tích nghiên cứu khoa học
-  Đối với công trình nghiên cứu khoa học sinh viên:
+ Đạt giải thưởng cấp ĐHQGHN hoặc cấp Bộ Giáo dục và Đào tạo: giải nhất: 0.2
điểm, giải nhì 0.15 điểm, giải ba 0.1 điểm, giải khuyến khích 0.07 điểm.
+ Đạt giải thưởng cấp trường hoặc cấp khoa trực thuộc: giải nhất 0.1 điểm, giải nhì
````

</details>

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `af7ea174b909042f82dde7bd9b87daae24a9596cff414eb0ffcccb2bcb0eb5e6`.

### human-candidate-0136

**Câu hỏi:** ISI => xtt ths + bn điểm

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-22af1cc90c53f3f7dae2`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `26093cc6c71ef95a0b830ff94aba7f3e73e7c41107bc324127bd372f407eb633`.

### human-candidate-0137

**Câu hỏi:** scopus +bn đ xtt ths

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-ab46ef4055d290a45242`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `23c6291cef3e15e7501ddd942980d65e77c0edef62c3172c66c6d712a89d348a`.

### human-candidate-0138

**Câu hỏi:** xtt ths trong thông báo lịch xét + ngày có kq

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-fa8ab7404ea45210a57a`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s20_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022 | Page: 4]

2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022
````

</details>

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s21_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022 | Page: 4]

2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e064da937dd6ddf6072eb463efa1594bd3870835a449bb46a67d84ca014b22e3`.

### human-candidate-0139

**Câu hỏi:** em vừa up thông báo cao học, đang mở điện thoại trên xe bus nên đọc hơi rối 😵 em tìm mãi không ra giờ đóng đăng ký online diện tuyển thẳng, nhờ xem giúp chính xác ngày và giờ, em sợ lỡ hạn

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7693aa0ddf4dbfa5ce0f`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s18_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ | Page: 3]

2.14. Thời gian thu nhận hồ sơ
- Thời gian đăng ký trực tuyến trên phần mềm tuyển sinh sau đại học của ĐHQGHN:
từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
- Thời gian nộp hồ sơ đăng ký xét tuyển thẳng tại Phòng Đào tạo, Trường Đại học
Công nghệ, ĐHQGHN: từ 8h00 ngày 15/07/2022 đến 17h00 ngày 30/08/2022.
Ghi chú: Đối với thí sinh đăng ký xét tuyển thẳng ngoài việc đăng ký trực tuyến trên
phần mềm tuyển sinh sau đại học của ĐHQGHN còn phải nộp đầy đủ hồ sơ bản cứng
tại Phòng Đào tạo, Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `858cf394c3df7a4695a01d7aa347c740f752d8fe853f54d8de060940ab690db9`.

### human-candidate-0140

**Câu hỏi:** em hỏi riêng về thông báo thạc sĩ trong file này nhé, em thuộc diện xét tuyển thẳng chứ không phỏng vấn, vậy khoản lệ phí có được bỏ qua hay vẫn phải đóng

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-f6a40cbdefecdb88cc89`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `5c5c466a880bdf0ebb7d07799aa90e6866f539d54ed10db081dcab1ce50f41f1`.

### human-candidate-0141

**Câu hỏi:** mình đang tính tiền học với tiền trọ nhưng hỏi mỗi tiền học thôi nha, file mình vừa up ghi học phí thạc sĩ bao nhiêu một năm? chỉ lấy mức trong file, tiền trọ với tiền ăn mình tính sau, đọc bảng phí hơi loạn

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-48236eb8c311d4613ba1`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s34_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: THÔNG TIN LỘ TRÌNH HỌC PHÍ TRONG QUÁ TRÌNH ĐÀO TẠO | Pages: 5-6]

THÔNG TIN LỘ TRÌNH HỌC PHÍ TRONG QUÁ TRÌNH ĐÀO TẠO
Theo Quyết định số 346/QĐ-KHTC ngày 16/05/2022 về việc Quy định, định mức
học phí đào tạo sau đại học năm học 2022-2023 của Hiệu trưởng Trường Đại học
Công nghệ, học phí đào tạo bậc thạc sĩ năm học 2022-2023 của Trường Đại học
Công nghệ là 30.000.000 đ/năm học (10 tháng).
Học phí, lộ trình tăng học phí tuân theo Nghị định 81/2021/NĐ-CP ngày
27/08/2021 "Quy định về cơ chế thu, quản lý học phí đối với cơ sở giáo dục thuộc
hệ thống giáo dục quốc dân và chính sách miễn, giảm học phí, hỗ trợ chi phí học
tập; giá dịch vụ trong lĩnh vực giáo dục, đào tạo" và Nghị định 60/2021/NĐ-CP
ngày 21/06/2021 "Quy định cơ chế tự chủ tài chính của đơn vị sự nghiệp công lập"
và các văn bản liên quan.
8.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `478b403bd1872ba586643e485b56132e52358ca389821aa44bb60da9a4ed9b48`.

### human-candidate-0142

**Câu hỏi:** em đang đối chiếu thông báo thạc sĩ theo file đang mở, lúc đăng ký có thể chưa kịp nhận chứng chỉ ngoại ngữ nên muốn biết có được nộp hồ sơ trước rồi bổ sung không và phải bổ sung trước khi nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-e8ab114bb11c67ef7330`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 2**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p2_s10_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.3. Điều kiện về năng lực ngoại ngữ | Page: 2]

1.3. Điều kiện về năng lực ngoại ngữ
-
Có bằng tốt nghiệp đại học, thạc sĩ, tiến sĩ được đào tạo toàn thời gian ở nước ngoài
bằng ngoại ngữ phù hợp với yêu cầu của chương trình đào tạo, được cơ quan có
thẩm quyền công nhận văn bằng theo quy định hiện hành.
-
Bằng tốt nghiệp trình độ đại học trở lên ngành ngôn ngữ nước ngoài, ngành sư
phạm ngôn ngữ nước ngoài hoặc bằng tốt nghiệp trình độ đại học trở lên mà các học
phần thuộc khối kiến thức cơ sở và chuyên ngành được thực hiện bằng ngôn ngữ
nước ngoài;
-
Bằng tốt nghiệp trình độ đại học trở lên do các đơn vị đào tạo trong ĐHQGHN cấp
trong thời gian không quá 2 năm có chuẩn đầu ra về ngoại ngữ đáp ứng yêu cầu về
năng lực ngoại ngữ để dự tuyển CTĐT thạc sĩ và thí sinh đã có chứng chỉ ngoại ngữ
đáp ứng chuẩn đầu ra trước khi tốt nghiệp CTĐT trình độ đại học;
-
Một trong các chứng chỉ ngoại ngữ đạt trình độ tương đương Bậc 3 trở lên theo
Khung năng lực Ngoại ngữ 6 bậc dùng cho Việt Nam và được ĐHQGHN công
nhận (phụ lục 1 và phụ lục 2), còn hiệu lực tính đến ngày đăng ký dự tuyển.
Ghi chú: Thí sinh có thể được nợ minh chứng về năng lực ngoại ngữ và được bổ
sung trước thời điểm Nhà trường ra quyết định trúng tuyển. Thời gian dự kiến tháng
11/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `840cde3c544eb012d0e1d66c7a1fdc8f2332d7392614435c1e5340ba2b57786a`.

### human-candidate-0143

**Câu hỏi:** mình đọc thông báo cao học rồi mà hơi lú, thấy giải nghiên cứu cộng điểm, bài báo cũng cộng, bạn mình cứ bảo cộng hết là được 😂 nếu có nhiều loại cùng lúc thì trong file có trần tổng điểm cộng không nhỉ

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7bd487e2a33f91e366dc`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s15_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.1. XÉT TUYỂN THẲNG > 2.1.2. Điểm thưởng thành tích nghiên cứu khoa học | Page: 3]

2.1.2. Điểm thưởng thành tích nghiên cứu khoa học
-  Đối với công trình nghiên cứu khoa học sinh viên:
+ Đạt giải thưởng cấp ĐHQGHN hoặc cấp Bộ Giáo dục và Đào tạo: giải nhất: 0.2
điểm, giải nhì 0.15 điểm, giải ba 0.1 điểm, giải khuyến khích 0.07 điểm.
+ Đạt giải thưởng cấp trường hoặc cấp khoa trực thuộc: giải nhất 0.1 điểm, giải nhì
````

</details>

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `b13acc1eb61872a27f6d2a8f07580010d02a656521c3889cdbcdc170f0fa0ae1`.

### human-candidate-0144

**Câu hỏi:** mình cần ghi hai mốc riêng của xét tuyển thẳng thạc sĩ trong thông báo: khoảng thời gian hội đồng xét và ngày thông báo kết quả, nhờ bạn phân biệt giúp

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-fa8ab7404ea45210a57a`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s20_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022 | Page: 4]

2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022
````

</details>

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s21_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022 | Page: 4]

2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `5143210e4c8d85843d6abb14c9223e1daae7867f066226436d4e191b854ac013`.

### human-candidate-0145

**Câu hỏi:** em đang hỏi danh hiệu Sinh viên Xuất sắc trong quy định, không phải học bổng nhé, nếu tổng học tập và rèn luyện đều xuất sắc nhưng lỡ một môn dưới C+ thì có bị loại không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-1793a321d0f86c98eead`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `9729c0303a1db3fb752a6562b9b7b2450763bf7cd477969439e16084b7f09e45`.

### human-candidate-0146

**Câu hỏi:** cho mình hỏi ngoài lề tí à mà vẫn về file vừa up 😅 nếu học nhanh xong trước khóa thì xét thủ khoa ngay đợt mình ra trường hay chờ khóa ra trường đúng hạn? bạn mình nói hai kiểu nên mình không biết tin bên nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-7a548e1da444c68163d9`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `cfcc0ea14ae65a2e6172a3ab9f124d9177658d967a310e79dccffb5611c5b7fa`.

### human-candidate-0147

**Câu hỏi:** em thấy có danh hiệu sinh viên có đóng góp cho công tác tập thể trong quy định, nhờ tách giúp điều kiện về GPA, điểm môn, rèn luyện và vai trò cán bộ chứ em đọc hơi rối

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-64a1f59f724befd13a99`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA
Việc khen thưởng thành tích học tập và rèn luyện của sinh viên/tập thể sinh viên được
tiến hành vào cuối năm học và cuối khóa học đối với các tập thể và cá nhân không bị kỷ luật
trong năm học/khóa học và đang học tập tại Trường ở thời điểm xét/đủ điều kiện tốt nghiệp
đối với sinh viên cuối khóa, cụ thể:
Điều 3: Danh hiệu “Thủ khoa ngành học” được trao cho các sinh viên tốt nghiệp đúng
thời hạn đào tạo chuẩn và có điểm trung bình toàn khóa học cao nhất trong ngành học (nếu
sinh viên tốt nghiệp trước hạn thì sẽ được xem xét vào thời điểm tốt nghiệp đúng hạn của
ngành đào tạo).

Sinh viên đạt danh hiệu này được nhận kỉ niệm chương và Giấy chứng nhận
của Hiệu trưởng Nhà trường.
798
15
08
Điều 4: Danh hiệu “Sinh viên Xuất sắc” được trao cho các sinh viên có kết quả học
tập và rèn luyện trong năm học/toàn khóa học đạt loại Xuất sắc và không có học phần nào
có điểm dưới C+.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy khen của Hiệu trưởng Nhà
trường và tiền thưởng theo quy định hiện hành của Đại học Quốc gia Hà Nội và của Trường
Đại học Công nghệ.

Điều 5: Danh hiệu “Sinh viên Giỏi” được trao cho các sinh viên có kết quả học tập
trong năm học/toàn khóa học đạt loại Giỏi trở lên và không có học phần nào có điểm dưới
C+, kết quả rèn luyện đạt loại Tốt trở lên.

Sinh viên đạt danh hiệu này sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 6: Danh hiệu “Sinh viên có đóng góp cho công tác tập thể” được trao cho các
sinh viên đạt kết quả học tập trong năm học/toàn khóa từ 3.0 trở lên, không có học phần nào
có điểm dưới D, đạt kết quả rèn luyện trong năm học/toàn khóa loại Xuất sắc, đồng thời giữ
ít nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.
````

</details>

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

t nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 7: Danh hiệu “Sinh viên bảo vệ khóa luận/đồ án tốt nghiệp Xuất sắc” được trao
cho các sinh viên tốt nghiệp đúng hoặc trước thời hạn đào tạo chuẩn, có kết quả học tập và
rèn luyện toàn khóa học đạt từ loại Khá trở lên và có kết quả bảo vệ khóa luận/đồ án tốt
nghiệp được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc.

Sinh viên đạt
danh hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 8: Danh hiệu “Tập thể Tiên tiến” được trao cho các tập thể đạt các tiêu chuẩn
sau: Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên; Không có sinh viên
xếp loại học tập và rèn luyện loại Yếu trở xuống (không tính các trường hợp sinh viên đã tự
ý nghỉ học/bỏ học hoặc thuộc diện không tương tác); Tập thể đoàn kết, giúp đỡ lẫn nhau
trong học tập, rèn luyện, tổ chức nhiều hoạt động thi đua và tích cực hưởng ứng các phong
trào thi đua trong Nhà trường.

Tập thể đạt danh hiệu “Tập thể Tiên tiến” sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 9: Danh hiệu “Tập thể Xuất sắc” được trao cho các tập thể đạt các tiêu chuẩn
của danh hiệu “Tập thể Tiên tiến” và có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên
Giỏi” và có sinh viên đạt danh hiệu “Sinh viên Xuất sắc”.

Tập thể đạt Danh hiệu “Tập thể
Xuất sắc” sẽ được tặng Giấy khen của Hiệu trưởng Nhà trường và tiền thưởng theo quy định
hiện hành của Đại học Quốc gia Hà Nội và của Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `13816e4367af1c39817882b2d4b70fddbaaa78ca869347fbe8b43c189c967d7b`.

### human-candidate-0148

**Câu hỏi:** mình chỉ hỏi danh hiệu khóa luận hoặc đồ án xuất sắc theo quy định, không hỏi điểm chấm riêng, sinh viên còn phải tốt nghiệp vào lúc nào và học tập rèn luyện ở mức nào mới được khen

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D04. Filters: `{}`.
Nhóm: `family-b3f576c04ba97aa7d0c5`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D04, trang 2**, `7489db58974835607085d5244795f2e9ca4ba4f137bc2f7ce0b1fc1358ec6c2b_p2_s16_c2`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2017, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Section: THÀNH TÍCH HỌC TẬP VÀ RÈN LUYỆN TRONG NĂM HỌC/TOÀN KHÓA | Pages: 2-3]

t nhất một chức vụ trong Ban cán sự lớp/Ban chấp hành Đoàn-Hội các cấp và có đóng góp
tích cực cho công tác Đoàn và phong trào sinh viên trong Nhà trường.

Sinh viên đạt danh
hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 7: Danh hiệu “Sinh viên bảo vệ khóa luận/đồ án tốt nghiệp Xuất sắc” được trao
cho các sinh viên tốt nghiệp đúng hoặc trước thời hạn đào tạo chuẩn, có kết quả học tập và
rèn luyện toàn khóa học đạt từ loại Khá trở lên và có kết quả bảo vệ khóa luận/đồ án tốt
nghiệp được Hội đồng chấm khóa luận/đồ án công nhận đạt kết quả Xuất sắc.

Sinh viên đạt
danh hiệu này sẽ được tặng Giấy chứng nhận của Hiệu trưởng Nhà trường.

Điều 8: Danh hiệu “Tập thể Tiên tiến” được trao cho các tập thể đạt các tiêu chuẩn
sau: Có 70% sinh viên đạt kết quả học tập và rèn luyện loại Khá trở lên; Không có sinh viên
xếp loại học tập và rèn luyện loại Yếu trở xuống (không tính các trường hợp sinh viên đã tự
ý nghỉ học/bỏ học hoặc thuộc diện không tương tác); Tập thể đoàn kết, giúp đỡ lẫn nhau
trong học tập, rèn luyện, tổ chức nhiều hoạt động thi đua và tích cực hưởng ứng các phong
trào thi đua trong Nhà trường.

Tập thể đạt danh hiệu “Tập thể Tiên tiến” sẽ được tặng Giấy
chứng nhận của Hiệu trưởng Nhà trường.

Điều 9: Danh hiệu “Tập thể Xuất sắc” được trao cho các tập thể đạt các tiêu chuẩn
của danh hiệu “Tập thể Tiên tiến” và có từ 10% sinh viên trở lên đạt danh hiệu “Sinh viên
Giỏi” và có sinh viên đạt danh hiệu “Sinh viên Xuất sắc”.

Tập thể đạt Danh hiệu “Tập thể
Xuất sắc” sẽ được tặng Giấy khen của Hiệu trưởng Nhà trường và tiền thưởng theo quy định
hiện hành của Đại học Quốc gia Hà Nội và của Trường Đại học Công nghệ.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2bca666166fffae23a866d51abb47b6c5e23c7bb02410db0ef72562f0f41fad5`.

### human-candidate-0149

**Câu hỏi:** nếu xét tuyển thẳng thạc sĩ trong thông báo thì có phải trả phí không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-f6a40cbdefecdb88cc89`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `708b73adbabf3aaf60a398c6cda0bf446063118db7f5961db8774c3363ed80e3`.

### human-candidate-0150

**Câu hỏi:** không phải đi thi mà tuyển thẳng cao học trong thông báo thì vẫn nộp tiền hả

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-f6a40cbdefecdb88cc89`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ffca51e79e3a9a90279f31b3e6595aac65a87221335ac4f24cbb07c0b0f184da`.

### human-candidate-0151

**Câu hỏi:** diện nhận thẳng vào cao học trong thông báo có được miễn khoản tiền dự tuyển không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-f6a40cbdefecdb88cc89`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 5**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p5_s33_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: ĐĂNG KÝ DỰ THI, THỜI GIAN THI VÀ LỆ PHÍ > 6.3. Lệ phí | Page: 5]

6.3. Lệ phí
-
Lệ phí: 420.000đ/thí sinh (áp dụng cho cả thí sinh xét tuyển thẳng).
-
Phương thức nộp tiền: thí sinh có thể chuyển lệ phí tuyển sinh theo quy định vào tài
khoản của Trường Đại học Công nghệ hoặc nộp trực tiếp bằng tiền mặt tại Trường
Đại học Công nghệ.
-
Thông tin chuyển tiền:
+  Tên Tài khoản: Trường Đại học Công nghệ - ĐHQGHN
+
Số TK: 21510000214781 tại Ngân hàng BIDV Cầu Giấy, Hà Nội
+  Nội dung chuyển khoản: Mã ĐKDT_Họ tên thí sinh_TS SĐH đợt 2_2022.
-
Địa chỉ nộp tiền mặt: P.101A – Phòng Kế hoạch Tài chính – Trường Đại học Công
nghệ - ĐHQGHN – Nhà E3, 144 Xuân Thủy, Cầu Giấy, Hà Nội.
7.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `93e3c87d95c2eca673f3d73f5cdd1eca3a8c9a3c1d578cff2405196b2eb1b435`.

### human-candidate-0152

**Câu hỏi:** chưa có chứng chỉ ngoại ngữ lúc đăng ký cao học trong thông báo thì được bổ sung sau không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-e8ab114bb11c67ef7330`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 2**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p2_s10_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: CÁC CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ CHUẨN > 1.3. Điều kiện về năng lực ngoại ngữ | Page: 2]

1.3. Điều kiện về năng lực ngoại ngữ
-
Có bằng tốt nghiệp đại học, thạc sĩ, tiến sĩ được đào tạo toàn thời gian ở nước ngoài
bằng ngoại ngữ phù hợp với yêu cầu của chương trình đào tạo, được cơ quan có
thẩm quyền công nhận văn bằng theo quy định hiện hành.
-
Bằng tốt nghiệp trình độ đại học trở lên ngành ngôn ngữ nước ngoài, ngành sư
phạm ngôn ngữ nước ngoài hoặc bằng tốt nghiệp trình độ đại học trở lên mà các học
phần thuộc khối kiến thức cơ sở và chuyên ngành được thực hiện bằng ngôn ngữ
nước ngoài;
-
Bằng tốt nghiệp trình độ đại học trở lên do các đơn vị đào tạo trong ĐHQGHN cấp
trong thời gian không quá 2 năm có chuẩn đầu ra về ngoại ngữ đáp ứng yêu cầu về
năng lực ngoại ngữ để dự tuyển CTĐT thạc sĩ và thí sinh đã có chứng chỉ ngoại ngữ
đáp ứng chuẩn đầu ra trước khi tốt nghiệp CTĐT trình độ đại học;
-
Một trong các chứng chỉ ngoại ngữ đạt trình độ tương đương Bậc 3 trở lên theo
Khung năng lực Ngoại ngữ 6 bậc dùng cho Việt Nam và được ĐHQGHN công
nhận (phụ lục 1 và phụ lục 2), còn hiệu lực tính đến ngày đăng ký dự tuyển.
Ghi chú: Thí sinh có thể được nợ minh chứng về năng lực ngoại ngữ và được bổ
sung trước thời điểm Nhà trường ra quyết định trúng tuyển. Thời gian dự kiến tháng
11/2022.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `34b4bbf3fed677df8e688f2effdfe88d4d2b574e45e0af020632115937dbc6bb`.

### human-candidate-0153

**Câu hỏi:** nếu nhiều công trình và giải thưởng cùng đủ điều kiện thì tuyển thẳng cao học có chặn trần điểm cộng không

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7bd487e2a33f91e366dc`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s15_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.1. XÉT TUYỂN THẲNG > 2.1.2. Điểm thưởng thành tích nghiên cứu khoa học | Page: 3]

2.1.2. Điểm thưởng thành tích nghiên cứu khoa học
-  Đối với công trình nghiên cứu khoa học sinh viên:
+ Đạt giải thưởng cấp ĐHQGHN hoặc cấp Bộ Giáo dục và Đào tạo: giải nhất: 0.2
điểm, giải nhì 0.15 điểm, giải ba 0.1 điểm, giải khuyến khích 0.07 điểm.
+ Đạt giải thưởng cấp trường hoặc cấp khoa trực thuộc: giải nhất 0.1 điểm, giải nhì
````

</details>

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e676e27c98257df21fb70b07bf79eaeae56aca490b07e883c2c2e7ea2307ba33`.

### human-candidate-0154

**Câu hỏi:** mức trần cộng điểm từ thành tích khoa học trong diện vào thẳng cao học là gì

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-7bd487e2a33f91e366dc`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s15_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.1. XÉT TUYỂN THẲNG > 2.1.2. Điểm thưởng thành tích nghiên cứu khoa học | Page: 3]

2.1.2. Điểm thưởng thành tích nghiên cứu khoa học
-  Đối với công trình nghiên cứu khoa học sinh viên:
+ Đạt giải thưởng cấp ĐHQGHN hoặc cấp Bộ Giáo dục và Đào tạo: giải nhất: 0.2
điểm, giải nhì 0.15 điểm, giải ba 0.1 điểm, giải khuyến khích 0.07 điểm.
+ Đạt giải thưởng cấp trường hoặc cấp khoa trực thuộc: giải nhất 0.1 điểm, giải nhì
````

</details>

**Gold: D01, trang 3**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p3_s16_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 0.07 điểm, giải ba 0.05 điểm. | Page: 3]

0.07 điểm, giải ba 0.05 điểm.
-  Đối với bài báo khoa học đăng ở tạp chí ISI: 0.3 điểm; bài báo đăng trên tạp chí
Scopus/quốc tế khác: 0.2 điểm; bài báo đăng trên kỷ yếu Hội nghị, hội thảo khoa học
cấp quốc tế/quốc gia: 0.15 điểm.
-  Sinh viên có nhiều thành tích thì được tích lũy điểm thưởng nhưng không quá 0.5
điểm.
Ghi chú: Điểm thưởng về thành tích nghiên cứu khoa học có thể được cộng thêm vào
điểm trung bình chung tích lũy toàn khóa của thí sinh để xét tuyển thẳng.
Thí sinh có bằng tốt nghiệp loại Khá nếu có thành tích nghiên cứu khoa học có thể
nộp hồ sơ xét tuyển thẳng nếu điểm xét tuyển thẳng = điểm trung bình chung tích lũy
bậc đại học + điểm thành tích nghiên cứu khoa học ≥ 3.2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `1551e4779978d4052a5ba34bfd018a556b391033746f4b5184c1c6e8672b6ce5`.

### human-candidate-0155

**Câu hỏi:** direct admission review dates và result date master trong thông báo là khi nào

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D01. Filters: `{}`.
Nhóm: `family-fa8ab7404ea45210a57a`. Exposure: `known_exposed_dev`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s20_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022 | Page: 4]

2.1.6. Thời gian xét tuyển thẳng: từ ngày 05/09/2022 ÷ 08/09/2022
````

</details>

**Gold: D01, trang 4**, `242faf4504a48503dce8821b53e5ae6b909a370725062a2855886b8593c34a59_p4_s21_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: regulation | Academic years: 2014, 2018, 2019, 2020, 2021, 2022, 2023 | Institution: ĐẠI HỌC QUỐC GIA HÀ NỘI | Program: Kỹ thuật phần mềm | Section: PHƯƠNG THỨC TUYỂN SINH > 2.14. Thời gian thu nhận hồ sơ > 2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022 | Page: 4]

2.1.7. Thời gian thông báo kết quả: ngày 09/09/2022
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d9a23743cc14079c57265b94e85f639da0f18003d4cb58dc0f1419818878456f`.

### human-candidate-0156

**Câu hỏi:** môn EMA2036E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 3**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p3_s44_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2036E | Pages: 3-4]

EMA2036E
STT
Mã học
phần
Học phần
Số
tín
chỉ
Số giờ tín chỉ
Mã số
học phần
tiên quyết
Lí
thuyế
t
Thực
hành
Tự
học
Engineering Mechanics 2
23.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `8e032e89109db092e2b5342e5e76dd0386d17381c743148be93807cfccfe8518`.

### human-candidate-0157

**Câu hỏi:** môn MAT1041 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 5**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p5_s93_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1041 | Pages: 5-6]

MAT1041
STT
Mã học
phần
Học phần
Số
tín
chỉ
Số giờ tín chỉ
Mã số
học phần
tiên quyết
Lí
thuyế
t
Thực
hành
Tự
học
43.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `294d3daa017efecf1e78007086349819466d69961dc0f10be4585b4034795f67`.

### human-candidate-0158

**Câu hỏi:** môn EMA3071E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 14**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p14_s353_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3071E | Page: 14]

EMA3071E
Ứng dụng máy tính trong đo
lường và điều khiển *
Computer Applications in
Measurement and Control
3
30
15
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `af2ae2acf965feb6524ac48e16733c960cc0489730b0ee134a9de175dd8b28a3`.

### human-candidate-0159

**Câu hỏi:** môn EMA3005E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 7**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p7_s150_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3005E | Page: 7]

EMA3005E
Công nghệ chế tạo máy *
Machinery Manufacturing
Technology
3
39
6
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e1ff4251da0edcdaa9a79a623036bab86204e7a8c9ed3818514149261d64bf67`.

### human-candidate-0160

**Câu hỏi:** môn EMA3143 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 9**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p9_s208_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3143 | Page: 9]

EMA3143
Đồ án 01: Đồ án chuyên
ngành Cơ điện tử 1 ***
Project 01: Specialized
subject of mechatronics 1
2
15
15
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `ca4ef98a724eb60d33c79c54b29c7bc14876387dab0687f83538dfea972bdb03`.

### human-candidate-0161

**Câu hỏi:** môn MAT1042 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 3**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p3_s29_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: MAT1042 | Page: 3]

MAT1042
Giải tích 2
Analytics 2
4
30
30
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a68806b590e78705e2a1acb69f45b0977f798c89ebaedde9efb63f9a217219f3`.

### human-candidate-0162

**Câu hỏi:** môn EMA3086 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 11**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p11_s255_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3086 | Page: 11]

EMA3086
Các vật liệu cho công nghệ
MEMS và NEMS
Materials for NEMS and
MEMS Technology
2
30
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `5c91fef3ee4418a9f5586fc9c7f28bc09f8ffdf7eb445e49c7a8b08ba43c0ebd`.

### human-candidate-0163

**Câu hỏi:** môn EMA2026 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 4**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p4_s73_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2026 | Pages: 4-5]

EMA2026
STT
Mã học
phần
Học phần
Số
tín
chỉ
Số giờ tín chỉ
Mã số
học phần
tiên quyết
Lí
thuyế
t
Thực
hành
Tự
học
Digital Techniques
33.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f54894885ab95004c9eba9deddc128c81b2c1e68ff0f69c6cfc6d29db0c08298`.

### human-candidate-0164

**Câu hỏi:** môn EMA2011 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 13**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p13_s328_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2011 | Pages: 13-14]

EMA2011
STT
Mã học
phần
Học phần
Số
tín
chỉ
Số giờ tín chỉ
Mã số
học phần
tiên quyết
Lí
thuyế
t
Thực
hành
Tự
học
109.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `7a766e0bcd504cf0346c09887c8a840df0830e7c835ff8ea353dbe793522f089`.

### human-candidate-0165

**Câu hỏi:** môn INT2013 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 11**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p11_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: INT2013 | Page: 11]
Table headers: STT | Mã học
phần | Học phần | Số
tín
chỉ | Số giờ tín chỉ | Mã số
học phần
tiên quyết

{"headers": ["STT", "Mã học\nphần", "Học phần", "Số\ntín\nchỉ", "Số giờ tín chỉ", "", "", "Mã số\nhọc phần\ntiên quyết"], "rows": [["", "", "", "", "Lí\nthuyế\nt", "Thực\nhành", "Tự\nhọc", ""], ["87.", "INT3401", "Trí tuệ nhân tạo ***\nArtificial Intellegence", "3", "45", "", "", ""], ["88.", "EMA3143", "Đồ án 01: Đồ án chuyên\nngành Cơ điện tử 1 ***\nProject 01: Specialized\nsubject of mechatronics 1", "2", "15", "15", "", "EMA3135"], ["V.3.4.2.", "", "Các học phần tự chọn", "8/12", "", "", "", ""], ["89.", "EMA3116E", "Kỹ thuật thuỷ khí *\nHydraulics and Pneumatics\nTechniques", "3", "30", "15", "", "EPN1095\nEPN1096"], ["90.", "EMA2028", "Nhập môn công nghệ vi cơ\nđiện tử\nIntroduction to\nMicromechatronics", "2", "30", "", "", "EMA2026\nINT2013"], ["91.", "EMA3086", "Các vật liệu cho công nghệ\nMEMS và NEMS\nMaterials for NEMS and\nMEMS Technology", "2", "30", "", "", "EPN1095\nEPN1096"], ["92.", "ELT3093", "Ứng dụng MEMS trong Điện\ntử Viễn thông\nMEMS Applications in\nTelecommunication", "2", "30", "", "", "EMA2027E\nEMA2028\nEMA2006E"], ["93.", "EMA3071E", "Ứng dụng máy tính trong đo\nlường và điều khiển *\nComputer Applications in\nMeasurement and Control", "3", "30", "15", "", "EMA2013\nINT2013"], ["V.3.5.", "", "Khối kiến thức định hướng\nchuyên sâu về Kỹ thuật robot", "34", "", "", "", ""], ["V.3.5.1.", "", "Các học phần bắt buộc", "19", "", "", "", ""], ["94.", "EMA3087E", "Mô phỏng và thiết kế robot *\nRobot - Simulation and\nDesign", "3", "25", "20", "", "MAT1093\nMAT1041\nMAT1042\nEPN1095"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `68b1602c9a5bdd9048ee9fbfdeb031d06440712219d52536a208c1a78766ee08`.

### human-candidate-0166

**Câu hỏi:** môn INT2208 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 5**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p5_s88_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: INT2208 | Page: 5]

INT2208
Công nghệ phần mềm
Software Technology
3
45
41.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2c6e47e253983593a269b5739e37b9ac39f624a41ff1fca42077ff29d890108e`.

### human-candidate-0167

**Câu hỏi:** môn EMA3062E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 8**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p8_s156_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3062E | Page: 8]

EMA3062E
Điều khiển PLC *
PLC Programming
3
25
20
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `287494616adc5c1de128328fe863196b8272290ff968388b1466639e3fedb464`.

### human-candidate-0168

**Câu hỏi:** môn EMA3084E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 10**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p10_s230_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3084E | Page: 10]

EMA3084E
Vi xử lý và vi điều khiển *
Microprocessors and
Microcontrollers
3
25
20
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `d2f62262be0f6de4e747f59c57319393dd19f96e5e0d6ffc98ab131b057154e4`.

### human-candidate-0169

**Câu hỏi:** môn EMA2019E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 13**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p13_s301_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2019E | Page: 13]

EMA2019E
Vật liệu chức năng *
Functional Materials
2
30
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `88b4a40cffd7a9c9a15f7ec594f751d5250fe8d99945849f09ca6dd01e4e08e5`.

### human-candidate-0170

**Câu hỏi:** môn EMA2028 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 7**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p7_s143_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA2028 | Page: 7]

EMA2028
Nhập môn công nghệ vi cơ
điện tử
Introduction to
Micromechatronics
2
30
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `e1101ee5706710a87774ae4863f76a0c07f0db789d5fede0ce2933199c444288`.

### human-candidate-0171

**Câu hỏi:** môn EMA3114E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 12**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p12_s282_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3114E | Page: 12]

EMA3114E
Vi điều khiển và hệ thống
nhúng *
Microcontrollers and
Embedded Systems
3
30
15
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `db908170b797683b9b46e22ecb40e2b93885b2a4b2de29bcdbe19e1d2cac9dbb`.

### human-candidate-0172

**Câu hỏi:** môn INT1006 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 2**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p2_s18_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: INT1006 | Page: 2]

INT1006
Tin học cơ sở 4
Introduction to Informatics 4
3
20
23
2
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `784f8eb8fd56f1098dc22adcc7a3a3d762a47129064d1efd9abe9d7967cdf17f`.

### human-candidate-0173

**Câu hỏi:** môn ELT3093 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 11**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p11_s258_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: ELT3093 | Page: 11]

ELT3093
Ứng dụng MEMS trong Điện
tử Viễn thông
MEMS Applications in
Telecommunication
2
30
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `6eb26736deb795d9b5b94d0b949ee015dff8eec177fb996a0d07a1895d7808d6`.

### human-candidate-0174

**Câu hỏi:** môn EMA3002E trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 14**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p14_s338_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3002E | Page: 14]

EMA3002E
Chẩn đoán âm học máy *
Acoustic Diagnostic
2
20
10
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `f3959158d7528e56ab100d6ff683153bbf2f8f0572ffff7ccddbc4baae76a798`.

### human-candidate-0175

**Câu hỏi:** môn ELT2028 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 5**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p5_s87_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: ELT2028 | Page: 5]

ELT2028
Chuyên nghiệp trong công
nghệ
Professional in Technology
2
30
40.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `a952be030795bdaedb704254e6c2f5a578a371961fac58d568cddf03ad6ce034`.

### human-candidate-0176

**Câu hỏi:** môn PHI1004 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 2**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p2_s10_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: PHI1004 | Page: 2]

PHI1004
Những nguyên lý cơ bản của
chủ nghĩa Mác – Lênin 1
Fundamental Principles of
Marxism-Leninism 1
2
24
6
2.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `2247808ca4400c6db06b698446c268b04918431349cd7fcff1415be8fd7829d0`.

### human-candidate-0177

**Câu hỏi:** môn EMA3135 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `medium`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 7**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p7_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA3135 | Page: 7]
Table headers: STT | Mã học
phần | Học phần | Số
tín
chỉ | Số giờ tín chỉ | Mã số
học phần
tiên quyết

{"headers": ["STT", "Mã học\nphần", "Học phần", "Số\ntín\nchỉ", "Số giờ tín chỉ", "", "", "Mã số\nhọc phần\ntiên quyết"], "rows": [["", "", "", "", "Lí\nthuyế\nt", "Thực\nhành", "Tự\nhọc", ""], ["51.", "EMA3071E", "Ứng dụng máy tính trong đo\nlường và điều khiển *\nComputer based Control and\nMeasurement", "3", "30", "15", "", "EMA2013\nINT2013"], ["52.", "EMA3116E", "Kỹ thuật thuỷ khí *\nHydrolics and Pneumatics\nEngineering", "3", "30", "15", "", "MAT1083\nMAT1084"], ["53.", "EMA3064E", "Điều khiển điện, thuỷ khí *\nElectrohydrolic Control", "2", "24", "6", "", "EMA2013\nEMA2026"], ["54.", "INT3017E", "Lập trình C *\nC Programming", "2", "20", "10", "", "INT1003\nINT1006"], ["55.", "EMA3033E", "Mô phỏng và thiết kế hệ cơ\nđiện tử\nSimulation and Design\nMechatronic Systems", "3", "30", "15", "", "MAT1093\nMAT1041\nMAT1042\nEPN1095\nELT2050E"], ["56.", "EMA2028", "Nhập môn công nghệ vi cơ\nđiện tử\nIntroduction to\nMicromechatronics", "2", "30", "", "", "EMA2026\nINT2013"], ["57.", "EMA2019E", "Vật liệu chức năng\nFunctional Materials", "2", "30", "", "", "EPN1095\nEPN1096"], ["V.3.2.", "Khối kiến thức định hướng chuyên sâu về\nChế tạo thiết bị", "", "34", "", "", "", ""], ["V.3.2.1", "", "Các học phần bắt buộc", "19", "", "", "", ""], ["58.", "EMA3005E", "Công nghệ chế tạo máy *\nMachinery Manufacturing\nTechnology", "3", "39", "6", "", "EMA2033\nEMA2022E"], ["59.", "EMA3035E", "Máy công cụ - CNC *\nCNC Machines", "3", "30", "15", "", ""], ["60.", "EMA3004", "Công nghệ CAD/CAM/CNC", "2", "18", "12", "", "EMA2032E"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `8730989a06da5856d5dd87cb304aa03329bc96e7c3dc1d9057875cb1843622ba`.

### human-candidate-0178

**Câu hỏi:** môn FLF2103 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `hard`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 3**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p3_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: FLF2103 | Page: 3]
Table headers: STT | Mã học
phần | Học phần | Số
tín
chỉ | Số giờ tín chỉ | Mã số
học phần
tiên quyết

{"headers": ["STT", "Mã học\nphần", "Học phần", "Số\ntín\nchỉ", "Số giờ tín chỉ", "", "", "Mã số\nhọc phần\ntiên quyết"], "rows": [["", "", "", "", "Lí\nthuyế\nt", "Thực\nhành", "Tự\nhọc", ""], ["11.", "", "Giáo dục thể chất\nPhysical education", "4", "", "", "", ""], ["12.", "", "Giáo dục quốc phòng - an ninh\nNational Defence Education", "8", "", "", "", ""], ["13.", "", "Kĩ năng bổ trợ\nSoft skills", "3", "", "", "", ""], ["II", "", "Khối kiến thức theo lĩnh vực", "16", "", "", "", ""], ["14.", "MAT1093", "Đại số\nAlgebra", "4", "30", "30", "", ""], ["15.", "MAT1041", "Giải tích 1\nAnalytics 1", "4", "30", "30", "", ""], ["16.", "MAT1042", "Giải tích 2\nAnalytics 2", "4", "30", "30", "", "MAT1041"], ["17.", "EPN1095", "Vật lý đại cương 1\nGeneral Physics 1", "2", "30", "", "", ""], ["18.", "EPN1096", "Vật lý đại cương 2\nGeneral Physics 2", "2", "30", "", "", "EPN1095"], ["III", "", "Khối kiến thức theo khối\nngành", "6", "", "", "", ""], ["19.", "EMA2050", "Xác suất thống kê ứng dụng\nApplied Probability and\nStatistic", "3", "30", "15", "", "MAT1093\nMAT1042"], ["20.", "EMA2011", "Phương pháp tính trong kỹ\nthuật\nComputational Methods for\nEngineering", "3", "30", "15", "", "INT1006\nMAT1093\nMAT1042"], ["IV", "", "Khối kiến thức theo nhóm\nngành", "25", "", "", "", ""], ["21.", "EMA2036E", "Cơ học kỹ thuật 1 *\nEngineering Mechanics 1", "3", "30", "15", "", "MAT1093\nMAT1042"], ["22.", "EMA2037E", "Cơ học kỹ thuật 2 *", "3", "30", "15", "", "EMA2036E"]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `19aac4c08ab2f8b84a57e9258686783d681d0a2df2fe35bec24a23be94f5fa7f`.

### human-candidate-0179

**Câu hỏi:** môn EPN1096 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 12**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p12_s300_c1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EPN1096 | Pages: 12-13]

EPN1096
STT
Mã học
phần
Học phần
Số
tín
chỉ
Số giờ tín chỉ
Mã số
học phần
tiên quyết
Lí
thuyế
t
Thực
hành
Tự
học
Techniques
103.
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `8f654666ecb2e8fe59c919d0a7badd07d5c09446e7a5b7f7e847a29ffa8f8ccd`.

### human-candidate-0180

**Câu hỏi:** môn EMA4002 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?

Nhãn hiện có: positive; `easy`; hành vi `answer_grounded`.
Scope hiện có: D07. Filters: `{}`.
Nhóm: `family-f750befa59ae648ef4b1`. Exposure: `unknown_pending_history_audit`.
Author alias gốc: `LEGION`; đối chiếu tác giả và ghi reviewer role `project_owner` hoặc `independent_reviewer`: **chờ duyệt**.

**Gold: D07, trang 15**, `c64064b1854fe6e98b3278d038e6b1aa03356d00483caa18194e6215e6654850_p15_t1`.

<details><summary>Nội dung chunk đầy đủ để đối chiếu</summary>

````text
[Document type: curriculum | Academic years: 2001, 2002, 2006, 2011, 2012, 2013, 2019, 2021, 2022, 2023, 2024, 2026, 2027, 2028, 2032, 2033, 2036, 2037, 2041, 2050 | Program: 155 tín chỉ | Section: EMA4002 | Page: 15]
Table headers: STT | Mã học
phần | Học phần | Số
tín
chỉ | Số giờ tín chỉ | Mã số
học phần
tiên quyết

{"headers": ["STT", "Mã học\nphần", "Học phần", "Số\ntín\nchỉ", "Số giờ tín chỉ", "", "", "Mã số\nhọc phần\ntiên quyết"], "rows": [["", "", "", "", "Lí\nthuyế\nt", "Thực\nhành", "Tự\nhọc", ""], ["", "", "Practices", "", "", "", "", ""], ["119.", "EMA4001", "Thực tập kỹ thuật\nEngineering Practices", "5", "", "75", "", "EMA4002"], ["V.5", "", "Khóa luận tốt nghiệp/các học\nphần thay thế khóa luận tốt\nnghiệp", "10", "", "", "", ""], ["120.", "EMA4051", "Khoá luận tốt nghiệp **\nThesis", "10", "", "", "", ""], ["121.", "", "Các học phần tương đương\n(10 tín chỉ từ danh sách các\nhọc phần lựa chọn trong khối\nkiến thức chuyên sâu)", "10", "", "", "", ""], ["Tổng cộng", "", "", "155", "", "", "", ""]]}
````

</details>

**Quyết định:** [ ] duyệt [ ] cần sửa [ ] loại; reviewer: ____; role (`project_owner` / `independent_reviewer`): ____; thời điểm có timezone: ____.
Scope/hành vi xác nhận: ____; chỉnh nhãn/gold/context (nếu có): ____; lý do/evidence: ____.
Gold claims cần câu trả lời đáp ứng (số/đơn vị/năm/điều kiện/hop và chunk hỗ trợ): ____.
Bảy tiêu chí: tự nhiên; answerability; đủ evidence; phạm vi tài liệu/thời gian; độ khó; leakage; hành vi mong đợi.

Binding record: `0ecebfaaa66f8891e9a3540c5a174bce854a098b0c32c3e36792c92f81504d12`.

