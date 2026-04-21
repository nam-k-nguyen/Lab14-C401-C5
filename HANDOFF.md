# HANDOFF — Lab 14 còn lại

> R1 tạm dừng. File này mô tả **chính xác** những gì cần làm tiếp để hoàn thành và nộp bài.

## Tình trạng main (commit `437bdf3`)

✅ **Code sẵn sàng chạy end-to-end:**
- Dataset: 55 cases (`data/golden_set.jsonl`)
- Chroma: collection `rag_lab`, 29 chunks
- Retrieval eval: `score_one`, Hit Rate, MRR
- Multi-Judge: GPT-4o-mini + Gemini 1.5 Pro thật, agreement + tie-breaker khi Δ > 1
- MainAgentV2: Chroma + keyword rerank
- Release Gate: 5 ngưỡng, CostTracker, Semaphore(5)

⏳ **Còn thiếu** (ưu tiên từ trên xuống):

---

## 1. R3 — viết `data/assign_gt_ids.py` (BLOCKER, ~15')

Hiện `expected_retrieval_ids` trong `golden_set.jsonl` **rỗng toàn bộ** → `hit_rate = 0` dù code đúng. Skeleton:

```python
# data/assign_gt_ids.py
import json, chromadb, os

client = chromadb.PersistentClient(path="chroma_db")
col = client.get_collection("rag_lab")

def enrich(case, top_k=2):
    sources = case.get("expected_sources", [])
    if not sources:
        return []
    # Lọc chunks thuộc các file nguồn
    src = sources[0]
    all_match = col.get(where={"source": {"$contains": src}})
    if not all_match["ids"]:
        return []
    # Dùng câu hỏi + expected_answer làm query
    q = case["question"] + " " + case.get("expected_answer", "")
    res = col.query(query_texts=[q], n_results=top_k,
                    where={"source": {"$contains": src}})
    return res["ids"][0] if res["ids"] else []

with open("data/golden_set.jsonl", encoding="utf-8") as f:
    cases = [json.loads(l) for l in f if l.strip()]
for c in cases:
    c["expected_retrieval_ids"] = enrich(c)
with open("data/golden_set.jsonl", "w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print("Done. Sample:", cases[0]["expected_retrieval_ids"])
```

Chạy: `python data/assign_gt_ids.py`. Sanity: 5 dòng ngẫu nhiên phải có 1-2 chunk ID (không `[]`).

Commit:
```bash
git checkout main && git pull
git add data/assign_gt_ids.py data/golden_set.jsonl
git commit -m "[R3] data: enrich expected_retrieval_ids via Chroma dense retrieval"
git push
```

---

## 2. Chạy full benchmark (người có .env với OPENAI_API_KEY + GOOGLE_API_KEY)

```bash
# Install deps nếu chưa:
venv/Scripts/pip.exe install google-generativeai sentence-transformers

# Chạy — mất ~5-15' tuỳ rate limit. Tốn ~$0.20-0.40 API cost
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe -X utf8 main.py

# Xác nhận output:
ls reports/           # phải có summary.json + benchmark_results.json
python check_lab.py   # phải ra 3 ✅
```

**Nếu Gemini rate limit** (free tier 2 RPM): sửa [main.py](main.py) trong `run_benchmark_with_results`, đổi `runner.run_all(dataset)` → `runner.run_all(dataset, concurrency=2)`.

Commit:
```bash
git add reports/
git commit -m "[TEAM] data: commit real benchmark reports V1 vs V2"
git push
```

---

## 3. R5 — điền `analysis/failure_analysis.md` bằng số thật (~20')

Hiện file còn placeholder "X/Y", "[Mô tả ngắn]". Sau khi có `reports/benchmark_results.json`:

```bash
# Lấy 3 case tệ nhất:
python -c "
import json
data = json.load(open('reports/benchmark_results.json'))
all_cases = data.get('v2', data) if 'v2' in data else data
worst = sorted(all_cases, key=lambda r: r['judge']['final_score'])[:3]
for c in worst:
    print('---')
    print('Q:', c['test_case'])
    print('A:', c['agent_response'][:200])
    print('Score:', c['judge']['final_score'])
    print('IDs:', c.get('retrieved_ids'))
"
```

Điền vào `failure_analysis.md`:
- Tỉ lệ Pass/Fail: count từ `status` field
- Faithfulness/Relevancy: không có trực tiếp → dùng `avg_score` và `agreement_rate` thay
- 3 case 5-Whys: mô tả symptom + trace tới root cause (Chunking/Retrieval/Prompting)
- Action plan: ít nhất 3 mũi tên cụ thể

---

## 4. Reflections cá nhân — R1, R2, R3, R5 (~25'/người, song song)

Mỗi người tạo `analysis/reflections/reflection_[Ho_Ten].md`. Template lấy từ [reflection_Nguyen_Minh_Hieu.md](analysis/reflections/reflection_Nguyen_Minh_Hieu.md).

**Chủ đề gợi ý theo role** (bắt buộc cover ≥ 2 khái niệm technical để lấy 15đ Technical Depth):

| Vai | Chủ đề technical | Bằng chứng commit |
|---|---|---|
| **R1** | Release Gate design / Cost-Quality trade-off / Integration patching | `[R1]*`, `[R1-patch]*`, `[R1-ops]*` |
| **R2** | SDG adversarial design / Hard case coverage / Dataset validation | `feat(r2):*`, `fix(r2):*` |
| **R3** | Hit Rate vs MRR / Dense retrieval enrichment / Chroma collection mapping | `Update retrieval_eval.py`, `Update main_agent.py` |
| **R5** | Gemini vs GPT Judge agreement / Position Bias / Keyword rerank rationale | `Update agentv2, gemini judge, requirements` |

Naming: bỏ dấu tiếng Việt, dùng underscore. Ví dụ `reflection_Nguyen_Van_A.md`.

---

## 5. Checklist nộp bài cuối (~10')

Ai làm final submit chạy:
```bash
# 1. Pull latest main
git checkout main && git pull

# 2. Verify
ls analysis/reflections/                    # phải có 5 file (R1-R5)
wc -l data/golden_set.jsonl                 # phải 55
head -1 data/golden_set.jsonl | python -c "import json,sys; print(json.loads(sys.stdin.read())['expected_retrieval_ids'])"  # phải > 0
python check_lab.py                         # phải pass hết ✅
git status                                  # không có .env, __pycache__, venv trong stage

# 3. Fresh-eyes: clone repo sạch ra /tmp, chạy lại
cd /tmp && git clone <repo-url> lab14-verify
cd lab14-verify && python -m venv venv && venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env  # điền key
python data/synthetic_gen.py    # optional nếu cần tái tạo
python data/assign_gt_ids.py
python main.py
python check_lab.py             # phải ra 🚀 Bài lab đã sẵn sàng
```

Final commit + submit link repo.

---

## Thứ tự execution đề xuất

1. **R3** làm task 1 ngay (unblocks mọi thứ sau)
2. **Ai rảnh + có API key** chạy benchmark task 2 sau khi R3 xong
3. **R5** làm task 3 sau khi có reports
4. **R1, R2, R3, R5** viết reflection song song task 4
5. **Ai làm submit cuối** chạy task 5

Nếu kẹt bất cứ đâu: check commit `[R1-patch] agent: fix R3 merge blockers` (`b9e3210`) để xem ví dụ fix pattern, hoặc [PLAN_TEAM.md](PLAN_TEAM.md) để rõ responsibility matrix.

---

## Rủi ro còn lại

| Rủi ro | Mitigation |
|---|---|
| Gemini rate limit (2 RPM free) | `concurrency=2` hoặc dùng `gemini-1.5-flash` model (sửa `LLMJudge.__init__`) |
| OpenAI billing surprise | Trước khi full benchmark, xem dashboard OpenAI, set hard limit $5/day |
| Hit rate = 0 toàn bộ | Verify `assign_gt_ids.py` chạy xong có kết quả, Chroma `rag_lab` có đúng IDs |
| Agreement = 0 toàn bộ | Judge prompt fail JSON parse. Kiểm tra 1 case trong `benchmark_results.json` → `individual_scores.gpt.error` và `individual_scores.gemini.error` |
| Pipeline chậm > 10' | Giảm dataset xuống 30 cases bằng `dataset = dataset[:30]` sau khi load |

Pipeline chính đã test pass smoke — các rủi ro trên đều là external (API) chứ không phải code.
