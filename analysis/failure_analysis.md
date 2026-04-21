# Báo cáo Phân tích Thất bại (Failure Analysis Report)

> Tất cả số liệu dưới đây được tính từ `reports/benchmark_results.json` và `reports/summary.json` (V2 Agent, 54 cases, benchmark timestamp 2026-04-21 17:48:27).

## 1. Tổng quan Benchmark

| Metric | V1 | V2 | Delta |
|---|:---:|:---:|:---:|
| **Total cases** | 54 | 54 | — |
| **Pass / Fail** | — | **24 / 30** | — |
| **Fail rate** | — | **55.6%** | — |
| **Hit Rate** | 0.463 | **0.537** | +7.4% |
| **MRR** | 0.318 | **0.475** | +15.7% |
| **Judge avg_score** | 2.832 / 5 | **2.881 / 5** | +0.05 |
| **Agreement rate** | 0.326 | **0.161** | −0.16 |
| **Total cost** | $0.184 | **$0.197** | +7.0% |
| **p95 latency** | 3.95s | **3.26s** | −0.69s |

### Score distribution (V2, 54 cases)

| Bucket | Count | % |
|:---:|:---:|:---:|
| < 2 | 2 | 3.7% |
| 2 – 3 | 28 | 51.9% |
| 3 – 4 | 20 | 37.0% |
| 4 – 5 | 4 | 7.4% |

Kết luận: **đa số case nằm ở vùng "gần pass nhưng chưa đủ"** (2–3), cho thấy Agent có hiểu câu hỏi nhưng trả lời không đủ tốt chứ không phải hoàn toàn sai.

### Release Gate decision: **ROLLBACK**

Từ `summary.json`:
- ✅ `quality_improved` (V2 > V1)
- ❌ `hit_rate_ok` (0.537 < 0.85)
- ❌ `agreement_ok` (0.161 < 0.70)
- ✅ `cost_within_budget` (+7% ≤ +10%)
- ❌ `latency_p95_ok` (3.26s > 1.5s)

3/5 gate fail → V2 không được deploy. **Gate logic chạy đúng**, phát hiện đúng vấn đề.

---

## 2. Phân nhóm lỗi (Failure Clustering — 30 fail cases)

| Nhóm lỗi | Số lượng | % / fail | Triệu chứng |
|---|:---:|:---:|---|
| **Retrieval miss** | 20 | 67% | `hit_rate=0` — không retrieve được chunk từ source đúng. Agent buộc phải từ chối hoặc bịa |
| **Over-refusal** | 8 | 27% | `hit_rate=1` nhưng Agent trả lời "xin lỗi, không có trong tài liệu". LLM từ chối dù context có thông tin |
| **Low quality** | 2 | 7% | Có trả lời nhưng score < 3, thiếu chi tiết hoặc không đủ cấu trúc |

**Judge disagreement cao bất thường: 48/54 cases (89%) có agreement rate < 0.5** — GPT-4o-mini và Gemini-2.5-flash-lite bất đồng gần như toàn bộ benchmark. Đây là tín hiệu: hoặc rubric không rõ ràng, hoặc 2 model có bias khác nhau về "có coi refusal là câu trả lời tốt không". Tie-breaker (gpt-4o) fire khoảng 30% cases (dựa vào cost breakdown $0.175 / 54 cases).

---

## 3. Phân tích 5 Whys (3 case tệ nhất V2)

### Case #1 — Score 1.78 / 5, hit_rate = 1.0, Δ judge = 3.33

**Question:** *"Mức độ ưu tiên P1 có định nghĩa như thế nào?"*

**Agent answer:** *"Xin lỗi, nhưng thông tin về định nghĩa mức độ ưu tiên P1 không có trong tài liệu đã cung cấp..."*

**Retrieved IDs:** `access_control_sop_6`, `access_control_sop_2`, `sla_p1_2026_3`

**5 Whys:**
1. **Symptom:** Agent từ chối trả lời dù có chunk từ `sla_p1_2026` được retrieve (hit_rate=1)
2. **Why:** Trong top-3 có 2 chunk sai chủ đề (`access_control_sop_2, 6`) và 1 chunk đúng (`sla_p1_2026_3`) nằm ở vị trí **thứ 3**
3. **Why:** Keyword-overlap rerank không đẩy `sla_p1_2026_3` lên top-1 vì từ "P1" không đủ discriminative (xuất hiện trong cả access_control context)
4. **Why:** LLM nhìn thấy context bị "pha loãng" bởi 2 chunk sai chủ đề → không đủ tin cậy để trích xuất định nghĩa P1 từ chunk đúng
5. **Why (deeper):** System prompt V2 *"CHỈ sử dụng thông tin trong Context — không bịa đặt"* quá nghiêm khắc, khiến LLM ưu tiên từ chối thay vì suy luận từ chunk đúng duy nhất

**Root cause:** **V2 system prompt quá strict** kết hợp với **rerank keyword không đủ precision** → over-refusal ngay cả khi retrieval có đúng thông tin.

---

### Case #2 — Score 1.89 / 5, hit_rate = 1.0, Δ judge = 3.67

**Question:** *"Khi nào quyền truy cập cần phải được thu hồi ngay lập tức?"*

**Agent answer:** *"Xin lỗi, nhưng thông tin về việc thu hồi quyền truy cập ngay lập tức không có trong tài liệu..."*

**Retrieved IDs:** `access_control_sop_2`, `policy_refund_v4_0`, `access_control_sop_6`

**5 Whys:**
1. **Symptom:** Giống Case #1 — agent từ chối dù retrieve được chunks từ đúng source (`access_control_sop`)
2. **Why:** `policy_refund_v4_0` (chunk SAI source) chen vào vị trí thứ 2 → context nhiễu
3. **Why:** Embedding model `all-MiniLM-L6-v2` (English-focused) không phân biệt tốt giữa "thu hồi quyền truy cập" vs "hoàn tiền" trong Vietnamese — cả 2 có signal "thu hồi/trả lại" chung
4. **Why:** Không có filter theo source khi retrieve top-k → chunks từ tài liệu không liên quan có thể lọt vào
5. **Why:** Chunking của Lab08 không có metadata ngữ nghĩa chi tiết (chỉ có `source` và `section`), không có field như `topic` hoặc `doc_type` để pre-filter

**Root cause:** **Embedding multilingual yếu cho Vietnamese** + **không có pre-filter theo topic** → chunk sai source lọt vào top-k.

---

### Case #3 — Score 2.11 / 5, hit_rate = 0.0, Δ judge = 3.0

**Question:** *"Sản phẩm nào không được hoàn tiền theo chính sách này?"*

**Agent answer:** *"Xin lỗi, nhưng thông tin về sản phẩm không được hoàn tiền không có trong tài liệu..."*

**Retrieved IDs:** `it_helpdesk_faq_0`, `access_control_sop_1`, `access_control_sop_6`

**5 Whys:**
1. **Symptom:** `hit_rate = 0` — không chunk nào từ `policy_refund_v4` được retrieve mặc dù câu hỏi rõ ràng về refund
2. **Why:** Top-3 chunks đều từ `it_helpdesk_faq` và `access_control_sop` — hoàn toàn sai source
3. **Why:** Embedding `all-MiniLM-L6-v2` map "hoàn tiền" xa với "refund" trong documents Vietnamese/English mixed
4. **Why:** Collection có metadata `source` nhưng retrieval không dùng filter — chỉ dùng pure semantic similarity
5. **Why:** Chunking của `policy_refund_v4` có thể không chứa từ khóa cụ thể về "sản phẩm không hoàn tiền" (có thể phrase khác: "exclusion list", "non-refundable items")

**Root cause:** **Embedding model không đủ mạnh cho cross-language Vietnamese↔English** + **không có hybrid retrieval (BM25 + dense)** để cover case keyword discriminative.

---

## 4. Kế hoạch cải tiến (Action Plan)

### Ưu tiên cao (address 27% + 67% = 94% fail)

- [ ] **Nới lỏng V2 system prompt** — cho phép LLM suy luận từ context khi có chunk liên quan, thay "CHỈ sử dụng" → "Ưu tiên sử dụng context, nếu thiếu chi tiết có thể nói rõ mức độ chắc chắn". Address 8 over-refusal cases.
- [ ] **Thay embedding sang model tốt hơn cho Vietnamese** — ví dụ `bge-m3` hoặc `multilingual-e5-large`. Address 20 retrieval miss cases.
- [ ] **Thêm hybrid retrieval (BM25 + dense)** — BM25 giúp keyword-heavy queries ("P1", "refund", tên cụ thể). Address Case #3 kiểu queries.

### Ưu tiên trung bình (address retrieval precision)

- [ ] **Cross-encoder reranker** (ví dụ `bge-reranker-v2-m3`) thay keyword-overlap rerank — bắt được semantic similarity tốt hơn cho top-k.
- [ ] **Metadata-based pre-filter** — phân loại question bằng intent classifier nhỏ, filter collection theo source trước khi semantic search.

### Ưu tiên thấp (gate compliance)

- [ ] **Giảm p95 latency** từ 3.26s xuống < 1.5s — chủ yếu do tie-breaker fire 30% cases. Solutions: (a) tăng agreement threshold trước tie-breaker, (b) làm tie-breaker async background, (c) cache judge results cho similar questions.
- [ ] **Tăng agreement rate** lên > 0.7 — root cause là rubric có 3 tiêu chí (Accuracy/Tone/Safety) nhưng 2 Judge weight khác nhau. Solution: fix rubric ràng buộc hơn về weight + cho ví dụ chấm.

### Không ưu tiên (đã pass ngưỡng)

- [x] Cost — $0.197 cho 54 cases V2, đã dưới $10 budget rộng
- [x] Quality improved V2 > V1 — gate pass mục này

---

## 5. Bài học rút ra cho nhóm

1. **Test prompt strictness bằng dataset adversarial** — V2 prompt nghe có vẻ tốt ("chỉ dùng context, không bịa") nhưng thực tế khiến agent **over-refuse 15% cases**. Lần sau: có A/B test prompt trên 10 cases trước khi chạy full.
2. **Judge disagreement cao không phải bug mà là signal** — 89% disagreement cho thấy 2 Judge có world-view khác nhau về câu trả lời tốt. Đây là **lý do cần multi-judge** thay vì tin 1 model.
3. **Retrieval là bottleneck lớn nhất** — 20/30 fail (67%) là do retrieval sai, không phải generation kém. Đầu tư vào retrieval (embedding tốt hơn, hybrid search, reranker) sẽ cải thiện nhiều hơn là tuning prompt.
