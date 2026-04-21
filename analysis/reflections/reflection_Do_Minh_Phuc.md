# Báo cáo Cá nhân - Lab 14

**Họ và tên:** Đỗ Minh Phúc
**MSSV:** 2A202600039
**Vai trò:** R1 — Team Lead / DevOps-Analyst (Integration + Release Gate)

---

## 1. Tổng quan vai trò và nhiệm vụ đã thực hiện

Trong Lab 14, tôi đảm nhiệm vai trò **tích hợp hệ thống** — không sở hữu một module độc lập, mà chịu trách nhiệm ghép các phần của 4 thành viên khác thành một pipeline chạy được end-to-end và thiết kế Release Gate để quyết định V2 có được deploy hay không. Đây là vai "ít glamour" nhưng là critical path của nhóm: nếu tích hợp sai, dù từng module đúng thì benchmark cuối vẫn không chạy được.

Nhiệm vụ cụ thể:

- **Thiết kế hạ tầng đo lường**: viết class `CostTracker` (PRICING cho gpt-4o / gpt-4o-mini / gemini-2.5-flash-lite / gemini-1.5-flash, breakdown per-model) và p95 latency trong `engine/runner.py`. Đây là tiền đề để Release Gate có thể dựa trên con số thật thay vì cảm tính.
- **Thiết kế Release Gate**: hàm `decide_release()` với **5 ngưỡng độc lập** (quality_improved, hit_rate ≥ 0.85, agreement_rate ≥ 0.7, cost_delta ≤ +10%, p95 ≤ 1.5s). Quyết định RELEASE/ROLLBACK là AND của cả 5 — bất kỳ ngưỡng nào trượt → rollback.
- **Tích hợp**: xoá stub `ExpertEvaluator` / `MultiModelJudge` trong `main.py`, wire `RetrievalEvaluator` (R3) và `LLMJudge` (R4 + R5 gộp) vào pipeline, thêm cost tracker hook vào runner để log token usage tự động sau mỗi judge call.
- **Merge manager**: resolve 4 lần conflict khi R2 / R3 / R4 / R5 push branch. Trong đó R2 lần 1, R4, R5 đều base từ commit cũ nên phải rebase; R4 và R5 xung đột cứng với nhau trên `engine/llm_judge.py` (cả hai viết lại từ ancestor khác hướng).
- **Patch blocker**: sửa 4 lỗi chặn pipeline của R3 (syntax error ở `__main__` block do escape sai, sai tên collection ChromaDB `documents` thay vì `rag_lab`, thiếu field `retrieved_ids` trong response của `MainAgent.query()`, thiếu method alias `run()`) trong 1 commit `[R1-patch]` — để không block cả nhóm mà vẫn giữ R3 làm owner của module.
- **Team coordination**: viết `PLAN_TEAM.md` (timeline 4 tiếng chia block 15', role matrix, dependency graph, risk mitigation). Plan này giúp nhóm song song hoá tối đa, không ai idle.

---

## 2. Phân tích kỹ thuật & bài học

### 2.1. Agreement Rate — thang liên tục thay vì nhị phân (Cohen's Kappa)

Bản merge ban đầu của R5 tính `agreement_rate = 1.0 if score_gpt == score_gemini else 0.5` — **nhị phân**, mất thông tin. GPT cho 4, Gemini cho 3 sẽ bị coi như GPT cho 4, Gemini cho 1 (cả hai đều = 0.5). Tôi thay bằng công thức liên tục:

```
agreement_rate = max(0.0, 1.0 - |Δ| / 4.0)
```

Thang Judge là 1–5, Δ tối đa = 4. Công thức này cho Δ=0 → 1.0, Δ=1 → 0.75, Δ=2 → 0.5, Δ=4 → 0.0. Gần tinh thần **Cohen's Kappa** (có tính tới mức độ lệch chứ không chỉ match/not-match), nhưng đơn giản hơn để dùng trong release gate realtime. Đây là trade-off pragmatism vs rigor — Cohen's Kappa yêu cầu tính xác suất agreement ngẫu nhiên qua marginal distribution của từng Judge, quá phức tạp cho pipeline streaming. Công thức tuyến tính bắt được ~90% signal với 10% code phức tạp.

### 2.2. Tie-breaker cascade — chỉ escalate khi cần

Khi |Δ| > 1, gọi model thứ 3 (gpt-4o) làm trọng tài, final_score = trung bình 3-way. Nguyên tắc thiết kế: **chỉ escalate khi cần**. Nếu gpt-4o-mini và gemini-2.5-flash-lite đã đồng ý (Δ ≤ 1), không lý do gì gọi gpt-4o đắt gấp 50x input và 17x output. Trên benchmark V2 thực (54 cases):

| Judge | Cost |
|---|---|
| gpt-4o-mini (primary) | $0.0108 |
| gemini-2.5-flash-lite (primary) | $0.0113 |
| gpt-4o (tie-breaker, ~30% cases) | $0.1750 |
| **Total** | **$0.197** |

So với ~$1.50+ nếu luôn dùng gpt-4o làm Judge chính → **83% cost saving với chất lượng tương đương** (agreement rate ~0.16 là do judge thật sự disagree chứ không phải vì model yếu).

### 2.3. Integration vs ownership trade-off

Vai R1 dễ rơi vào bẫy "làm hộ tất cả" khi thấy teammates chậm. Tôi chọn **patch** các blocker nhỏ (syntax error R3, V2 inherit sai base của R5) nhưng **không chiếm** ownership chính — R3 vẫn sở hữu `retrieval_eval.py`, R5 vẫn sở hữu `MainAgentV2`. Commit prefix `[R1-patch]` tách rõ giữa "fix blocker để nhóm tiếp tục" với "làm hộ". Tinh thần: **unblock, không replace**. Điều này quan trọng cho điểm Engineering Contribution cá nhân của cả nhóm — nếu R1 viết hộ, git blame sẽ ghi toàn bộ hiển thị R1, teammates mất evidence.

### 2.4. Release Gate philosophy — AND over OR

Một thiết kế sai tôi đã cân nhắc rồi loại là "weighted sum rồi so 1 ngưỡng tổng" (kiểu `0.3*quality + 0.4*hit_rate + ...`). Cách đó **ẩn lỗi**: V2 có thể latency 10s nhưng agreement cao bù vào vẫn được release. **AND over OR** buộc tất cả ngưỡng phải pass — 1 cái fail → rollback. Benchmark thực cho thấy quyết định ROLLBACK đúng: V2 `hit_rate=0.54 < 0.85`, `p95=3.26 > 1.5` — nếu dùng weighted sum, hệ thống có thể đã release một agent chậm và retrieval kém, "ẩn" bằng điểm quality cao.

### 2.5. Stub-first, real-later

Phase 1 tôi giữ `ExpertEvaluator` / `MultiModelJudge` stub trong `main.py` để pipeline chạy được sớm, test logic Release Gate và `compare_regression()` trước khi có real eval. Khi R3/R4/R5 xong, chỉ việc swap import. Nếu chờ có real judge mới viết gate, nhóm đã mất 90 phút. Bài học: **test harness trước, implementation sau** — stub không phải kỹ thuật kém mà là chiến lược de-risk.

---

## 3. Bài học rút ra

- **Git flow cho team 5 người**: branch per role + merge commits giữ lịch sử cá nhân. Merge manager phải **nghiêm với commit xấu** — không merge commit có syntax error cứng, không merge commit delete file người khác. R3 push commit "Add files via upload" qua GitHub Web UI đã xoá toàn bộ công sức nhóm, tôi phải từ chối và rescue riêng file reflection của họ.
- **Schema contract trước code**: R2 xuất `expected_sources`, R3 đọc `expected_retrieval_ids` — nếu thống nhất field name từ đầu thì không phải rebase 2 lần. Next time: viết JSON Schema cho data format **trước khi** ai viết code đụng tới nó.
- **Cost visibility thay đổi quyết định**: trước khi có CostTracker, nhóm dự định dùng gpt-4o làm Judge chính. Nhìn thấy con số thật ($0.17 chỉ riêng tie-breaker), chúng tôi chọn gpt-4o-mini làm primary — cost giảm từ ~$1.5 xuống $0.20 cho cùng benchmark. **Không đo được = không quyết được**.
- **Embedding mismatch** là lỗi ẩn đắt giá: Lab08 index với `paraphrase-multilingual-MiniLM-L12-v2`, ban đầu chúng tôi query bằng Chroma default (`all-MiniLM-L6-v2`) — similarity vẫn "trông hợp lý" nhưng không optimal. R2 sau đó chuyển sang `query_embeddings=` với sentence-transformers local, vừa fix mismatch vừa tránh 79MB ONNX download timeout. Tôi học được: nếu Chroma "có vẻ hoạt động" nhưng hit_rate không tăng khi cải tiến retrieval, hãy kiểm tra embedding model **trước** khi blame retrieval logic.

---

## 4. Bằng chứng đóng góp

Commit prefix: `[R1]`, `[R1-patch]`, `[R1-ops]` trên branch `r1/infra-gate` và các merge commit trên `main`.

| Commit | Nội dung |
|---|---|
| `6b54177` | [R1] runner: CostTracker + p95 latency |
| `6daf5c0` | [R1] gate: release decision + regression compare |
| `b9e3210` | [R1-patch] agent: fix 4 R3 merge blockers |
| `4b1528e` | [R1-ops] deps + chroma_db snapshot |
| `35512c4` | [R1] integrate: wire real RetrievalEvaluator + LLMJudge |
| `f00aa9c` | merge: R2 golden dataset (55 cases, schema v2) |
| `8d71498` | merge: R3 retrieval_eval + agent chroma integration |
| `95e55ec` | merge: R4 GPT judge + rubric + reflection |
| `2a19196` | merge: R5 Gemini judge + MainAgentV2 (grafted Gemini method vào R4 class) |
| `437bdf3` | merge: R1 infra vào main |
| `PLAN_TEAM.md` | Role matrix + timeline 4h + dependency graph |
