# Personal Reflection Report - Lab 14

**Full Name:** Nguyen Minh Hieu  
**Student ID:** 2A202600180  

**Role:** R4 - AI Engineer (Judge-GPT + Rubrics)

---

## 1. Role Overview and Tasks Performed
In Lab 14, I was responsible for building the **LLM Judge** system based on GPT to evaluate the quality of responses from the RAG system. My primary tasks included:
- Developing a detailed evaluation Rubric covering Accuracy, Tone, and Safety.
- Implementing the `LLMJudge` class in `engine/llm_judge.py` using the **gpt-4o-mini** model.
- Optimizing Prompts in English to achieve maximum performance and stability.
- Establishing automated JSON data extraction (JSON Mode) and cost tracking (Token usage).

---

## 2. Technical Analysis and Reflections

### 2.1. Consensus Logic & Judge Reliability
To enhance the reliability of automated evaluation, we adopted a **Multi-Judge** model. The consensus logic I established works as follows:
- When another Judge model (such as R5's Gemini) evaluates alongside, the system calculates an **Agreement Rate**.
- If the score difference between GPT and Gemini exceeds a defined threshold (delta > 1.0), the system triggers a **Tie-breaker** (calling a third model to arbitrate). 
- **Reflection:** Relying on a single model is prone to systematic error. Using Consensus minimizes risks when a model "hallucinates" during the scoring process.

### 2.2. Position Bias
While my primary work focused on a Single Judge setup, through research, I observed that LLMs often tend to favor responses appearing in certain positions or those with greater length.
- **Solution:** In advanced logic (`check_position_bias`), we proposed swapping the positions of Responses to ensure the Judge scores based on content rather than order.

### 2.3. Cost-Quality Trade-off
I decided to use **gpt-4o-mini** instead of the full gpt-4o.
- **Reason:** Through experimentation, gpt-4o-mini showed the capability to adhere to JSON mode and understand the Rubric comparably to the larger model for scoring tasks, but at a cost ~20-30 times cheaper and with significantly faster response times.
- **Conclusion:** For systems requiring continuous scoring of thousands of cases (Regression testing), cost optimization is a vital factor while maintaining result stability.

---

## 3. Lessons Learned
- **The "Lazy Judge" and Safe Scoring Problem:** I realized that LLMs tend to default to middle scores (3 or 4) to avoid making extreme decisions. To counter this, I adjusted the Rubric to require the Judge to list specific "violations" based on the Ground Truth before providing a final score. This forces the model to have "evidence" before concluding, significantly increasing the system's sensitivity.
- **Judge Cascade Strategy for 90% Cost Optimization:** A major lesson is that not every case requires a premium "referee." I proposed a Cascade workflow: Use gpt-4o-mini to filter out perfect answers (5) or complete failures (1). Only cases with mediocre scores (2, 3, 4) or those showing "ambiguity" in the reasoning are escalated to a higher-tier Judge (GPT-4o or Gemini Pro). This saves a massive budget without sacrificing overall system accuracy.
- **Dependency on Ground Truth Quality:** A Judge, no matter how intelligent, is only as good as the reference material it possesses. During testing, I found many cases where the Judge scored "incorrectly" only because the Ground Truth was missing points or vaguely phrased. The takeaway: the dataset validation phase (by R2/R3) is just as critical as writing the Judge code itself.

---

**Commit Evidence:** Branch `R4-Hieu` with commit prefix `[R4]`.
