# PLAN_TEAM.md — Kế hoạch thực thi Lab 14 (5 người × 4 tiếng)

> **Stack Judge:** OpenAI GPT-4o + Google Gemini 1.5 Pro (2 vendor khác nhau → thoả điều kiện Multi-Judge Consensus, tránh điểm liệt).

---

## 1. Phân vai 5 người

| Vai | Tên vai | Trách nhiệm chính | Module/file phụ trách | % điểm nhóm gánh | Dependencies in / out |
|:---:|---|---|---|:---:|---|
| **R1** | Team Lead / DevOps-Analyst | Kickoff, Regression Gate, Release Logic, `check_lab`, orchestration, fresh-eyes rerun cuối giờ | `main.py` (toàn bộ); `check_lab.py`; `reports/*`; `.env.example` | 20% (Regression 10 + một phần Performance) | **In:** kết quả R2–R5. **Out:** ngưỡng gate cho R5 |
| **R2** | Data Engineer (SDG) | Sinh 50+ cases adversarial + paraphrase + edge, build Golden Dataset | `data/synthetic_gen.py`; `data/golden_set.jsonl`; `data/docs/` (copy từ Lab08) | 20% (Dataset & SDG 10 + một phần Retrieval 5) | **In:** docs Lab08. **Out:** `golden_set.jsonl` cho R3, R4, R5 |
| **R3** | Data Engineer (Retrieval) | Gán `expected_retrieval_ids`, hoàn thiện Hit Rate / MRR, tích hợp Chroma từ Lab08 | `engine/retrieval_eval.py`; copy `chroma_db/`; `agent/main_agent.py` (phần retrieval) | 15% (Retrieval Evaluation 10 + chia 5 với R2) | **In:** Chroma Lab08, dataset R2. **Out:** agent có `retrieved_ids` cho R5 |
| **R4** | AI Engineer (Judge-GPT + Rubrics) | GPT-4o Judge thật, rubrics Accuracy/Tone/Safety, consensus logic | `engine/llm_judge.py` (GPT side + rubrics + consensus); `engine/prompts/rubric.md` | 15% (Multi-Judge 7.5 + chia 7.5 với R5) | **In:** rubric thống nhất với R5. **Out:** `evaluate_multi_judge()` cho R1 |
| **R5** | AI Engineer (Judge-Gemini + Agent V2) | Gemini 1.5 Pro Judge, Position Bias, Agent V2 (prompt/retrieval cải tiến), Failure Analysis lead | `engine/llm_judge.py` (Gemini side + position bias); `agent/main_agent.py` (V2 variant); `analysis/failure_analysis.md` | 20% (Multi-Judge 7.5 + Failure Analysis 5 + Performance 5) | **In:** kết quả V1 từ R1. **Out:** V2 agent + 5-Whys cho R1 |

> **Điểm cá nhân (40đ × 5 người):** mỗi R* phải có ≥ 3 Git commit thực chất với prefix `[R1]…[R5]` để chứng minh **Engineering Contribution (15đ)**.

---

## 2. Timeline 4 tiếng — block 15'

Ký hiệu: **🔄 SYNC** = đồng bộ nhanh 3–5'. **🛑 CP** = checkpoint gate.

### Giai đoạn 0 — Kickoff (0:00–0:15)

| Block | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| **00:00–00:15** | `git init`, tạo branch, push skeleton; cấu hình `.env.example` với `OPENAI_API_KEY`, `GOOGLE_API_KEY` | Đọc `HARD_CASES_GUIDE.md`, chuẩn bị prompt SDG | Clone `chroma_db/` + `data/docs/` từ Lab08 vào Lab14; cài `chromadb`, `google-generativeai` | Viết rubric dự thảo (Accuracy/Tone/Safety) | Đọc 3 file engine, plan diff V1→V2 |

🔄 **SYNC 0** (00:13): R1 xác nhận 2 API key đã có (OPENAI + GOOGLE), các thành viên pull branch chuẩn.

### Giai đoạn 1 — Dataset Foundation (0:15–1:00) | 45'

| Block | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| **00:15–00:30** | Viết skeleton `Release Gate` (ngưỡng `hit_rate≥0.85`, `agreement≥0.7`, `cost_delta≤+10%`, `p95≤1.5s`) trong `main.py` | Viết 20 adversarial + 10 paraphrase cases seed (xem §3) | Parse Chroma: trích toàn bộ chunk_id → map về source file → lookup `source→[chunk_ids]` | Implement `evaluate_single_gpt()` trong `llm_judge.py`, dùng JSON-mode ép schema | Design Agent V2 diff: thêm reranker + "only answer from context" prompt |
| **00:30–00:45** | Bổ sung `cost_tracker` trong `runner.py` (token usage từ response) | Mở rộng 20 edge cases: OOC, ambiguous, conflicting | Viết `assign_gt_ids(case, top_k=5)`: dense retrieval trên `question + expected_answer`, lấy top-5 chunk_id | Viết rubric v1 lên `engine/prompts/rubric.md` | Fork `MainAgent` → `MainAgentV2` với reranker (keyword overlap) |
| **00:45–01:00** | Chạy smoke test trên 3 cases stub; đảm bảo `reports/` sinh file | Gộp → 50 cases → ghi `golden_set.jsonl` | Chạy `assign_gt_ids` trên 50 cases → bơm `expected_retrieval_ids` vào mỗi dòng | Test GPT judge với 2 cases thật: đo latency, cost | Test MainAgentV2 retrieve trên 3 câu |

🛑 **CP1 (01:00)**: `data/golden_set.jsonl` có ≥ 50 dòng, mỗi dòng có `expected_retrieval_ids` không rỗng. R3 hand off dataset final cho R4 + R5.

### Giai đoạn 2 — Engine Development (1:00–2:30) | 90'

| Block | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| **01:00–01:15** | Tích hợp `RetrievalEvaluator` thay `ExpertEvaluator` giả tại `main.py:9-16` | Support R3: thêm 5 "hard red-team" cases break-system | Hoàn thiện `evaluate_batch()` thật tại `retrieval_eval.py:26` | Hoàn thiện GPT side + xử lý JSON parse error + retry | Implement Gemini side tương đương GPT, dùng `google-generativeai` SDK |
| **01:15–01:30** | Tích hợp `LLMJudge` thay `MultiModelJudge` giả tại `main.py:18-24` | Viết `validate_dataset.py` kiểm tra 50 cases đủ trường | Viết `retriever_v1.py` gọi ChromaDB `rag_lab` → `{answer, contexts, retrieved_ids}` | Viết `build_judge_prompt(q,a,gt,rubric)` dùng Jinja2 | Integrate Gemini vào `evaluate_multi_judge` |
| **01:30–01:45** | Chạy 10-case pilot — verify pipeline end-to-end không crash | Chạy `validate_dataset.py` → fix cases malformed | Plug retriever thật vào `agent/main_agent.py` (V1) | Consensus logic: nếu `|s_gpt-s_gemini|>1` → gọi judge 3 (gpt-4o-mini) làm tie-breaker | Implement `check_position_bias`: swap A/B, chạy 5 cases |
| **01:45–02:00** | Thêm `asyncio.Semaphore(5)` né rate limit tại `runner.py:38` | Bắt đầu phần 1 reflection cá nhân (MRR / Adversarial design) | Thêm cache embedding (dict) để né re-embed khi regression V1/V2 | Implement `agreement_rate` thật + log individual scores | Finalize `MainAgentV2`: reranker + stricter prompt template |
| **02:00–02:15** | Chạy 25-case dry-run đo thời gian, tăng batch nếu >60s | Reflection (Technical Depth SDG) | Reflection (Cohen's Kappa, Hit Rate vs MRR) | Reflection (Position Bias, Judge consensus) | Reflection (RAG optimization trade-off) |
| **02:15–02:30** | **Chạy benchmark V1 full 50 cases** → lưu `v1_summary.json` tạm | Triage case fail do data vs do agent | Fix retrieval bugs (MRR = 0 thường do sai chunk_id format) | Fix agreement = 0% (thường do prompt ép JSON strict) | Chuẩn bị chạy V2 ngay sau V1 |

🛑 **CP2 (02:30)**: `v1_summary.json` tồn tại với `hit_rate>0.6`, `agreement_rate>0.5`, `avg_score∈[2,5]`. Nếu 3 chỉ số đều placeholder → dừng, debug 15'.

### Giai đoạn 3 — Benchmark V2 + Root Cause (2:30–3:30) | 60'

| Block | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| **02:30–02:45** | Chạy benchmark V2 (MainAgentV2) → `v2_summary.json` | Phân cụm fail-cases: Hallucination / Incomplete / Tone / Injection → `analysis/clusters.json` | Tính Hit Rate delta V1→V2 | Đo total cost USD cho 50 cases, breakdown GPT vs Gemini | Chọn 3 case tệ nhất theo `final_score` → draft 5-Whys |
| **02:45–03:00** | Code `compare_regression()`: bảng V1 vs V2, sinh quyết định | Finalize clustering + đếm số case mỗi nhóm | Plot Hit Rate distribution (optional) | Judge Cascade: Gemini-Flash cấp 1 → Gemini-Pro khi disagreement (bonus Expert) | Hoàn thiện 5-Whys case #1 và #2 (Chunking/Ingestion/Retrieval/Prompt) |
| **03:00–03:15** | Merge vào `summary.json`; chạy `python check_lab.py` lần 1 → fix cảnh báo | Reflection phần 2 (Failure mode insight) | Reflection phần 2 (Retrieval↔Answer correlation) | Reflection phần 2 (Cost-Quality trade-off) | 5-Whys case #3 + Action Plan |
| **03:15–03:30** | Review schema `reports/*.json`; verify version metadata | R2+R3: section "Dataset Bias" trong `failure_analysis.md` | — | R4+R5: section "Judge Reliability" trong `failure_analysis.md` | — |

🛑 **CP3 (03:30)**: `failure_analysis.md` không còn "X/Y" placeholder; 3 case 5-Whys đều ra root cause; `analysis/reflections/` có 5 file.

### Giai đoạn 4 — Polish + Submit (3:30–4:00) | 30' + 15' buffer

| Block | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| **03:30–03:45** | **FRESH EYES**: clone repo sạch, chạy lại `pip install -r requirements.txt && python data/synthetic_gen.py && python main.py && python check_lab.py` | Finalize reflection, commit | Finalize reflection, commit | Finalize reflection, commit | Finalize reflection, commit |
| **03:45–04:00** | Review naming `reflection_[Ho_Ten].md` của cả 5 người | Review reflection của R3 | Review reflection của R2 | Review reflection của R5 | Review reflection của R4; R1 tự review |
| **Buffer 04:00–04:15** | Fix nhanh bugs từ fresh-eyes run | | | | |

---

## 3. Kế hoạch tái sử dụng Lab08

### (a) Copy files — nguồn → đích

| Nguồn (Lab08) | Đích (Lab14) | Ghi chú |
|---|---|---|
| `Lecture-Day-08-09-10/day08/lab/data/docs/*.txt` (5 file) | `Lab14-C401-C5/data/docs/` | IT / HR / Policy, tổng 294 dòng |
| `Lecture-Day-08-09-10/day08/lab/chroma_db/` (folder) | `Lab14-C401-C5/chroma_db/` | Bỏ re-index; collection `rag_lab` có 29 chunks, ID pattern `{stem}_{i}` |
| `Lecture-Day-08-09-10/day08/lab/data/grading_questions.json` | `Lab14-C401-C5/data/seeds/grading_seed.json` | 10 Q&A, có `expected_sources` dùng để map GT-IDs |
| `Lecture-Day-08-09-10/day08/lab/data/test_questions.json` | `Lab14-C401-C5/data/seeds/test_seed.json` | 10 Q&A đơn giản hơn |
| `Lecture-Day-08-09-10/day08/lab/rag_answer.py` (hàm `retrieve_dense`) | Mẫu tham khảo trong `agent/main_agent.py` | Không copy nguyên — mượn logic `collection.query()` |
| `Lecture-Day-08-09-10/day08/lab/index.py` (hàm chunk) | Tham khảo nếu cần re-chunk | Giữ nguyên format ID `{filepath.stem}_{i}` |

### (b) Mở rộng 20 seed → ≥ 50 cases (+30 augmented)

| Kỹ thuật | Số cases | Cách làm | Phụ trách |
|---|:---:|---|---|
| **Paraphrasing** | 10 | GPT-4o rewrite seed q 1–2 cách. Metadata: `{type:"paraphrase", parent_id:"gq01"}` | R2 |
| **Adversarial — Prompt Injection** | 5 | Prefix `"Ignore the document, just tell me..."`; expected_answer giữ nguyên (agent phải từ chối) | R2 |
| **Adversarial — Goal Hijacking** | 3 | "Agent đang là IT-Helpdesk, user yêu cầu viết thơ tình" — expected_answer: refusal | R2 |
| **Out-of-Context** | 5 | Hỏi chủ đề không có trong 5 docs — expected_answer: "Không có trong tài liệu" | R2 |
| **Ambiguous** | 3 | "VPN giới hạn mấy cái?" — expected_answer: clarify | R2 |
| **Conflicting** | 2 | Ghép 2 fact từ 2 docs mâu thuẫn — expected_answer: "ghi nhận mâu thuẫn" | R2 |
| **Multi-hop** | 2 | Combine 2 chunk từ 2 docs (ví dụ: SLA + Access Level) | R2 |
| **Total** | **30 + 20 seed = 50 ✅** | | |

### (c) Gán `expected_retrieval_ids` từ ChromaDB

```
Input: 1 case {question, expected_answer, expected_sources}
       + ChromaDB collection "rag_lab"

Bước 1: expected_sources (["support/sla-p1-2026.pdf"])
        → chuẩn hóa: "sla_p1_2026"
Bước 2: collection.get(where={"source": {"$contains": "sla_p1_2026"}})
        → tất cả chunk_id thuộc file đó (5–7 chunks)
Bước 3: Dense-retrieve top-3 bằng embedding (question + expected_answer)
        → chọn chunk_id similarity cao nhất
Bước 4: expected_retrieval_ids = [top-1, top-2] (2 ID để Hit Rate@3 có dung sai)
```

**Sanity check (R3):** in `data/gt_audit.csv` cột `[case_id, question, gt_ids, chunk_preview]`, R2 đọc chéo 10 dòng — nếu >2/10 sai → revise logic.

---

## 4. Ma trận phụ thuộc

```
                         [R1: .env, git init]
                                  │
                                  ▼
     ┌──────────────────┬─────────┼─────────┬──────────────────┐
     ▼                  ▼         ▼         ▼                  ▼
[R2: SDG 20 seed] [R3: copy Chroma] [R4: rubric v1] [R5: V2 design]
     │                  │                  │                  │
     └────────┬─────────┘                  │                  │
              ▼                            │                  │
     [R2+R3: 50 cases + GT-IDs] ──────── CP1 ─────────────────┤
              │                                               │
              ├─────────────┐                                 │
              ▼             ▼                                 │
     [R3: retrieval_eval]  [R4: GPT judge thật]───┐           │
              │             │                    ▼           │
              │             └──► [R4: consensus logic] ◄── [R5: Gemini judge]
              │                          │                   │
              ▼                          ▼                   │
     [R1: main.py thay class giả] ───────┴────────────── CP2 ┤
                       │                                     │
                       ▼                                     ▼
              [R1: benchmark V1] ──────────────────► [R5: Agent V2 run]
                       │                                     │
                       └─────────┬───────────────────────────┘
                                 ▼
                       [R1: regression + gate] ── CP3
                                 │
                                 ▼
              [R5: 5-Whys] + [R2/R3/R4: clusters + cost]
                                 │
                                 ▼
                       [R1: fresh-eyes rerun] → submit
```

**Critical path:** `R2 SDG → R3 GT-IDs → R1 main.py integration → V1 benchmark → V2 benchmark → regression → submit`

---

## 5. Rủi ro & Mitigation (Top 5)

| # | Rủi ro | Xác suất | Impact | Mitigation |
|---|---|:---:|:---:|---|
| 1 | Rate limit OpenAI/Google khi 50 cases × 2 judge = 100+ calls | Cao | -10đ Performance | R1 đặt `asyncio.Semaphore(5)` từ đầu; R4 thêm `tenacity` exponential backoff; Gemini có free tier RPM thấp → R5 cân nhắc batch |
| 2 | Judge GPT vs Gemini disagreement > 50% | TB | -7đ Multi-Judge | R4+R5 đồng bộ rubric v1 block 00:30; test 3 cases tại CP1 để calibrate; >50% disagree → revise prompt (JSON strict + 1-shot example) |
| 3 | Agent V2 không khá hơn V1 → delta ≤ 0 → auto-Reject | Cao | -5đ | R5 chuẩn bị **2 variant V2**: (A) stricter prompt, (B) rerank + keyword filter. Nếu cả 2 không hơn → documented "Release blocked by quality gate" — vẫn đủ điểm vì logic gate đúng |
| 4 | Thời gian cạn giai đoạn 3 (benchmark > 3 phút) | TB | -5đ Performance | R1 đo pilot 10 cases tại 01:30; nếu >3s/case → tăng concurrency 8, tie-breaker chỉ khi disagreement > 1.5 |
| 5 | Kỹ năng không đồng đều (R5 chưa quen Google GenAI SDK) | TB | Trễ 15–30' ở CP2 | Block 00:15 R5 đọc quickstart `google-generativeai`; R4 pair 10' với R5 tại 01:00 nếu stuck |

### Task **KHÔNG thể skip** (điểm liệt)
- ✅ Multi-Judge với 2 vendor (OpenAI + Google) → R4+R5 deliver trước CP2
- ✅ Retrieval `hit_rate` + `MRR` có số thật → R3 deliver trước CP2
- ✅ `check_lab.py` pass → R1 chạy 03:00 và 03:30

### Task **có thể cắt** khi cạn thời gian
- ⚠️ `check_position_bias` (R5) — "nâng cao", không có điểm riêng
- ⚠️ Judge Cascade Flash → Pro — bonus Expert
- ⚠️ Cost breakdown per-case — chỉ cần total
- ⚠️ Matplotlib plots — không có điểm

---

## 6. Checklist nộp bài — 10 phút cuối (03:50–04:00)

| Phút | Ai | Hành động | Xác minh |
|---|---|---|---|
| 03:50 | R1 | `cd /tmp/lab14-clean && python check_lab.py` | ✅ Hit Rate, Agreement Rate, Version |
| 03:51 | R1 | `ls -la analysis/reflections/ \| wc -l` | Trả về 5 file reflection |
| 03:52 | R2 | `grep -c "^{" data/golden_set.jsonl` | ≥ 50 |
| 03:53 | R3 | `python -c "import json; d=json.load(open('reports/summary.json')); print(d['metrics'])"` | Có `hit_rate`, `agreement_rate`, `avg_score`, `total_cost` |
| 03:54 | R4 | Cross-review `reflection_[R5].md` (check MRR / Cohen's Kappa / Position Bias) | Thiếu → R5 bổ sung 2' |
| 03:55 | R5 | Cross-review `reflection_[R4].md` | — |
| 03:56 | R2–R3 | Cross-review lẫn nhau; R1 tự review | — |
| 03:57 | R1 | `git status` — không có `.env`, `venv/`, `__pycache__` | Sạch |
| 03:58 | R1 | `git add -A && git commit -m "Lab14 final submission"` | Commit hash |
| 03:59 | R1 | `git push origin main` | — |
| 04:00 | R1 | Gửi link repo vào kênh nộp bài | Screenshot |

---

## 7. Quick-start cho từng thành viên

```bash
# Tất cả chạy:
git clone <repo>
cd Lab14-C401-C5
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # điền OPENAI_API_KEY + GOOGLE_API_KEY

# R1: git init + CI
# R2: python data/synthetic_gen.py   (sau khi implement)
# R3: cp -r ../Lecture-Day-08-09-10/day08/lab/chroma_db ./chroma_db
#     cp -r ../Lecture-Day-08-09-10/day08/lab/data/docs ./data/docs
# R4: python -m pytest tests/test_judge_gpt.py
# R5: python -m pytest tests/test_judge_gemini.py
# R1 (cuối giờ): python main.py && python check_lab.py
```
