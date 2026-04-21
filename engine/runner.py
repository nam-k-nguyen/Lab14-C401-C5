import asyncio
import statistics
import time
from typing import List, Dict

PRICING = {
    "gpt-4o":         {"in": 0.0025, "out": 0.01},
    "gpt-4o-mini":    {"in": 0.00015, "out": 0.0006},
    "gemini-2.5-flash-lite": {"in": 0.00125, "out": 0.005},
    "gemini-1.5-flash": {"in": 0.000075, "out": 0.0003},
}


class CostTracker:
    def __init__(self):
        self.entries: List[Dict] = []

    def log(self, model: str, in_tokens: int, out_tokens: int) -> float:
        p = PRICING.get(model, {"in": 0.0, "out": 0.0})
        cost = (in_tokens * p["in"] + out_tokens * p["out"]) / 1000.0
        self.entries.append({
            "model": model,
            "in_tokens": in_tokens,
            "out_tokens": out_tokens,
            "cost": cost,
        })
        return cost

    def total(self) -> float:
        return sum(e["cost"] for e in self.entries)

    def breakdown(self) -> Dict[str, float]:
        agg: Dict[str, float] = {}
        for e in self.entries:
            agg[e["model"]] = agg.get(e["model"], 0.0) + e["cost"]
        return agg


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge
        self.cost_tracker = CostTracker()
        self.p95_latency: float = 0.0

    def _log_judge_cost(self, judge_result: Dict) -> None:
        """Pull token usage from each model in individual_scores and log to CostTracker."""
        for name, score_dict in judge_result.get("individual_scores", {}).items():
            if not isinstance(score_dict, dict):
                continue
            usage = score_dict.get("usage", {})
            if not usage:
                continue
            model = score_dict.get("model", name)
            self.cost_tracker.log(
                model,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
            )

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time

        ragas_scores = await self.evaluator.score(test_case, response)

        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"],
        )
        self._log_judge_cost(judge_result)

        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "retrieved_ids": response.get("retrieved_ids", []),
            "latency": latency,
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass",
        }

    async def run_all(
        self, dataset: List[Dict], concurrency: int = 5
    ) -> List[Dict]:
        """
        Chạy song song với Semaphore giới hạn concurrency để né rate limit
        OpenAI/Gemini. Mặc định 5 request đồng thời.
        """
        sem = asyncio.Semaphore(concurrency)

        async def _guarded(case):
            async with sem:
                return await self.run_single_test(case)

        tasks = [_guarded(case) for case in dataset]
        results = await asyncio.gather(*tasks)

        latencies = [r["latency"] for r in results if "latency" in r]
        if len(latencies) >= 2:
            try:
                self.p95_latency = statistics.quantiles(latencies, n=20)[18]
            except statistics.StatisticsError:
                self.p95_latency = max(latencies)
        elif latencies:
            self.p95_latency = latencies[0]
        return results
