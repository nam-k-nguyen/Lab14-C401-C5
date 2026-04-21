import asyncio
import json
import os
import time

from agent.main_agent import MainAgent, MainAgentV2
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


def _build_agent(agent_version: str):
    """Select agent based on version label ('V2' in name → optimized variant)."""
    if "V2" in agent_version:
        return MainAgentV2()
    return MainAgent()


async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    agent = _build_agent(agent_version)
    evaluator = RetrievalEvaluator(agent=agent, top_k=3)
    judge = LLMJudge()
    runner = BenchmarkRunner(agent, evaluator, judge)
    results = await runner.run_all(dataset)

    total = len(results)
    summary = {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
            "hit_rate": sum(r["ragas"]["hit_rate"] for r in results) / total,
            "mrr": sum(r["ragas"]["mrr"] for r in results) / total,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total,
            "total_cost": runner.cost_tracker.total(),
            "cost_breakdown": runner.cost_tracker.breakdown(),
            "p95_latency": runner.p95_latency,
        }
    }
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary


RELEASE_THRESHOLDS = {
    "hit_rate":        0.85,
    "agreement_rate":  0.70,
    "cost_delta_pct":  0.10,
    "p95_latency_sec": 1.5,
}


def decide_release(v1: dict, v2: dict) -> dict:
    """Release Gate: V2 chỉ release khi pass cả 5 ngưỡng."""
    m1, m2 = v1["metrics"], v2["metrics"]
    delta_score = m2["avg_score"] - m1["avg_score"]
    delta_hit = m2["hit_rate"] - m1["hit_rate"]

    cost_v1 = max(m1.get("total_cost", 0.0), 1e-9)
    cost_delta_pct = (m2.get("total_cost", 0.0) - cost_v1) / cost_v1

    gates = {
        "quality_improved":   delta_score >= 0,
        "hit_rate_ok":        m2["hit_rate"] >= RELEASE_THRESHOLDS["hit_rate"],
        "agreement_ok":       m2["agreement_rate"] >= RELEASE_THRESHOLDS["agreement_rate"],
        "cost_within_budget": cost_delta_pct <= RELEASE_THRESHOLDS["cost_delta_pct"],
        "latency_p95_ok":     m2.get("p95_latency", 0.0) <= RELEASE_THRESHOLDS["p95_latency_sec"],
    }
    decision = "RELEASE" if all(gates.values()) else "ROLLBACK"
    return {
        "decision": decision,
        "gates": gates,
        "deltas": {
            "score": delta_score,
            "hit_rate": delta_hit,
            "cost_pct": cost_delta_pct,
        },
        "thresholds": RELEASE_THRESHOLDS,
    }


def compare_regression(v1: dict, v2: dict) -> None:
    """In bảng so sánh V1 vs V2 cho từng metric."""
    m1, m2 = v1["metrics"], v2["metrics"]
    print("\n📊 --- REGRESSION V1 vs V2 ---")
    print(f"{'Metric':<20} {'V1':>12} {'V2':>12} {'Δ':>12}")
    print("-" * 58)
    for key in ["avg_score", "hit_rate", "mrr", "agreement_rate", "total_cost", "p95_latency"]:
        a, b = m1.get(key, 0.0), m2.get(key, 0.0)
        sign = "+" if (b - a) >= 0 else ""
        print(f"{key:<20} {a:>12.4f} {b:>12.4f} {sign}{b-a:>11.4f}")


async def main():
    v1_results, v1_summary = await run_benchmark_with_results("Agent_V1_Base")
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")

    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    compare_regression(v1_summary, v2_summary)

    gate_result = decide_release(v1_summary, v2_summary)
    v2_summary["release_gate"] = gate_result
    v2_summary["v1_metrics"] = v1_summary["metrics"]

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({"v1": v1_results, "v2": v2_results}, f, ensure_ascii=False, indent=2)

    print(f"\n🚦 QUYẾT ĐỊNH: {gate_result['decision']}")
    for name, passed in gate_result["gates"].items():
        print(f"   {'✅' if passed else '❌'} {name}")

if __name__ == "__main__":
    asyncio.run(main())
