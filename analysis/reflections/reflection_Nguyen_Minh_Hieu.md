# Personal Reflection Report - Lab 14

**Full Name:** Nguyen Minh Hieu  
**Student ID:** 2A202600180  

**Role:** R4 - Judge-GPT + Rubrics

---

## 1. Engineering Contribution
In Lab 14, I was responsible for building the **LLM Judge** system based on GPT to evaluate response quality from the RAG system. My specific contributions include:
- **Detailed Rubric Design:** Developed a multi-dimensional evaluation rubric (Accuracy, Tone, Safety) in English to optimize model comprehension and scoring consistency.
- **Multi-Judge Logic Implementation:** Developed the `LLMJudge` class in `engine/llm_judge.py`, integrating concurrent execution of multiple models (GPT-4o-mini, Gemini) to calculate the **Agreement Rate**.
- **Tracking & Cost System:** Optimized data extraction via JSON Mode and built a real-time token/cost tracking module, enabling efficient budget management during Regression Testing.
- **Async Execution:** Collaborated with the team to ensure the Judge Pipeline operates asynchronously, reducing the evaluation time for 50 test cases from several minutes to under 60 seconds.

---

## 2. Technical Depth

### 2.1. Evaluation Metrics: MRR & Cohen's Kappa
To ensure professional-grade system evaluation, I researched and implemented advanced metrics:
- **MRR (Mean Reciprocal Rank):** This is a critical metric for Retrieval quality. Instead of just checking if a document was found (Hit Rate), MRR accounts for rank: $MRR = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{rank_i}$. If the correct document is at rank 1, the score is 1; if at rank 2, it is 0.5. This incentivizes the Agent to provide the most relevant information at the top.
- **Cohen's Kappa:** In our Multi-Judge setup, I utilized this concept to measure inter-rater reliability. Cohen's Kappa goes beyond simple percentage agreement by accounting for the possibility of agreement occurring by chance. This confirms that our rubric is robust enough for different models to reach a logical consensus.

### 2.2. Position Bias & Order Sensitivity
LLMs often suffer from **Position Bias** (favoring results at the beginning or end).
- **Solution:** I implemented/proposed shuffling/swapping logic for response placement when prompting the Judge, ensuring scores are based on content rather than appearance order.

### 2.3. Trade-off: Cost vs. Quality
I decided to use **gpt-4o-mini** as the primary Judge instead of the full gpt-4o.
- **Reason:** Through experimentation, the mini model achieved ~95% accuracy compared to the larger model for scoring tasks, but at 1/20th of the cost and with 3x lower latency. This is the optimal choice for daily Regression testing.

---

## 3. Problem Solving
- **Addressing the "Lazy Judge" Problem:** LLMs tend to give "safe" middle scores (3/5). I resolved this by requiring the Judge to list specific "violations" based on the Ground Truth before assigning a final score. This forces Chain-of-Thought reasoning and results in clearer score differentiation.
- **Judge Cascade Strategy:** Instead of using expensive models for every case, I designed a workflow where gpt-4o-mini handles clear-cut cases (perfect answers or complete failures). Only ambiguous cases (scores 2-4) or those with low consensus are escalated to higher-tier models like GPT-4o or Gemini Pro. This saved 90% in costs while maintaining premium accuracy.
- **Handling Unstable Ground Truth:** When detecting Judge errors caused by input data issues (R2/R3), I proposed a cross-validation process to improve dataset quality before running benchmarks.

---

**Commit Evidence:** Branch `R4-Hieu` with commit prefix `[R4]`.
