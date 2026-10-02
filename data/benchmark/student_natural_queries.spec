# AI authored. Six deliberately different surface forms per intent.
# @intent|document alias or none|frozen item indices|difficulty|normalized intent query|expected answer / missing evidence reason
# category|query[|normalized override][|previous user message for contextual follow-up]
@scholarship_gpa_requirement|none||medium|GPA bao nhiêu thì được học bổng khuyến khích học tập?|Corpus chưa có quy định ngưỡng GPA học bổng khuyến khích học tập; không dùng điều kiện khen thưởng thay thế.
abbreviation|gpa bn thì đc hb
colloquial|muốn lấy học bổng thì điểm phải cỡ nào vậy
code_switching|minimum GPA để get scholarship là bn
typo|điêm trung binh bao nhieu thi dc hoc bong
lexical_mismatch|điểm tích lũy phải chạm mốc nào mới có tiền hỗ trợ học tập
unanswerable|trường có quy định GPA tối thiểu để nhận học bổng khuyến khích học tập không
@scholarship_failed_course|none||hard|Rớt một môn có làm mất điều kiện học bổng khuyến khích học tập không?|Thiếu quy định học bổng và loại học bổng; không suy từ quy định danh hiệu sinh viên.
slang|rớt môn có bay học bổng ko
abbreviation|1 môn F thì còn xét hb kkht đc k
conditional|nếu điểm tổng em vẫn cao nhưng có một môn không đạt thì học bổng khuyến khích học tập tính sao
code_switching|failed one subject thì scholarship eligibility còn không
colloquial|em tạch một môn thôi á, suất học bổng có bị mất luôn không
unanswerable|quy định nào nói một môn F ảnh hưởng học bổng khuyến khích học tập thế nào
@academic_warning_low_gpa|none||hard|Điểm thấp đến mức nào thì bị cảnh báo học vụ?|Trích quy chế 2014 chỉ có kỷ luật phòng thi, không có ngưỡng cảnh báo học vụ do GPA.
colloquial|điểm thấp quá có bị trường cảnh cáo không
slang|gpa tụt sml thì có dính cảnh báo học vụ k
abbreviation|gpa bn là cbhv vậy
lexical_mismatch|học lực xuống mức nào thì trường gửi thông báo cảnh báo về kết quả học tập
typo|diem thap qua co bi canh bao hoc vu ko
unanswerable|cho em xin ngưỡng GPA khiến sinh viên bị cảnh báo học vụ
@failed_two_courses_consequence|none||hard|Rớt hai môn trong học kỳ thì có bị cảnh báo học vụ không?|Không có quy định số môn rớt và cảnh báo học vụ trong corpus.
slang|kì này tạch 2 môn thì có bị sao không
conditional|nếu em rớt hai môn nhưng GPA còn 2.5 thì có bị cảnh báo không|Rớt hai môn nhưng GPA 2,5 có bị cảnh báo học vụ không?
abbreviation|fail 2 môn/kì => cbhv k
code_switching|two failed courses in a semester có academic warning không
long_noisy|huhu em vừa xem điểm xong hai môn đều không qua, còn những môn khác cũng tạm ổn, giờ em lo không biết trường có cảnh báo học vụ chỉ vì rớt hai môn không
unanswerable|trường quy định thế nào về cảnh báo học vụ khi sinh viên không đạt hai học phần trong kỳ
@minimum_credits_per_semester|none||medium|Mỗi học kỳ phải đăng ký tối thiểu bao nhiêu tín chỉ?|Corpus chưa có quy định khối lượng đăng ký tối thiểu theo học kỳ; không lấy tổng tín chỉ chương trình làm ngưỡng học kỳ.
paraphrase|mỗi kì phải học tối thiểu bao nhiêu tín
abbreviation|1 kỳ đăng kí ít nhất bn tín vậy
implicit_intent|kì này em muốn học ít môn cho nhẹ thì mức ít nhất được phép là bao nhiêu
code_switching|minimum credits per semester là bao nhiêu
conditional|được đăng ký có 8 tín không|Đăng ký 8 tín chỉ trong một học kỳ có được không?
long_noisy|em định bớt môn kỳ này vì đang đi làm, chỉ chọn 2 môn thôi nhưng không rõ có vi phạm mức tín chỉ tối thiểu không, cho em hỏi quy định với|Đăng ký hai môn trong một học kỳ có vi phạm quy định tín chỉ tối thiểu không?
@maximum_credits_with_failed_course|none||hard|GPA 2,1 và có một môn F thì có được đăng ký 20 tín chỉ không?|Không có quy định tải học tập theo GPA và học phần F trong corpus.
conditional|nếu GPA 2.1 mà có 1 môn F thì đăng kí 20 tín được không
abbreviation|gpa 2.1 + 1F, dk 20tc ok k
code_switching|GPA 2.1 with one F có register 20 credits được không
colloquial|điểm tích lũy em 2 phẩy 1, rớt một môn, kỳ tới ôm 20 tín có được phép không
slang|2.1 gpa dính 1 F mà muốn cày 20 tín thì có bị chặn k
long_noisy|em đang tính đăng ký kỳ sau, tổng em muốn học là 20 tín nhưng GPA hiện chỉ 2.1 và bảng điểm còn một môn F chưa học lại, hệ thống có cho em đăng ký vậy không
@retake_vs_grade_improvement|none||medium|Học lại và học cải thiện điểm khác nhau thế nào?|Corpus chưa có quy định học lại hoặc học cải thiện và cách tính điểm tương ứng.
paraphrase|học lại với học cải thiện khác nhau thế nào
colloquial|qua môn rồi đăng ký học lại thì tính là cải thiện hả
abbreviation|hl vs hct khác j vậy
code_switching|retake với grade improvement có giống nhau không
lexical_mismatch|học để xóa điểm không đạt với học để nâng điểm đã qua có khác quy chế không
unanswerable|khi học cải thiện thì điểm cũ được thay hay cả hai lần đều tính|Khi học cải thiện điểm, điểm mới thay điểm cũ hay tính cả hai lần?
@attendance_exam_eligibility|none||hard|Nghỉ học nhiều có bị cấm thi và ngưỡng vắng học là bao nhiêu?|Không có quy định chuyên cần/cấm thi do vắng lớp trong corpus; khác đình chỉ thi vì gian lận.
colloquial|cho mình hỏi kiểu nếu nghỉ học nhiều quá thì có bị cấm thi không
slang|cúp học mấy buổi là hết slot thi vậy
abbreviation|vắng bn % thì ko đc thi
code_switching|low attendance có bị ban khỏi final exam không
implicit_intent|em nghỉ mấy tuần rồi, muốn biết còn được vào thi cuối kỳ không|Nghỉ học vài tuần có còn được thi cuối kỳ không?
long_noisy|em đi làm ca tối nên có nghỉ khá nhiều buổi học, giờ gần thi rồi mà bạn bảo nghỉ quá số buổi là cấm thi, tài liệu trường nói ngưỡng nào vậy
@english_requirement_cohort_2025|none||hard|Sinh viên khóa 2025 phải áp dụng chuẩn tiếng Anh theo quy định nào?|Các chương trình 2023/2019 và thông báo thạc sĩ 2022 không chứng minh chuẩn tiếng Anh cho mọi ngành khóa 2025; cần ngành và văn bản áp dụng.
colloquial|mình khóa 2025 thì chuẩn tiếng Anh áp dụng theo quy định nào
abbreviation|k2025 cần TA bậc mấy để ra trường
code_switching|cohort 2025 English exit requirement theo policy nào vậy
typo|khoa 2025 chuan tieng ah ra truong ntn
conditional|nếu em nhập học năm 2025 thì dùng chuẩn tiếng Anh của văn bản 2023 luôn được không|Sinh viên nhập học 2025 có mặc nhiên áp dụng chuẩn tiếng Anh của văn bản 2023 không?
unanswerable|bộ tài liệu mình gửi có quy định chuẩn tiếng Anh áp dụng chung toàn bộ khóa tuyển 2025 không
@graduation_gpa_requirement|none||medium|GPA tối thiểu để tốt nghiệp đại học là bao nhiêu?|Corpus chưa có ngưỡng GPA tốt nghiệp áp dụng chung; không suy từ tiêu chí khen thưởng hoặc số tín chỉ chương trình.
code_switching|minimum GPA để graduate là bao nhiêu
abbreviation|gpa bn mới đc tn
colloquial|điểm tích lũy phải được mấy chấm mới ra trường vậy
implicit_intent|em đang xem điều kiện ra trường, phần điểm trung bình cần tới mức nào
typo|diem trung binh tot nghiep toi thieu bao nhiu
unanswerable|cho em ngưỡng điểm trung bình toàn khóa tối thiểu để được xét tốt nghiệp
@unspecified_credit_question|none||hard|Bạn đang hỏi số tín chỉ để đăng ký học kỳ, tốt nghiệp hay một học phần?|Thiếu đối tượng và mục đích của câu hỏi số tín chỉ.
ambiguous|bao nhiêu tín thì được|Bao nhiêu tín chỉ thì được?
ambiguous|bn tc là đủ vậy|Bao nhiêu tín chỉ là đủ?
ambiguous|mấy tín nhỉ|Mấy tín chỉ?
ambiguous|credits cần bao nhiêu|Cần bao nhiêu tín chỉ?
ambiguous|thế tổng là mấy|Vậy tổng là bao nhiêu?
ambiguous|ủa ít nhất bao nhiêu tín mới ok|Ít nhất bao nhiêu tín chỉ mới được?
@contextless_second_year_followup|none||hard|Sinh viên năm hai được áp dụng điều kiện nào? Cần biết chủ đề trước đó.|Thiếu hội thoại trước và chủ đề: học bổng, tín chỉ, học phí hay quy định khác.
ambiguous|thế sinh viên năm 2 thì sao|Vậy sinh viên năm hai thì sao?
ambiguous|năm hai có khác ko|Sinh viên năm hai có khác không?
ambiguous|còn sv năm 2|Còn sinh viên năm hai thì sao?
ambiguous|what about second-year students|Sinh viên năm hai thì sao?
ambiguous|vậy n2 áp dụng kiểu gì|Vậy năm hai áp dụng thế nào?
ambiguous|em năm hai thì có được không|Em học năm hai thì có được không?
@unspecified_eligibility|none||hard|Cần biết bạn đang xin xét điều kiện gì và có dữ liệu cá nhân nào.|Không đủ ngữ cảnh để quyết định điều kiện cá nhân.
ambiguous|mình có đủ điều kiện ko|Mình có đủ điều kiện không?
ambiguous|vậy em được chứ|Vậy em có được không?
ambiguous|case t thì sao|Trường hợp của tôi thì sao?
ambiguous|am I eligible vậy|Tôi có đủ điều kiện không?
ambiguous|như của mình thì ok không bạn|Trường hợp của mình có được không?
ambiguous|tính vậy em có bị gì không|Như vậy em có bị ảnh hưởng gì không?
@unspecified_english_certificate|none||hard|Cần biết chương trình, khóa tuyển và chứng chỉ ngoại ngữ muốn đối chiếu.|Không thể xác định điều kiện chứng chỉ cho chương trình không được nêu.
ambiguous|bằng này có dùng được không|Bằng này có dùng được không?
ambiguous|ielts này đủ chưa|Chứng chỉ IELTS này có đủ không?
ambiguous|cert này trường nhận k|Trường có nhận chứng chỉ này không?
ambiguous|cái tiếng Anh đó còn hạn không|Chứng chỉ tiếng Anh đó còn thời hạn không?
ambiguous|mức vậy có qua chuẩn chưa bạn|Mức đó đã đạt chuẩn chưa?
ambiguous|nộp cái chứng chỉ kia được chứ|Có được nộp chứng chỉ đó không?
@unspecified_scholarship_or_reward|none||hard|Bạn đang hỏi học bổng khuyến khích học tập hay danh hiệu khen thưởng nào?|Từ học bổng/tiền thưởng và dữ liệu cá nhân chưa đủ rõ; cần phân biệt khen thưởng và học bổng.
ambiguous|được loại giỏi thì tiền đâu|Đạt loại Giỏi thì có khoản tiền nào?
ambiguous|cái thưởng đấy cần bn điểm|Khoản thưởng đó cần bao nhiêu điểm?
ambiguous|hb này là loại nào nhỉ|Học bổng này là loại nào?
ambiguous|có được tiền ko vậy|Có được nhận tiền không?
ambiguous|good grades thì nhận gì|Điểm tốt thì được nhận gì?
ambiguous|mình hỏi vụ hỗ trợ ấy|Mình hỏi về khoản hỗ trợ đó.
@unspecified_course_prerequisite|none||hard|Cần biết học phần và chương trình đào tạo để tra môn tiên quyết.|Thiếu tên hoặc mã học phần và chương trình; không đoán học phần từ lượt trước không có trong dữ liệu.
ambiguous|môn đó cần học gì trước|Môn đó yêu cầu học trước môn nào?
ambiguous|cái này có tiên quyết k|Học phần này có môn tiên quyết không?
ambiguous|prereq của nó là gì|Học phần đó có môn tiên quyết nào?
ambiguous|em học luôn được không|Em có thể học ngay không?
ambiguous|chưa qua môn kia thì sao|Chưa qua môn kia thì sao?
ambiguous|mã đấy bao nhiêu tín ấy|Học phần có mã đó có bao nhiêu tín chỉ?
@masters_interview_date_2022|admission|31|easy|Phỏng vấn thạc sĩ trong thông báo diễn ra ngày nào?|17/09/2022.
paraphrase|lịch phỏng vấn cao học trong thông báo là ngày nào
colloquial|đợt cao học thứ hai thì hôm nào đi phỏng vấn vậy
abbreviation|pv ths trong thông báo ngày bn
typo|phong van thac sy dot 2 ngay nao
code_switching|master interview trong file này when vậy
contextual_followup|thế hôm nào em phải đi phỏng vấn|Phỏng vấn thạc sĩ trong thông báo diễn ra ngày nào?|Em đang xem thông báo tuyển thạc sĩ theo file đang mở.
@masters_application_deadline_2022|admission|17|easy|Hạn đăng ký trực tuyến xét tuyển thẳng thạc sĩ trong thông báo là lúc nào?|17h00 ngày 30/08/2022.
paraphrase|đăng ký online tuyển thẳng thạc sĩ trong thông báo hết hạn lúc nào
abbreviation|xtt ths đ2 chốt đk online bn h
slang|deadline đăng ký tuyển thẳng cao học trong thông báo dí tới ngày nào
typo|han dang ky truc tuyen tuyen thang thac si dot 2 la ngay nao
code_switching|online application deadline for master's direct admission trong thông báo là lúc nào
long_noisy|em vừa up thông báo cao học, đang mở điện thoại trên xe bus nên đọc hơi rối 😵 em tìm mãi không ra giờ đóng đăng ký online diện tuyển thẳng, nhờ xem giúp chính xác ngày và giờ, em sợ lỡ hạn
@masters_fee_2022|admission|32|easy|Lệ phí dự tuyển thạc sĩ trong thông báo là bao nhiêu?|420.000 đồng/thí sinh, kể cả xét tuyển thẳng.
paraphrase|dự tuyển thạc sĩ trong thông báo đóng lệ phí bao nhiêu
colloquial|đợt cao học trong file nộp hồ sơ tốn mấy tiền vậy
abbreviation|lp thi ths trong thông báo bn tiền
code_switching|application fee của master trong thông báo là bao nhiêu
implicit_intent|em tính chuẩn bị tiền đăng ký cao học theo file đang mở, khoản phí hồ sơ cần để ra bao nhiêu
contextual_followup|phải đóng mấy tiền vậy|Lệ phí dự tuyển thạc sĩ trong thông báo là bao nhiêu?|Em muốn đăng ký tuyển thạc sĩ theo file đang mở.
@masters_direct_admission_fee_2022|admission|32|hard|Xét tuyển thẳng thạc sĩ trong thông báo có phải đóng lệ phí không?|Có; mức 420.000 đồng áp dụng cả xét tuyển thẳng.
conditional|nếu xét tuyển thẳng thạc sĩ trong thông báo thì có phải trả phí không
abbreviation|xtt ths trong thông báo có mất lp k
colloquial|không phải đi thi mà tuyển thẳng cao học trong thông báo thì vẫn nộp tiền hả
code_switching|direct admission master's trong thông báo có waive application fee không
lexical_mismatch|diện nhận thẳng vào cao học trong thông báo có được miễn khoản tiền dự tuyển không
long_noisy|em hỏi riêng về thông báo thạc sĩ trong file này nhé, em thuộc diện xét tuyển thẳng chứ không phỏng vấn, vậy khoản lệ phí có được bỏ qua hay vẫn phải đóng
@masters_payment_methods_2022|admission|32|medium|Lệ phí dự tuyển thạc sĩ trong thông báo có thể nộp bằng những cách nào?|Chuyển khoản vào tài khoản trường hoặc nộp tiền mặt tại trường.
paraphrase|lệ phí cao học trong thông báo nộp bằng cách nào
colloquial|đợt thạc sĩ trong thông báo phải mang tiền mặt đến trường à
code_switching|application fee master's trong thông báo can I bank transfer
lexical_mismatch|có cách thanh toán từ xa khoản dự tuyển cao học trong thông báo không
typo|phi du tuyen thac si dot 2 co chuyen khoan dc ko
contextual_followup|chuyển khoản được chứ hay phải tới nộp|Lệ phí dự tuyển thạc sĩ trong thông báo có thể chuyển khoản hay nộp tiền mặt?|Em đang chuẩn bị lệ phí dự tuyển thạc sĩ theo file đang mở.
@masters_tuition_2022|admission|33|easy|Thông báo tuyển sinh thạc sĩ ghi học phí nêu trong thông báo là bao nhiêu?|30.000.000 đồng/năm học.
paraphrase|học phí cao học ghi trong file là bao nhiêu
abbreviation|hp ths nêu trong thông báo bn/năm
colloquial|học cao học theo mức ghi trong file hết khoảng bao nhiêu tiền một năm vậy
code_switching|master's annual tuition nêu trong thông báo là bao nhiêu
lexical_mismatch|mức tiền học mỗi năm bậc cao học ghi trong thông báo tuyển sinh là gì
long_noisy|mình đang tính tiền học với tiền trọ nhưng hỏi mỗi tiền học thôi nha, file mình vừa up ghi học phí thạc sĩ bao nhiêu một năm? chỉ lấy mức trong file, tiền trọ với tiền ăn mình tính sau, đọc bảng phí hơi loạn
@masters_duration_2022|admission|34|easy|Chương trình thạc sĩ trong thông báo này đào tạo bao lâu?|2 năm, chính quy.
paraphrase|thạc sĩ trong thông báo học trong mấy năm
colloquial|cao học theo thông báo này học bao lâu mới xong vậy
abbreviation|ths trong thông báo tg đào tạo bn năm
code_switching|duration of master theo uploaded notice là bao lâu
implicit_intent|em muốn tính thời gian học cao học theo file đang mở, cần dành mấy năm
typo|thac sy trong pdf dao tao may nam
@masters_foreign_language_entry_2022|admission|8|easy|Chuẩn ngoại ngữ đầu vào thạc sĩ theo thông báo là bậc mấy?|Bậc 3 theo khung 6 bậc.
paraphrase|đầu vào ngoại ngữ cao học cần bậc mấy
abbreviation|ths NN đầu vào bậc bn
code_switching|master English entry level là level mấy
colloquial|muốn vào cao học theo thông báo thì tiếng Anh phải tới bậc nào
lexical_mismatch|mức năng lực ngoại ngữ để nộp vào bậc cao học là gì
contextual_followup|vậy đầu vào cần bậc mấy|Chuẩn ngoại ngữ đầu vào thạc sĩ theo thông báo là bậc mấy?|Em đang đọc điều kiện ngoại ngữ tuyển thạc sĩ.
@masters_foreign_language_exit_2022|admission|8|medium|Khóa thạc sĩ nêu trong file phải đạt ngoại ngữ đầu ra bậc mấy?|Bậc 4 theo khung 6 bậc.
paraphrase|chuẩn ngoại ngữ tốt nghiệp thạc sĩ khóa nêu trong file là bậc nào
code_switching|master khóa nêu trong file English exit level là bao nhiêu
abbreviation|ths khóa nêu trong file NN đầu ra bậc bn
colloquial|học cao học theo khóa ghi trong file thì ra trường tiếng Anh bậc mấy
lexical_mismatch|đạt mức ngôn ngữ nào mới hoàn tất yêu cầu đầu ra cao học khóa nêu trong file
contextual_followup|còn lúc ra trường thì sao|Chuẩn ngoại ngữ đầu ra thạc sĩ khóa nêu trong file là bậc mấy?|Em hỏi chuẩn ngoại ngữ của khóa thạc sĩ nêu trong file.
@masters_late_language_evidence_2022|admission|9|hard|Chưa có minh chứng ngoại ngữ khi đăng ký thạc sĩ trong thông báo thì có được bổ sung sau không và trước lúc nào?|Được đăng ký, phải bổ sung trước quyết định trúng tuyển, dự kiến tháng 11/2022.
conditional|chưa có chứng chỉ ngoại ngữ lúc đăng ký cao học trong thông báo thì được bổ sung sau không
multi_hop|cao học trong thông báo cho nợ minh chứng ngoại ngữ không, nếu được thì hạn trước mốc nào
slang|đăng ký ths trong thông báo mà cert chưa về, có cho nợ tới lúc nào k
code_switching|language evidence pending khi apply master theo file đang mở, can submit later before what milestone
long_noisy|em đang đối chiếu thông báo thạc sĩ theo file đang mở, lúc đăng ký có thể chưa kịp nhận chứng chỉ ngoại ngữ nên muốn biết có được nộp hồ sơ trước rồi bổ sung không và phải bổ sung trước khi nào
contextual_followup|chưa có giấy chứng minh thì nộp sau được không|Chưa có minh chứng ngoại ngữ khi đăng ký thạc sĩ trong thông báo có được bổ sung sau không?|Em hỏi điều kiện ngoại ngữ dự tuyển thạc sĩ theo file đang mở.
@masters_research_bonus_cap_2022|admission|14,15|hard|Điểm thưởng nghiên cứu khoa học tích lũy tối đa khi xét tuyển thẳng thạc sĩ là bao nhiêu?|Tối đa 0,5 điểm.
multi_hop|có cả giải nghiên cứu với bài báo thì xét tuyển thẳng thạc sĩ cộng tối đa được bao nhiêu
abbreviation|xtt ths điểm NCKH cộng dồn cap bn
code_switching|research bonus cap cho direct admission master là bao nhiêu
conditional|nếu nhiều công trình và giải thưởng cùng đủ điều kiện thì tuyển thẳng cao học có chặn trần điểm cộng không
lexical_mismatch|mức trần cộng điểm từ thành tích khoa học trong diện vào thẳng cao học là gì
long_noisy|mình đọc thông báo cao học rồi mà hơi lú, thấy giải nghiên cứu cộng điểm, bài báo cũng cộng, bạn mình cứ bảo cộng hết là được 😂 nếu có nhiều loại cùng lúc thì trong file có trần tổng điểm cộng không nhỉ
@masters_isi_bonus_2022|admission|15|medium|Bài báo ISI được thưởng bao nhiêu điểm khi xét tuyển thẳng thạc sĩ?|0,3 điểm.
paraphrase|một bài ISI được cộng mấy điểm xét tuyển thẳng cao học
abbreviation|ISI => xtt ths + bn điểm
code_switching|ISI paper bonus for master's direct admission là bao nhiêu
colloquial|có bài báo ISI thì vụ tuyển thẳng cao học được thêm bao nhiêu vậy
lexical_mismatch|công bố trong hệ thống ISI được quy đổi thành mấy điểm thưởng theo thông báo tuyển thẳng thạc sĩ
typo|bai bao isi cong may diem tuyen thag thac si
@masters_scopus_bonus_2022|admission|15|medium|Bài báo Scopus được thưởng bao nhiêu điểm khi xét tuyển thẳng thạc sĩ?|0,2 điểm.
paraphrase|bài Scopus trong thông báo tuyển thẳng thạc sĩ được tính bao nhiêu điểm
abbreviation|scopus +bn đ xtt ths
code_switching|Scopus publication có bao nhiêu bonus points khi direct admission master
colloquial|em có bài Scopus thì tuyển thẳng cao học được cộng mấy chấm
lexical_mismatch|điểm quy đổi công bố khoa học thuộc Scopus theo diện tuyển thẳng cao học là gì
typo|scopuss dc cong bn diem vao thac sy
@masters_direct_admission_timeline_2022|admission|19,20|hard|Xét tuyển thẳng thạc sĩ trong thông báo diễn ra khi nào và thông báo kết quả ngày nào?|Xét 05–08/09/2022, thông báo 09/09/2022.
multi_hop|tuyển thẳng cao học trong thông báo xét ngày nào rồi bao giờ biết kết quả
abbreviation|xtt ths trong thông báo lịch xét + ngày có kq
code_switching|direct admission review dates và result date master trong thông báo là khi nào
colloquial|trong thông báo duyệt hồ sơ tuyển thẳng cao học trong mấy ngày, xong lúc nào báo đỗ
long_noisy|mình cần ghi hai mốc riêng của xét tuyển thẳng thạc sĩ trong thông báo: khoảng thời gian hội đồng xét và ngày thông báo kết quả, nhờ bạn phân biệt giúp
lexical_mismatch|thời điểm đánh giá hồ sơ và công bố quyết định xét diện vào thẳng cao học trong thông báo khác nhau thế nào
@masters_registration_portal_2022|admission|30|easy|Đăng ký dự tuyển thạc sĩ theo thông báo ở website nào?|http://tssdh.vnu.edu.vn.
paraphrase|thông báo cao học bảo đăng ký ở trang nào
colloquial|muốn đăng ký thạc sĩ thì vào web nào nhỉ
abbreviation|link đk ths đâu
code_switching|online registration portal master là gì
implicit_intent|mình chưa tìm được chỗ tạo hồ sơ online cao học theo file đang mở
typo|web dang ki thac si la trang nao
@excellent_student_no_low_grade|rewards|15|hard|Có học phần dưới C+ thì có đạt danh hiệu Sinh viên Xuất sắc theo quy định không?|Không; còn yêu cầu học tập và rèn luyện loại Xuất sắc.
conditional|học tập và rèn luyện xuất sắc mà có môn C thì được sinh viên Xuất sắc theo quy định không|Học tập và rèn luyện Xuất sắc nhưng có một môn C có đạt danh hiệu Sinh viên Xuất sắc không?
slang|có một môn dưới C+ là bay danh hiệu sv xuất sắc à
abbreviation|sv XS có 1 môn < C+ đc k
code_switching|one grade below C+ có còn eligible for excellent student award không
colloquial|đang xem quy định khen thưởng, có môn dưới C+ thì danh hiệu xuất sắc còn xét được không
long_noisy|em đang hỏi danh hiệu Sinh viên Xuất sắc trong quy định, không phải học bổng nhé, nếu tổng học tập và rèn luyện đều xuất sắc nhưng lỡ một môn dưới C+ thì có bị loại không
@good_student_training_requirement|rewards|15|hard|Danh hiệu Sinh viên Giỏi yêu cầu kết quả rèn luyện từ mức nào?|Từ loại Tốt trở lên, cùng học tập Giỏi trở lên và không môn dưới C+.
paraphrase|rèn luyện tối thiểu loại gì mới xét Sinh viên Giỏi theo quy định
abbreviation|sv giỏi ĐRL cần loại nào
code_switching|good student award cần conduct rating level nào
conditional|học tập giỏi nhưng rèn luyện trung bình thì có danh hiệu Sinh viên Giỏi không|Học tập Giỏi nhưng rèn luyện Trung bình có được danh hiệu Sinh viên Giỏi không?
lexical_mismatch|phần đánh giá ý thức và hoạt động phải ở mức nào để nhận danh hiệu học tập giỏi trong quy định
contextual_followup|còn phần rèn luyện thì cần tới loại nào|Danh hiệu Sinh viên Giỏi yêu cầu rèn luyện từ mức nào?|Em đang xem điều kiện danh hiệu Sinh viên Giỏi trong quy định.
@top_graduate_scope|rewards|15|medium|Thủ khoa ngành học theo quy định được xét theo từng ngành hay toàn trường?|Theo ngành, điểm trung bình toàn khóa cao nhất và tốt nghiệp đúng hạn chuẩn.
paraphrase|thủ khoa tốt nghiệp quy định xét theo ngành hay cả trường
colloquial|thủ khoa ở theo bản khen thưởng là đứng đầu ngành hay đứng đầu hết trường vậy
abbreviation|thủ khoa GPA top ngành hay top trường
code_switching|top graduate award ranked by major or university-wide
lexical_mismatch|phạm vi so sánh điểm toàn khóa để chọn sinh viên tốt nghiệp đứng đầu theo quy định là gì
typo|thu khoa nganh hoc xet tung nghanh hay toan truong
@top_graduate_early_graduation|rewards|15|hard|Tốt nghiệp sớm thì được xét Thủ khoa ngành học vào lúc nào?|Xét vào thời điểm tốt nghiệp đúng hạn của ngành đào tạo.
conditional|ra trường sớm thì xét thủ khoa ngành theo quy định ngay luôn không
slang|tn sớm có được chốt thủ khoa luôn k theo
code_switching|early graduation thì top graduate award xét at what time
colloquial|em hoàn thành sớm hơn khóa, theo quy định thì lúc nào mới xét thủ khoa cho em
lexical_mismatch|người hoàn thành chương trình trước hạn được đưa vào đợt xét sinh viên đứng đầu ngành ở mốc nào theo quy định
long_noisy|cho mình hỏi ngoài lề tí à mà vẫn về file vừa up 😅 nếu học nhanh xong trước khóa thì xét thủ khoa ngay đợt mình ra trường hay chờ khóa ra trường đúng hạn? bạn mình nói hai kiểu nên mình không biết tin bên nào
@excellent_student_reward_form|rewards|15|medium|Danh hiệu Sinh viên Xuất sắc theo quy định được khen thưởng bằng hình thức gì?|Giấy khen và tiền thưởng theo quy định hiện hành, không nêu số tiền cố định.
paraphrase|sinh viên Xuất sắc bản quy định được thưởng gì
abbreviation|sv XS nhận giấy hay tiền
code_switching|excellent student award gồm certificate hay cash reward
colloquial|đạt danh hiệu xuất sắc ở theo bản đang mở thì có giấy khen thôi hay có tiền nữa
lexical_mismatch|những hình thức ghi nhận dành cho danh hiệu học tập xuất sắc theo quy định là gì
contextual_followup|được nhận những gì thế|Danh hiệu Sinh viên Xuất sắc được thưởng bằng hình thức gì?|Em hỏi về danh hiệu Sinh viên Xuất sắc trong quy định khen thưởng.
@collective_contribution_reward_conditions|rewards|15,16|hard|Danh hiệu đóng góp công tác tập thể yêu cầu những điều kiện gì?|Học tập từ 3,0; không môn dưới D; rèn luyện Xuất sắc; giữ chức vụ lớp/Đoàn-Hội và đóng góp tích cực.
multi_hop|quy định xét sinh viên đóng góp tập thể cần điểm bao nhiêu và có phải làm cán bộ lớp không
abbreviation|sv đóng góp tập thể GPA/ĐRL/chức vụ cần gì
code_switching|collective contribution award cần academic score và leadership role thế nào
conditional|chỉ GPA từ 3.0 mà không giữ chức vụ nào thì đủ danh hiệu đóng góp tập thể chưa|GPA từ 3,0 nhưng không giữ chức vụ có đủ danh hiệu đóng góp tập thể không?
lexical_mismatch|được ghi nhận vì hoạt động lớp và Đoàn ở theo quy định thì phải thỏa các tiêu chí học tập và tổ chức nào
long_noisy|em thấy có danh hiệu sinh viên có đóng góp cho công tác tập thể trong quy định, nhờ tách giúp điều kiện về GPA, điểm môn, rèn luyện và vai trò cán bộ chứ em đọc hơi rối
@excellent_thesis_award_conditions|rewards|16|hard|Khen thưởng khóa luận/đồ án Xuất sắc yêu cầu gì về tốt nghiệp và học tập rèn luyện?|Đúng/sớm hạn chuẩn; học tập và rèn luyện Khá trở lên; hội đồng công nhận bảo vệ Xuất sắc.
multi_hop|muốn được thưởng khóa luận xuất sắc theo quy định thì ngoài điểm bảo vệ cần điều kiện gì
conditional|khóa luận xuất sắc mà tốt nghiệp trễ thì còn được khen theo không|Bảo vệ khóa luận Xuất sắc nhưng tốt nghiệp trễ có đủ điều kiện khen thưởng không?
abbreviation|KLTN XS điều kiện GPA ĐRL và hạn tn ntn
code_switching|excellent thesis award có graduation timing và academic conduct conditions nào
colloquial|bảo vệ ngon rồi nhưng quy định còn xét học lực với rèn luyện nữa hả
long_noisy|mình chỉ hỏi danh hiệu khóa luận hoặc đồ án xuất sắc theo quy định, không hỏi điểm chấm riêng, sinh viên còn phải tốt nghiệp vào lúc nào và học tập rèn luyện ở mức nào mới được khen
@advanced_class_percentage|rewards|16|medium|Tập thể lớp Tiên tiến cần bao nhiêu phần trăm sinh viên học tập và rèn luyện Khá trở lên?|70%, cùng các điều kiện khác trong Điều 8.
paraphrase|lớp Tiên tiến theo quy định cần tỷ lệ sinh viên khá là bao nhiêu
abbreviation|lớp TT cần bn % sv khá trở lên
code_switching|advanced class award minimum percentage of khá students là bao nhiêu
colloquial|muốn lớp được Tiên tiến theo thì mấy phần trăm sinh viên phải khá cả học tập lẫn rèn luyện
lexical_mismatch|tỷ trọng thành viên đạt kết quả từ khá trong học tập và rèn luyện để lớp được khen Tiên tiến theo là gì
typo|lop tien tien can bao nhieu phan tram sinh vien kha
@excellent_class_additional_conditions|rewards|16|hard|Lớp đã đạt Tiên tiến cần thêm gì để được Tập thể Xuất sắc?|Từ 10% sinh viên Giỏi và có sinh viên Xuất sắc.
conditional|đạt lớp tiên tiến rồi thì cần thêm gì để lên lớp xuất sắc
multi_hop|lớp xuất sắc phải vừa đạt Tiên tiến vừa có bao nhiêu sinh viên Giỏi và Xuất sắc
abbreviation|tập thể XS cần % sv giỏi + bn sv XS
code_switching|upgrade from advanced to excellent class award needs what extra conditions
lexical_mismatch|tập thể đã đáp ứng mức khen cơ bản phải bổ sung tiêu chí thành viên nổi bật nào để được mức Xuất sắc trong quy định
long_noisy|lớp mình đang bàn làm hoạt động cuối năm, group chat trôi mất đoạn này rồi, giả sử lớp đủ hết điều kiện Tiên tiến trong pdf thì lên Xuất sắc cần bn phần trăm sv Giỏi, có cần người Xuất sắc nữa không, hỏi hơi dài sorry nha
@admission_excellence_priority_points|rewards|18|hard|Khen sinh viên trúng tuyển xuất sắc có tính điểm ưu tiên không?|Xét điểm thi cao nhất theo từng phương thức, chưa tính điểm ưu tiên.
conditional|điểm có cộng ưu tiên thì dùng xét khen đầu vào theo quy định được không
colloquial|thủ khoa đầu vào được thưởng nhìn điểm gốc hay điểm cộng ưu tiên vậy
abbreviation|sv trúng tuyển XS có + điểm ƯT k
code_switching|admission excellence reward uses raw score or score with priority bonus
lexical_mismatch|khi chọn sinh viên có thành tích tuyển sinh cao nhất để khen theo có cộng phần ưu tiên khu vực không
long_noisy|mình đang hỏi quy định khen thưởng sinh viên trúng tuyển nhé, nếu điểm cuối cùng đã cộng ưu tiên thì trường dùng con số đó hay dùng điểm thi chưa cộng để tìm người cao nhất
@admission_excellence_tuition_reward|rewards|18|easy|Sinh viên trúng tuyển xuất sắc theo quy định được thưởng học phí năm nào?|Năm học thứ nhất.
paraphrase|thưởng học phí cho sinh viên trúng tuyển xuất sắc quy định là năm nào
abbreviation|trúng tuyển XS thưởng hp mấy năm
colloquial|thành tích đầu vào xuất sắc theo thì khoản học phí được thưởng tính năm đầu thôi à
code_switching|admission excellence tuition reward covers which academic year
lexical_mismatch|khoản tiền học được dùng làm phần thưởng tuyển sinh xuất sắc theo quy định thuộc năm học nào
contextual_followup|thưởng học phí của năm nào vậy|Sinh viên trúng tuyển xuất sắc được thưởng học phí năm nào?|Em đang xem diện khen sinh viên trúng tuyển xuất sắc trong quy định.
@reward_policy_start_2023|rewards|7,20|medium|Quy định khen thưởng ban hành áp dụng từ tháng nào?|Tháng 9/2023.
paraphrase|quy định khen thưởng bắt đầu áp dụng khi nào
abbreviation|QĐ khen thưởng hiệu lực áp dụng tháng bn
code_switching|student rewards policy starts applying from which month
colloquial|bản khen thưởng ký thì từ tháng nào sinh viên dùng vậy
lexical_mismatch|mốc bắt đầu thực hiện chế độ khen thưởng sinh viên trong văn bản là gì
typo|quy dinh khen thuong ap dung tu thang nao
@exam_reprimand_penalty_2014|regulation|3|medium|Bị khiển trách trong kỳ thi theo trích quy chế trường bị trừ bao nhiêu điểm bài thi?|Trừ 25% số điểm đạt được của bài thi học phần đó.
paraphrase|khiển trách lúc thi theo quy chế trường thì trừ bao nhiêu phần trăm điểm
abbreviation|khiển trách thi QĐ trừ bn % điểm
slang|dính khiển trách trong phòng thi theo bản quy chế này thì bay bao nhiêu điểm
code_switching|exam reprimand penalty in the uploaded rules cuts what percentage of marks
conditional|lần đầu nhìn bài bạn và bị khiển trách thì theo trích quy chế bài thi bị trừ thế nào|Lần đầu nhìn bài người khác và bị khiển trách theo quy chế thì bị trừ bao nhiêu phần trăm điểm?
lexical_mismatch|mức giảm điểm bài kiểm tra khi nhận hình thức nhắc phạt khiển trách trong phòng thi theo trích quy chế là gì
@exam_warning_penalty_2014|regulation|3|medium|Bị cảnh cáo trong phòng thi theo trích quy chế trường bị trừ bao nhiêu điểm?|Trừ 50% số điểm bài thi đạt được; đây là cảnh cáo thi, không phải cảnh báo học vụ.
paraphrase|cảnh cáo trong giờ thi theo quy chế trường trừ mấy phần trăm điểm
abbreviation|cảnh cáo thi -bn % điểm
code_switching|exam warning penalty in this PDF reduces score by how much
slang|ăn cảnh cáo phòng thi bản là mất nửa điểm hả|Theo quy chế trường, cảnh cáo phòng thi có bị trừ nửa số điểm bài thi không?
colloquial|mình hỏi cảnh cáo lúc đang thi trong quy chế nhé, điểm bài bị giảm bao nhiêu
long_noisy|cảnh cáo trong phòng thi với cảnh báo học vụ chắc khác nhau, mình chỉ cần biết theo trích quy chế trường thì bị cảnh cáo ngay trong kỳ thi sẽ mất bao nhiêu phần trăm điểm bài đó
@exam_suspension_result_2014|regulation|3|hard|Bị đình chỉ thi theo trích quy chế trường thì bài thi và việc ở lại phòng thi thế nào?|Bài thi điểm 0 và ra khỏi phòng thi ngay sau quyết định.
multi_hop|đình chỉ thi theo quy chế thì điểm bài là mấy và có phải ra khỏi phòng ngay không
slang|bị đình chỉ thi bản quy chế này là ăn 0 rồi ra ngoài luôn à
abbreviation|đình chỉ thi điểm bn, có rời phòng ngay k
code_switching|exam suspension under trường means zero score and immediate exit không
colloquial|nếu bị đình chỉ thi theo quy chế trường thì còn được làm tiếp bài không và bài đó tính điểm sao|Bị đình chỉ thi theo quy chế trường có được làm tiếp bài và bài thi tính bao nhiêu điểm?
long_noisy|em đọc trích quy chế của trường thấy mục đình chỉ thi, nhờ nói rõ hai hậu quả là điểm bài thi và có được ở lại phòng thi hay phải ra ngay sau quyết định
@exam_impersonation_first_offense_2014|regulation|3|hard|Thi hộ hoặc nhờ thi hộ lần đầu theo trích quy chế trường bị xử lý thế nào?|Đình chỉ học tập 1 năm.
conditional|lần đầu nhờ người thi hộ thì quy chế trường phạt thế nào
slang|thi hộ lần 1 theo bản quy chế này bị nghỉ học bao lâu
abbreviation|thi hộ/nhờ thi hộ lần đầu QĐ xử lý sao
code_switching|first exam impersonation offense theo file academic suspension bao lâu
lexical_mismatch|lần đầu để người khác làm bài thay hoặc đi làm thay bài thi cho bạn bị đình chỉ học trong bao lâu theo trích quy chế
colloquial|quy chế có cho cảnh cáo thôi khi nhờ thi hộ lần đầu không|Nhờ thi hộ lần đầu theo quy chế trường có chỉ bị cảnh cáo không?
@exam_impersonation_repeat_offense_2014|regulation|3|hard|Thi hộ hoặc nhờ thi hộ lần thứ hai theo trích quy chế trường bị xử lý thế nào?|Buộc thôi học.
conditional|tái phạm thi hộ lần hai thì quy chế trường xử lý sao
slang|nhờ thi hộ lần 2 là bị đuổi học luôn à
abbreviation|thi hộ lần 2 QĐ mức kl gì
code_switching|second exam impersonation offense theo file dẫn tới dismissal không
lexical_mismatch|lần thứ hai dùng người làm bài thay trong kỳ thi sẽ bị chấm dứt học tại trường theo quy chế không|Thi hộ hoặc nhờ thi hộ lần thứ hai theo quy chế trường có bị buộc thôi học không?
long_noisy|mình đang đối chiếu hai mức trong trích quy chế trường, lần đầu thì đình chỉ một năm rồi, còn lần thứ hai thi hộ hoặc nhờ thi hộ có còn chỉ đình chỉ nữa không|Thi hộ hoặc nhờ thi hộ lần thứ hai theo quy chế trường có tiếp tục chỉ bị đình chỉ học tập không?
@exam_repeated_cheating_escalation_2014|regulation|3|hard|Đã bị khiển trách nhưng tiếp tục vi phạm trong cùng kỳ thi thì theo quy chế trường bị mức nào?|Cảnh cáo; bị cảnh cáo rồi tiếp tục vi phạm thì đình chỉ thi.
conditional|bị khiển trách rồi mà vẫn quay cóp trong giờ thi ấy thì bản quy chế này tăng lên mức nào
multi_hop|theo quy chế khiển trách xong tái phạm thì sao, cảnh cáo xong vẫn tái phạm thì sao|Theo quy chế trường, tái phạm sau khiển trách và sau cảnh cáo bị xử lý thế nào?
slang|nhắc phạt khiển trách rồi vẫn cố vi phạm trong cùng bài thi thì ăn gì tiếp theo file đang mở
abbreviation|khiển trách -> tái phạm cùng giờ thi QĐ = mức gì
code_switching|repeat violation after reprimand in same exam theo file escalates to what sanction
long_noisy|không phải hai kỳ thi khác nhau nhé, em hỏi bản quy chế này: trong cùng một bài thi đã bị khiển trách một lần rồi mà vẫn tiếp tục vi phạm thì hình thức kỷ luật tăng như thế nào
@exam_prohibited_items_after_opening_2014|regulation|3|hard|Sau khi bóc đề bị phát hiện mang vật dụng không được phép thì quy chế trường xử lý thế nào?|Đình chỉ thi.
conditional|sau khi bóc đề mà phát hiện mang đồ bị cấm thì theo trường bị gì
slang|bóc đề rồi mới phát hiện phao trong đồ thì bị đình chỉ thi hả
abbreviation|mang vật dụng cấm sau bóc đề QĐ mức kl gì
code_switching|prohibited items found after opening exam paper theo file punishment là gì
lexical_mismatch|thời điểm đề đã mở mà thí sinh vẫn đem theo đồ không được phép thì mức xử lý trong trích quy chế là gì
colloquial|theo trích quy chế trường có chỉ cảnh cáo nếu vật dụng cấm bị phát hiện sau lúc bóc đề không|Mang vật dụng cấm bị phát hiện sau khi bóc đề theo quy chế có chỉ bị cảnh cáo không?
@exam_sanction_recording_2014|regulation|3|easy|Ai lập biên bản và thu tang vật vi phạm phòng thi theo trích quy chế trường?|Cán bộ coi thi lập biên bản, thu tang vật và ghi hình thức kỷ luật.
paraphrase|quy chế trường giao ai lập biên bản vi phạm phòng thi
abbreviation|ai lập bb + thu tang vật thi QĐ
code_switching|who records exam misconduct and collects evidence under the uploaded rules
colloquial|theo trích quy chế thì giám thị hay phòng đào tạo lập biên bản lúc sinh viên vi phạm trong thi
lexical_mismatch|người nào có trách nhiệm ghi nhận hành vi sai quy định và giữ vật chứng ngay tại phòng thi theo quy chế
implicit_intent|em muốn biết trong bản quy chế trường thì người chịu trách nhiệm giấy tờ kỷ luật phòng thi là ai
@electronics_total_credits_2023|electronics|24,25|medium|Chương trình điện tử viễn thông có tổng bao nhiêu tín chỉ, chưa tính những môn nào?|135 tín chỉ, chưa tính thể chất, quốc phòng-an ninh, kỹ năng bổ trợ.
paraphrase|khung điện tử viễn thông tổng mấy tín
abbreviation|ĐTVT CT tổng bn tc
code_switching|total credits of electronics and communications curriculum là bao nhiêu
multi_hop|khung ĐTVT tổng bao nhiêu tín, đã tính thể chất quốc phòng chưa
implicit_intent|mình đang lên kế hoạch học ĐTVT theo file đang mở, cần tích lũy tổng bao nhiêu tín chuyên môn|Theo khung ĐTVT, tổng tín chỉ chương trình chưa tính các môn bổ trợ là bao nhiêu?
long_noisy|em xem bản chương trình điện tử viễn thông thấy phần tổng tín chỉ nhưng không chắc mấy môn thể chất quốc phòng có nằm trong đó hay không, tổng cần học là bao nhiêu và loại trừ gì
@electronics_duration_2023|electronics|16|easy|Thời gian đào tạo chuẩn ngành điện tử viễn thông trong chương trình là bao lâu?|4 năm.
paraphrase|chương trình điện tử viễn thông học chuẩn mấy năm
abbreviation|ĐTVT đào tạo bn năm
code_switching|standard study duration electronics is how many years
colloquial|khung ĐTVT này thì theo tiến độ bình thường bao lâu ra trường
lexical_mismatch|độ dài lộ trình đào tạo tiêu chuẩn của điện tử viễn thông ghi trong bản là gì
typo|dien tu vien thong hoc may nam
@electronics_english_exit_2023|electronics|21|easy|Chuẩn ngoại ngữ đầu ra của chương trình điện tử viễn thông là bậc mấy?|Bậc 3/6.
paraphrase|điện tử viễn thông theo khung này ra trường cần tiếng Anh bậc mấy
abbreviation|ĐTVT trong file TA đầu ra bậc bn
code_switching|English exit level for electronics curriculum là level nào
colloquial|ngành điện tử viễn thông theo bản đang mở thì lúc tốt nghiệp ngoại ngữ phải đạt bậc nào
lexical_mismatch|chuẩn năng lực ngôn ngữ để hoàn tất chương trình điện tử viễn thông là mức nào trong khung sáu bậc
contextual_followup|tiếng Anh lúc ra trường cần bậc nào|Chuẩn ngoại ngữ đầu ra chương trình điện tử viễn thông là bậc mấy?|Mình đang xem khung chương trình Công nghệ kỹ thuật điện tử viễn thông.
@electronics_data_structures_prerequisite_2023|electronics|55,56|hard|Cấu trúc dữ liệu và giải thuật trong khung điện tử viễn thông cần môn tiên quyết nào và có mấy tín chỉ?|INT2210 có 4 tín chỉ, tiên quyết INT1008.
multi_hop|cấu trúc dữ liệu trong khung ĐTVT bao nhiêu tín và học trước môn gì
abbreviation|CTDL GT ĐTVT mấy tc, tq mã nào
code_switching|data structures and algorithms in electronics credits and prerequisite là gì
lexical_mismatch|môn tổ chức dữ liệu và thuật toán trong chương trình điện tử viễn thông yêu cầu hoàn thành học phần nào trước
implicit_intent|mình định học cấu trúc dữ liệu ở ĐTVT theo file đang mở, cần xem môn nào phải qua trước|Cấu trúc dữ liệu và giải thuật khung ĐTVT có học phần tiên quyết nào?
contextual_followup|cần học gì trước và mấy tín vậy|Cấu trúc dữ liệu và giải thuật trong khung ĐTVT tiên quyết gì và có mấy tín chỉ?|Mình hỏi môn Cấu trúc dữ liệu và giải thuật thuộc khung điện tử viễn thông.
@electronics_analog_lab_prerequisite_2023|electronics|65,66|hard|Thực tập điện tử tương tự trong chương trình cần môn tiên quyết nào?|ELT2040; thực tập ELT3102 có 2 tín chỉ.
paraphrase|môn tiên quyết thực tập điện tử tương tự là gì
abbreviation|lab ĐT tương tự tq môn nào
code_switching|analog electronics lab prerequisite in curriculum là gì
lexical_mismatch|muốn vào phần thực hành mạch tương tự thuộc khung điện tử viễn thông thì cần qua học phần nào
implicit_intent|em đang định đăng ký thực tập điện tử tương tự trong file nhưng chưa biết môn phải học trước
colloquial|học lab điện tử tương tự theo file này thì trước đó phải học điện tử tương tự chưa|Thực tập điện tử tương tự có yêu cầu học trước Điện tử tương tự không?
@electronics_digital_lab_credits_2023|electronics|67|easy|Thực tập điện tử số trong khung điện tử viễn thông có mấy tín chỉ?|2 tín chỉ.
paraphrase|thực tập điện tử số là mấy tín
abbreviation|lab ĐT số bn tc
code_switching|digital electronics lab worth how many credits
colloquial|môn thực tập điện tử số trong bản ĐTVT nặng mấy tín vậy
typo|thuc tap dien tu so bao nhieu tin chi
contextual_followup|môn này mấy tín nhỉ|Thực tập điện tử số trong chương trình có mấy tín chỉ?|Mình hỏi môn Thực tập điện tử số ở chương trình điện tử viễn thông.
@electronics_dsp_prerequisite_2023|electronics|69,70|hard|Xử lý tín hiệu số trong khung điện tử viễn thông tiên quyết môn nào và mấy tín chỉ?|ELT3144, 4 tín chỉ, tiên quyết ELT2035.
multi_hop|xử lý tín hiệu số ĐTVT khung mấy tín, cần qua môn nào
code_switching|DSP credits and prereq in electronics curriculum là gì
abbreviation|DSP ĐTVT tc + tq bn
conditional|muốn học Xử lý tín hiệu số khung ĐTVT thì có phải học Tín hiệu và hệ thống trước không|Xử lý tín hiệu số khung ĐTVT có tiên quyết Tín hiệu và hệ thống không?
lexical_mismatch|học phần xử lý các tín hiệu dạng số trong bản điện tử viễn thông yêu cầu kiến thức từ môn nào trước
long_noisy|mình đang xếp môn ĐTVT mà wifi đăng ký lag quá :)) trước khi bấm lại hỏi nhanh môn xử lý tín hiệu số trong file mấy tín và cần học trước môn nào, hai ý thôi nha để mình khỏi đăng ký rồi bị hủy
@electronics_common_credits_2023|electronics|25,26|easy|Khối kiến thức chung của chương trình điện tử viễn thông có mấy tín chỉ?|26 tín chỉ.
paraphrase|khối chung ĐTVT cần mấy tín
abbreviation|KTC ĐTVT bn tc
code_switching|common knowledge block credits electronics là bao nhiêu
colloquial|chương trình điện tử viễn thông thì riêng phần kiến thức chung là bao nhiêu tín
lexical_mismatch|phần môn đại cương chung ghi trong cơ cấu chương trình điện tử viễn thông có khối lượng tín chỉ nào
typo|khoi kien thuc chung dien tu vien thong bn tin
@mechatronics_total_credits|mechatronics|1,2|medium|Khung cơ điện tử trong file đang mở yêu cầu tổng bao nhiêu tín chỉ?|155 tín chỉ theo PDF được lưu trong corpus; chưa có review độc lập về niên khóa áp dụng.
paraphrase|khung cơ điện tử trong file tổng bao nhiêu tín
abbreviation|CĐT trong file tổng bn tc
code_switching|total credits in mechatronics in this uploaded PDF là bao nhiêu
colloquial|bản cơ điện tử đang lưu trong bộ tài liệu thì phải học tổng mấy tín vậy
implicit_intent|mình đang tính lượng môn cho cơ điện tử theo PDF trong file đang mở, tổng số tín cần tích lũy là bao nhiêu
long_noisy|mình biết cần đối chiếu khóa áp dụng riêng nhưng giờ chỉ hỏi con số trong PDF cơ điện tử vừa tải lên, cả chương trình ghi tổng bao nhiêu tín chỉ
@mechatronics_matlab_prerequisites|mechatronics|44,45,46,47|hard|Matlab và ứng dụng trong khung cơ điện tử trong file có mấy tín chỉ và những môn tiên quyết nào?|3 tín chỉ, INT1006, MAT1093, MAT1042.
multi_hop|Matlab và ứng dụng khung cơ điện tử trong file có mấy tín và cần qua những môn nào
abbreviation|matlab CĐT trong file tc + các tq là gì
code_switching|Matlab and Applications mechatronics in this PDF credits and prerequisites please
implicit_intent|mình muốn đăng ký Matlab của cơ điện tử theo file đang mở nên cần biết các môn phải học trước|Matlab và ứng dụng cơ điện tử trong file có những học phần tiên quyết nào?
lexical_mismatch|môn dùng Matlab để giải bài toán kỹ thuật trong khung cơ điện tử trong file đòi hỏi học phần nền nào
contextual_followup|cần học trước những môn nào nhỉ|Matlab và ứng dụng cơ điện tử trong file có các học phần tiên quyết nào?|Mình đang xem môn Matlab và ứng dụng của cơ điện tử trong PDF đang mở.
@mechatronics_calculus2_prerequisite|mechatronics|28,29|hard|Giải tích 2 trong khung cơ điện tử trong file có mấy tín chỉ và tiên quyết gì?|4 tín chỉ; MAT1041.
multi_hop|Giải tích 2 cơ điện tử trong file bao nhiêu tín, học trước gì
abbreviation|GT2 CĐT trong file tc/tq ntn
code_switching|Calculus 2 in mechatronics in this PDF credits and prereq là gì
conditional|muốn học Giải tích 2 cơ điện tử trong file thì cần Giải tích 1 trước đúng không|Giải tích 2 cơ điện tử trong file có tiên quyết Giải tích 1 không?
lexical_mismatch|môn giải tích phần tiếp theo trong PDF cơ điện tử trong file yêu cầu mã học phần nào trước
typo|giai tich 2 co dien tu trong file can mon nao truoc
@mechatronics_probability_prerequisites|mechatronics|33,34,35|hard|Xác suất thống kê ứng dụng cơ điện tử trong file yêu cầu những môn nào trước?|MAT1093 và MAT1042.
paraphrase|xác suất thống kê ứng dụng cơ điện tử trong file tiên quyết là những môn gì
abbreviation|XSTK ứng dụng CĐT trong file cần tq nào
code_switching|applied probability and statistics mechatronics in this PDF prerequisites là gì
conditional|học Xác suất thống kê ứng dụng trong khung cơ điện tử trong file có cần cả Đại số lẫn Giải tích 2 không|Xác suất thống kê ứng dụng cơ điện tử trong file có tiên quyết Đại số và Giải tích 2 không?
lexical_mismatch|môn thống kê và xác suất phục vụ kỹ thuật trong khung cơ điện tử trong file cần nền từ học phần nào
long_noisy|mình zoom bảng cơ điện tử trong pdf mãi chữ bé quá, màn hình còn nứt đúng cột tiên quyết nữa :v riêng xác suất thống kê ứng dụng thì phải học trước hết những mã môn nào vậy, liệt kê đủ giúp mình
@mechatronics_machine_design_credits|mechatronics|56|easy|Cơ sở thiết kế máy trong khung cơ điện tử trong file có mấy tín chỉ?|4 tín chỉ.
paraphrase|Cơ sở thiết kế máy cơ điện tử trong file mấy tín
abbreviation|CSTKM CĐT trong file bn tc
code_switching|Fundamental of Machine Design mechatronics in this PDF credits bn
colloquial|môn thiết kế máy cơ sở của cơ điện tử trong PDF đang mở tính bao nhiêu tín vậy
typo|co so thiet ke may co dien tu trong file may tin
contextual_followup|mấy tín vậy bạn|Cơ sở thiết kế máy cơ điện tử trong file có mấy tín chỉ?|Mình đang hỏi môn Cơ sở thiết kế máy trong khung cơ điện tử trong file.
@mechatronics_supplementary_electives|mechatronics|7|medium|Phần bổ trợ cơ điện tử trong file yêu cầu chọn bao nhiêu trên tổng bao nhiêu tín chỉ?|5 trên 15 tín chỉ.
paraphrase|phần bổ trợ cơ điện tử trong file đang mở chọn mấy tín trên mấy tín
abbreviation|bổ trợ CĐT trong file chọn bn/tổng bn tc
code_switching|supplementary electives mechatronics in this PDF choose how many out of total credits
colloquial|bản cơ điện tử trong file ghi bổ trợ kiểu chọn trong danh sách thì em phải lấy bao nhiêu tín
lexical_mismatch|khối môn hỗ trợ được lựa chọn của PDF cơ điện tử trong file có mức tích lũy yêu cầu và mức cung cấp là bao nhiêu
long_noisy|em vừa up khung cơ điện tử, đọc phần bổ trợ thấy kiểu 5/15 gì đó nhưng không rõ dấu gạch là chọn mấy hay chia ra sao, hôm nay học cả ngày hơi đơ rồi 😭 phần này phải lấy bao nhiêu tín trên tổng bao nhiêu vậy
@mai_semester1_total|mai|42|easy|Học kỳ 1 chương trình chương trình liên kết có tổng bao nhiêu tín chỉ?|30 tín chỉ.
paraphrase|chương trình liên kết học kỳ một tổng mấy tín
abbreviation|chương trình liên kết hk1 bn tc
code_switching|semester 1 total credits chương trình liên kết curriculum là bao nhiêu
colloquial|học chương trình với MAI theo bản đang mở thì kỳ đầu ôm bao nhiêu tín vậy
lexical_mismatch|khối lượng học tập của học kỳ mở đầu chương trình liên kết chương trình liên kết trong bảng là gì
typo|chuong trinh lien ket hoc ky 1 tong bao nhiu tin
@mai_semester5_location|mai|44|easy|Các học phần học kỳ 5 trong chương trình chương trình liên kết do đơn vị nào phụ trách?|MAI theo cột Resources.
paraphrase|chương trình liên kết kỳ 5 học phần do trường nào phụ trách
abbreviation|chương trình liên kết hk5 bên nào dạy
code_switching|semester 5 courses chương trình liên kết taught by which institution
colloquial|bản chương trình liên kết tới kỳ năm thì học bên hay bên MAI vậy
lexical_mismatch|cột đơn vị cung cấp môn học ở học kỳ thứ năm trong bảng chương trình liên kết ghi gì
contextual_followup|kỳ 5 thì bên nào phụ trách|Học kỳ 5 chương trình chương trình liên kết do đơn vị nào phụ trách?|Mình đang xem chương trình liên kết chương trình liên kết.
@mai_final_attestation_credits|mai|45|medium|Final State Attestation trong chương trình chương trình liên kết có mấy tín chỉ và ở học kỳ nào?|9 tín chỉ, học kỳ 8.
multi_hop|Final State Attestation chương trình liên kết có mấy tín và kỳ nào
abbreviation|chương trình liên kết FSA hk mấy bn tc
code_switching|final state attestation credits and semester in chương trình liên kết please
colloquial|phần đánh giá cuối chương trình ghi Final State Attestation trong bản chương trình liên kết học lúc nào và tính mấy tín
lexical_mismatch|mục kiểm định cuối khóa mang tên Final State Attestation trong bảng chương trình liên kết được xếp kỳ nào và có khối lượng tín chỉ bao nhiêu
long_noisy|mình đang tra đúng bảng chương trình liên kết nhé, ở cuối có mục Final State Attestation nhưng cần hai thông tin để ghi kế hoạch: học kỳ và số tín chỉ của mục đó
@cs_master_ai_nlp_semesters|cs|3|hard|Trong hướng dẫn thạc sĩ Khoa học máy tính, Trí tuệ nhân tạo nâng cao và Xử lý ngôn ngữ tự nhiên học kỳ nào?|INT6146 học kỳ 1, INT6152 học kỳ 2.
multi_hop|AI nâng cao với NLP trong hướng dẫn thạc sĩ KHMT học ở kỳ nào vậy
abbreviation|ths KHMT AI nâng cao/NLP hk mấy
code_switching|Advanced AI and NLP semesters in CS master's progression là gì
colloquial|hướng dẫn cao học khoa học máy tính xếp môn trí tuệ nhân tạo nâng cao trước hay sau môn xử lý ngôn ngữ tự nhiên|Trong thạc sĩ KHMT, Trí tuệ nhân tạo nâng cao và Xử lý ngôn ngữ tự nhiên được xếp học kỳ nào, môn nào trước?
lexical_mismatch|hai môn về AI bậc nâng cao và xử lý văn bản ngôn ngữ trong lộ trình thạc sĩ KHMT được bố trí vào các kỳ nào
long_noisy|mình không hỏi ngành đại học KHMT nhé, mình hỏi hướng dẫn chương trình thạc sĩ Khoa học máy tính: môn Trí tuệ nhân tạo nâng cao và môn Xử lý ngôn ngữ tự nhiên và ứng dụng nằm ở học kỳ nào
@uploaded_document_audience|rewards|13|easy|Quy định trong PDF đang mở áp dụng cho những đối tượng nào?|Sinh viên đại học hệ chính quy và tập thể lớp sinh viên.
paraphrase|quy định trong file này áp dụng cho ai
colloquial|cái file mình vừa gửi là dành cho những người nào vậy
abbreviation|pdf này áp dụng cho đối tượng nào v
code_switching|who does this uploaded policy apply to
implicit_intent|mình chưa biết bản quy định vừa tải lên có dành cho sinh viên hệ nào
long_noisy|mình vừa up file quy định, đọc qua thấy nhiều điều nhưng chưa tìm ra đối tượng áp dụng, bạn chỉ giúp những nhóm người hay tập thể nào thuộc phạm vi của văn bản này nhé
@uploaded_document_effective_month|rewards|7,20|medium|Quy định trong PDF được áp dụng từ thời điểm nào?|Áp dụng từ tháng 9/2023; không suy thành hiệu lực pháp lý hiện hành ngoài phạm vi tài liệu.
paraphrase|file này nói bắt đầu áp dụng từ khi nào
abbreviation|QĐ trong pdf áp dụng từ tháng bn
code_switching|when does the policy in this PDF start applying
colloquial|đọc giúp mình bản này bắt đầu dùng từ lúc nào với
lexical_mismatch|mốc thời gian đưa quy định trong tài liệu này vào thực hiện là khi nào
implicit_intent|mình cần biết thời điểm bắt đầu áp dụng của bản vừa tải lên để đối chiếu với khóa học
@uploaded_document_contact|admission|35|easy|PDF đang mở ghi thông tin liên hệ tư vấn ở đâu?|Phòng Đào tạo 105-E3, 144 Xuân Thủy, Cầu Giấy; điện thoại và email trong mục liên hệ.
paraphrase|trong pdf này có thông tin liên hệ tư vấn ở đâu
colloquial|đọc file này xong còn thắc mắc thì hỏi bên nào vậy
abbreviation|cần tư vấn vụ trong file thì lh ai
code_switching|contact person or office trong uploaded PDF là ai
implicit_intent|mình muốn hỏi trực tiếp một người phụ trách về thông báo vừa gửi, file có đầu mối nào không
long_noisy|mình vừa tải thông báo lên rồi, nếu không hiểu một điều trong đó thì có địa chỉ phòng hoặc số điện thoại nào để hỏi lại trực tiếp không, tìm giúp mục liên hệ trong file nhé
@selected_section_plain_language|regulation|3|medium|Giải thích đoạn quy định kỷ luật phòng thi được chọn bằng cách dễ hiểu.|Phân biệt khiển trách trừ 25%, cảnh cáo trừ 50%, đình chỉ thi điểm 0; thi hộ có chế tài riêng.
paraphrase|giải thích đoạn mình chọn trong file bằng lời dễ hiểu giúp mình
colloquial|đoạn này đọc căng quá nói nôm na là sao
abbreviation|đoạn đang chọn nghĩa ntn v
code_switching|explain this selected passage in simple Vietnamese please
lexical_mismatch|chuyển phần đang bôi chọn thành lời giải thích đời thường được không
long_noisy|mình có bôi chọn một đoạn trong PDF mà đọc đi đọc lại vẫn hơi rối, bạn nói lại bằng câu dễ hiểu, tách từng mức xử lý và giữ đúng ý trong đoạn nhé
@selected_section_compare_sanctions|regulation|3|hard|So sánh khiển trách và cảnh cáo trong đoạn quy định phòng thi được chọn.|Khiển trách lỗi lần đầu trừ 25%; cảnh cáo có các lỗi/tái phạm được nêu, trừ 50%.
multi_hop|khiển trách với cảnh cáo trong đoạn mình chọn khác nhau chỗ nào
abbreviation|khiển trách vs cảnh cáo thi khác j trong đoạn này
code_switching|compare reprimand versus warning in this selected exam section
colloquial|cùng bị phạt lúc thi mà hai mức này khác nhau sao vậy
lexical_mismatch|mức xử lý nhẹ và mức xử lý cảnh cáo trong phần bôi chọn khác về lỗi và số điểm bị giảm thế nào
long_noisy|mình đã chọn đúng đoạn kỷ luật thi trong file rồi, chỉ cần bạn đối chiếu hai mức khiển trách và cảnh cáo, nêu trường hợp áp dụng và hậu quả về điểm chứ đừng lấy quy định ngoài file
@selected_section_extract_percentages|regulation|3|medium|Trong đoạn kỷ luật phòng thi được chọn, các mức trừ điểm là bao nhiêu phần trăm?|Khiển trách 25%, cảnh cáo 50% số điểm đạt được.
paraphrase|lấy giúp các con số phần trăm bị trừ điểm trong đoạn đang chọn
abbreviation|đoạn này trừ bn % từng mức
code_switching|extract the mark deduction percentages from this selection
colloquial|chốt hộ mình các mức bị trừ điểm ở phần vừa bôi chọn với
implicit_intent|mình cần ghi lại mấy tỷ lệ giảm điểm trong đoạn chọn để ôn quy chế thi
long_noisy|đừng tóm tắt cả file nhé, mình chỉ cần con số phần trăm bị trừ điểm của từng mức kỷ luật xuất hiện trong đoạn đã chọn, ghi cả tên mức để không nhầm
@uploaded_table_semester_lookup|mai|45|medium|Trong bảng chương trình được chọn, tổng tín chỉ học kỳ 7 và 8 lần lượt là bao nhiêu?|Học kỳ 7: 31; học kỳ 8: 29 tín chỉ.
multi_hop|trong bảng mình chọn kỳ 7 với kỳ 8 tổng mấy tín
abbreviation|bảng này hk7/hk8 bn tc
code_switching|in the selected table, total credits semester 7 vs 8 là bao nhiêu
colloquial|nhìn bảng cuối file giúp mình, kỳ bảy với kỳ tám nặng mấy tín mỗi kỳ
lexical_mismatch|hai học kỳ cuối hiển thị trong bảng được bôi chọn có khối lượng tín chỉ tổng cộng như thế nào
long_noisy|mình chọn bảng có học kỳ 7 và 8 trong PDF rồi, nhờ bạn đọc đúng dòng tổng tín chỉ của từng kỳ, đừng cộng nhầm những học phần có phương án 1 và 2 nhé
@uploaded_documents_compare_totals|mechatronics,electronics|2;25|hard|Hai PDF chương trình được tải lên ghi tổng tín chỉ lần lượt là bao nhiêu?|PDF cơ điện tử: 155; PDF điện tử viễn thông: 135, theo phạm vi cách tính được nêu trong mỗi file.
multi_hop|so hai file vừa tải lên thì tổng tín chỉ mỗi chương trình là bao nhiêu
code_switching|compare total program credits in the two uploaded PDFs
abbreviation|2 pdf vừa up tổng tc từng cái bn
colloquial|mình gửi hai bản chương trình rồi đó, cái nào tổng mấy tín vậy
lexical_mismatch|đối chiếu khối lượng tín chỉ toàn chương trình được công bố ở hai tài liệu đã chọn
long_noisy|mình muốn đặt hai PDF chương trình đang tải lên cạnh nhau để xem tổng tín chỉ của mỗi cái, bạn ghi riêng từng tài liệu và lưu ý nếu cách tính có phần chưa tính bổ trợ nhé
@uploaded_document_personal_result|none||medium|Tài liệu có thể xác định kết quả học tập cá nhân của tôi không?|Không có dữ liệu điểm cá nhân hoặc quyền truy cập hồ sơ trong corpus; không đoán từ quy định chung.
unanswerable|xem file rồi cho mình biết GPA hiện tại của mình đi
unanswerable|pdf vừa up có nói điểm thi của t là mấy không
unanswerable|trong file này kết quả học tập cá nhân em thế nào
unanswerable|read this PDF and tell me my current semester GPA
unanswerable|file có quy định rồi đó, t đỗ hay trượt kỳ này
unanswerable|mình chưa gửi bảng điểm cá nhân, chỉ có quy định trong file thì bạn biết điểm tổng mình không
@uploaded_document_current_status|none||hard|Một tài liệu tĩnh có thể xác nhận trạng thái hồ sơ cá nhân hiện tại không?|Thiếu hồ sơ cá nhân và dữ liệu trạng thái hiện tại; tài liệu quy định không đủ chứng cứ.
unanswerable|theo file vừa up thì hồ sơ của mình đã duyệt chưa
unanswerable|đọc pdf này xem mình đã nhận được tiền thưởng chưa
unanswerable|trong tài liệu này đơn đăng ký của t đang ở bước nào
unanswerable|can this PDF tell whether my application is approved right now
unanswerable|chỉ có quy định thôi nhưng kiểm tra giúp mình có tên trong danh sách nhận thưởng không
unanswerable|mình chưa cung cấp mã hồ sơ hay danh sách kết quả, từ bản hướng dẫn này bạn xác nhận em được duyệt chưa
@uploaded_document_contextless_reference|none||hard|Cần biết người dùng đang chỉ đoạn hoặc đối tượng nào.|Không có vùng chọn, dẫn chiếu hay lượt hội thoại trước để giải quyết từ đoạn này/cái đó.
ambiguous|đoạn đó là sao|Đoạn đó có nghĩa là gì?
ambiguous|chỗ này tính kiểu gì|Phần này tính thế nào?
ambiguous|hai cái kia khác nhau gì|Hai đối tượng đó khác nhau thế nào?
ambiguous|that part means what|Phần đó có nghĩa là gì?
ambiguous|ý số đó là sao vậy bạn|Con số đó có ý nghĩa gì?
ambiguous|thế cái kia có áp dụng không|Vậy điều kia có áp dụng không?
