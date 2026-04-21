
# Personal Reflection Report - Lab 14

**Full Name:** LÊ TÚ NAM
**Student ID:** 2A202600109  

**Role:** R3-Data Engineer (Retrieval)

---

1. Role Overview and Tasks Performed

In Lab 14, I was responsible for the Retrieval Evaluation pipeline of the RAG system. My primary focus was to ensure that the retrieval stage is measurable, reliable, and analyzable, rather than treating it as a black box.

My key contributions include:

Designing and assigning expected_retrieval_ids for each evaluation sample to enable objective measurement of retrieval correctness.
Implementing the RetrievalEvaluator in engine/retrieval_eval.py, including:
Hit Rate@k
Mean Reciprocal Rank (MRR)
Modifying the Agent (agent/main_agent.py) to return retrieved_ids alongside generated answers, making retrieval observable.
Integrating Chroma Vector Database (from Lab08) to ensure consistent and reproducible retrieval results.
Building an async batch evaluation pipeline to efficiently evaluate large datasets.
2. Technical Analysis and Reflections
2.1. Retrieval Observability & Evaluation Design

A critical improvement I implemented was making retrieval explicitly observable.

Instead of only returning generated answers, the Agent now returns:
{
  "answer": "...",
  "retrieved_ids": ["chunk_1", "chunk_5"]
}
This enables direct comparison with:
{
  "expected_retrieval_ids": ["chunk_1"]
}
Insight: Without retrieved_ids, it is impossible to determine whether an incorrect answer is caused by:
retrieval failure
or generation hallucination

This design is essential for downstream Root Cause Analysis.

2.2. Hit Rate & MRR as Core Retrieval Metrics

I implemented two key metrics:

Hit Rate@k: Measures whether at least one relevant chunk appears in the top-k retrieved results.
MRR (Mean Reciprocal Rank): Measures how early the first correct chunk appears.

Reflection:

Hit Rate indicates coverage
MRR indicates ranking quality

During testing, I observed:

High Hit Rate but low MRR → relevant chunks exist but are poorly ranked
Low Hit Rate → retrieval failure (embedding or chunking issue)

This distinction is crucial for diagnosing system weaknesses.

2.3. Chroma Integration & ID Consistency

I reused the Chroma database from Lab08 to ensure consistency in retrieval behavior.

Key implementation detail:

Each chunk in Chroma must include a unique identifier:
metadata = {"id": chunk_id}
During retrieval:
retrieved_ids.append(doc.metadata["id"])

Reflection:
If IDs are not preserved:

Retrieval cannot be evaluated
Metrics like Hit Rate and MRR become meaningless

This is a common failure point in RAG systems where developers only retrieve text without tracking identity.

2.4. Async Evaluation for Scalability

To support large-scale evaluation (50+ samples), I implemented an async evaluation pipeline:

tasks = [self._eval_one(sample) for sample in dataset]
results = await asyncio.gather(*tasks)

Benefits:

Significant reduction in evaluation time
Enables integration with future LLM Judge pipeline

3. Lessons Learned
Retrieval Must Be Measurable, Not Assumed:
A major lesson is that retrieval quality cannot be inferred from final answers. Without explicit metrics (Hit Rate, MRR), the system lacks transparency and cannot be improved systematically.
Chunk-Level Ground Truth is Critical:
Using document-level labels is insufficient. Fine-grained chunk-level IDs are required to accurately evaluate retrieval performance.
Most Errors Originate from Retrieval, Not Generation:
Through evaluation logs, I observed that many incorrect answers were caused by:
missing relevant chunks in top-k
or incorrect ranking
rather than LLM hallucination
Evaluation Enables Root Cause Analysis:
By logging retrieved_ids and comparing with ground truth, I can trace failures to:
embedding quality
chunking strategy
or vector search configuration
---

**Commit Evidence:** https://github.com/nam-k-nguyen/Lab14-C401-C5/blob/R3_Data-Engineer-(Retrieval)/engine/retrieval_eval.py.
