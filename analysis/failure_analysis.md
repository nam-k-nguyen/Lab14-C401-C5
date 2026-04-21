# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark

| Chỉ số | V1 | V2 | Delta |
|--------|----|----|-------|
| **Tổng số cases** | 54 | 54 | — |
| **Pass / Fail** | 20 / 34 | 24 / 30 | +4 pass |
| **Hit Rate** | 0.463 | 0.537 | +7.4pp |
| **MRR** | 0.318 | 0.475 | +15.7pp |
| **LLM-Judge Score (avg)** | 2.83 / 5.0 | 2.88 / 5.0 | +0.05 |
| **Agreement Rate (GPT vs Gemini)** | 0.326 | 0.161 | -16.5pp |
| **Total Cost** | $0.184 | $0.197 | +7% |
| **P95 Latency** | 3.95s | 3.26s | -18% |

**Release Gate: ROLLBACK** — Hit Rate (0.537) chưa đạt ngưỡng 0.85, Agreement Rate (0.161) chưa đạt 0.70, P95 latency (3.26s) vượt ngưỡng 1.5s.

---

## 2. Phân nhóm lỗi (Failure Clustering)

| Nhóm lỗi | Số lượng (V2) | Nguyên nhân dự kiến |
|----------|:---:|---|
| **False Refusal** | ~15 | V2 strict prompt quá cứng — agent nói "không có thông tin" dù context đã có |
| **Retrieval Mismatch** | ~10 | Embedding không map đúng query về chunk liên quan, sai file nguồn |
| **Incomplete Answer** | ~5 | Agent trả lời thiếu bước trong quy trình nhiều điều kiện |

**Nhận xét:** False Refusal là lỗi chiếm đa số và nghịch lý — V2 cải thiện prompt để tránh hallucination nhưng lại sinh ra over-refusal. Đây là trade-off chưa được cân bằng.

---

## 3. Phân tích 5 Whys (3 case tệ nhất)

### Case #1: "Mức độ ưu tiên P1 có định nghĩa như thế nào?" — Score: 1.78/5

**Triệu chứng:** Agent trả lời "thông tin không có trong tài liệu" dù đã retrieve được chunk `sla_p1_2026_3` (Hit Rate = 1.0, MRR = 0.33 — document có nhưng ở vị trí 3).

1. **Why 1:** Agent không dùng được nội dung chunk `sla_p1_2026_3` để trả lời.
2. **Why 2:** Keyword reranker của V2 đưa `access_control_sop` chunks lên vị trí 1 và 2, đẩy chunk SLA xuống vị trí 3 — cuối danh sách context.
3. **Why 3:** Từ khóa "P1" ngắn, xuất hiện trong nhiều tài liệu khác nhau (access control cũng có nhắc đến mức độ ưu tiên), khiến lexical reranker không phân biệt được domain.
4. **Why 4:** LLM generation đọc context từ trên xuống, chunk quan trọng nhất bị đặt cuối → bị "lost in the middle", model không tổng hợp được.
5. **Why 5:** Không có cơ chế đảm bảo chunk từ đúng file nguồn luôn được ưu tiên khi `expected_sources` đã biết.

**Root Cause:** Keyword-overlap reranker thiếu domain-aware logic — không biết câu hỏi về SLA nên ưu tiên chunk từ `sla_p1_2026`, dẫn đến chunk đúng bị đặt sai vị trí.

---

### Case #2: "Khi nào quyền truy cập cần phải được thu hồi ngay lập tức?" — Score: 1.89/5

**Triệu chứng:** Agent trả lời "không có thông tin" dù chunk `access_control_sop_2` được retrieve đứng **vị trí 1** (Hit Rate = 1.0, MRR = 1.0 — retrieval hoàn hảo).

1. **Why 1:** Generation model từ chối trả lời dù context hoàn toàn đúng.
2. **Why 2:** V2 system prompt có rule "CHỈ sử dụng thông tin trong Context — không bịa đặt" → model interpret quá cứng, không nhận ra thông tin thật ra đang có.
3. **Why 3:** Nội dung chunk được trình bày dạng danh sách bullet list (`- Khi nhân viên nghỉ việc...`) — LLM không nhận dạng đây là câu trả lời trực tiếp cho câu hỏi.
4. **Why 4:** Prompt không có few-shot example hướng dẫn cách đọc và tổng hợp từ chunk có cấu trúc bullet/table.
5. **Why 5:** Không có bước post-check "nếu context có thông tin liên quan thì phải trả lời, không được từ chối".

**Root Cause:** Overly strict system prompt kết hợp thiếu few-shot example dẫn đến "false refusal" — lỗi nằm hoàn toàn ở tầng Prompting, không phải Retrieval.

---

### Case #3: "Sản phẩm nào không được hoàn tiền theo chính sách này?" — Score: 2.11/5

**Triệu chứng:** Agent không retrieve được chunk từ `policy_refund_v4` dù câu hỏi trực tiếp về chính sách hoàn tiền (Hit Rate = 0.0, MRR = 0.0 — lấy về `it_helpdesk_faq` và `access_control_sop`).

1. **Why 1:** Retrieval trả về sai tài liệu — `policy_refund_v4` không xuất hiện trong top-3.
2. **Why 2:** Embedding của câu hỏi "sản phẩm không được hoàn tiền" không có vector gần với các chunk trong `policy_refund_v4`.
3. **Why 3:** Fixed-size chunking cắt tài liệu theo số ký tự cố định, tách rời "danh sách sản phẩm không hoàn tiền" ra khỏi header "Chính sách hoàn tiền" — chunk thiếu ngữ cảnh.
4. **Why 4:** Chunk chứa danh sách sản phẩm chỉ có các tên sản phẩm, thiếu từ khóa "hoàn tiền" trong cùng một chunk → embedding không biết chunk này thuộc chủ đề hoàn tiền.
5. **Why 5:** Ingestion pipeline không inject metadata hoặc header của section vào từng chunk.

**Root Cause:** Fixed-size chunking strategy làm mất context — chunk bị tách khỏi header section, khiến embedding không hiểu chunk thuộc chủ đề gì. Cần Semantic/Recursive chunking với header injection.

---

## 4. Kế hoạch cải tiến (Action Plan)

| Ưu tiên | Hành động | Giải quyết vấn đề |
|:---:|---|---|
| 🔴 Cao | Thay Fixed-size chunking bằng **Recursive/Semantic Chunking** với header injection vào mỗi chunk | Root Cause Case #3 |
| 🔴 Cao | Thêm **few-shot examples** vào system prompt hướng dẫn cách đọc bullet list và table từ context | Root Cause Case #2 |
| 🟡 Trung bình | Nâng cấp reranker từ keyword-overlap lên **Cross-encoder** hoặc BM25 + semantic hybrid | Root Cause Case #1 |
| 🟡 Trung bình | Thêm bước **post-generation check**: nếu context liên quan và agent nói "không có thông tin" → flag để human review | Case #1 & #2 |
| 🟢 Thấp | Tối ưu tie-breaker judge: chỉ gọi `gpt-4o` khi delta > 1.5 thay vì > 1.0 → giảm ~30% cost từ $0.175 xuống ~$0.12 | Giảm chi phí |
| 🟢 Thấp | Thêm **embedding cache** cho các câu hỏi trùng lặp trong regression test | Giảm latency P95 |

---

## 5. Bài học rút ra cho nhóm

**Retrieval tốt không đủ — Generation cũng phải được kiểm soát.** Case #2 là ví dụ điển hình: Hit Rate = 1.0, MRR = 1.0 nhưng score chỉ 1.89/5. Nhóm ban đầu tập trung tối ưu retrieval (V2 reranker) mà chưa kiểm tra kỹ hành vi generation khi context có sẵn. Bài học: phải đánh giá từng tầng riêng biệt, không gộp chung.

**Strict prompt sinh ra lỗi mới.** V2 system prompt được thiết kế để chống hallucination, nhưng lại tạo ra false refusal — một dạng lỗi khác cũng nghiêm trọng không kém. Agreement Rate giảm từ 0.326 xuống 0.161 ở V2 là tín hiệu cảnh báo sớm nhưng nhóm chưa điều tra nguyên nhân kịp thời. Bài học: mọi thay đổi prompt phải đi kèm test adversarial ngay, không chờ đến cuối pipeline.

**Chunking là nền tảng, sai từ đầu thì sửa rất khó.** Case #3 lỗi xảy ra từ bước Ingestion — chunk bị tách khỏi context header — và không có cách nào sửa ở tầng retrieval hay generation. Nhóm tái sử dụng ChromaDB từ Lab08 mà không kiểm tra lại chiến lược chunking có phù hợp với dataset mới. Bài học: audit chunking quality phải là bước đầu tiên của bất kỳ RAG project nào.

**Dataset đa dạng mới phản ánh đúng thực tế.** 50 synthetic cases từ LLM cho hit_rate/MRR trông ổn, nhưng 5 adversarial cases viết tay lộ ra những lỗi hệ thống mà test tự động bỏ qua. Trong môi trường production, người dùng thật sẽ hỏi đúng kiểu adversarial này.
