from typing import List, Dict, Any
import asyncio


class RetrievalEvaluator:
    def __init__(self, agent, top_k: int = 3):
        """
        agent: object có method async run(query) -> {"retrieved_ids": [...]}
        """
        self.agent = agent
        self.top_k = top_k

    def calculate_hit_rate(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
        top_k: int = None
    ) -> float:
        if top_k is None:
            top_k = self.top_k

        if not expected_ids or not retrieved_ids:
            return 0.0

        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str]
    ) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0

        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)  # rank bắt đầu từ 1
        return 0.0

    async def _eval_one(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """
        Eval 1 sample (async)
        """
        query = sample.get("query")
        expected_ids = sample.get("expected_retrieval_ids", [])

        try:
            result = await self.agent.run(query)
            retrieved_ids = result.get("retrieved_ids", [])
        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "hit": 0.0,
                "mrr": 0.0,
                "retrieved_ids": [],
                "expected_ids": expected_ids,
            }

        hit = self.calculate_hit_rate(expected_ids, retrieved_ids)
        mrr = self.calculate_mrr(expected_ids, retrieved_ids)

        return {
            "query": query,
            "hit": hit,
            "mrr": mrr,
            "retrieved_ids": retrieved_ids,
            "expected_ids": expected_ids,
        }

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        """
        Chạy eval toàn bộ dataset (async + concurrent)
        """

        tasks = [self._eval_one(sample) for sample in dataset]
        results = await asyncio.gather(*tasks)

        # filter lỗi nếu có
        valid_results = [r for r in results if "error" not in r]

        if not valid_results:
            return {
                "avg_hit_rate": 0.0,
                "avg_mrr": 0.0,
                "total_samples": len(dataset),
                "valid_samples": 0,
                "errors": [r for r in results if "error" in r],
            }

        avg_hit = sum(r["hit"] for r in valid_results) / len(valid_results)
        avg_mrr = sum(r["mrr"] for r in valid_results) / len(valid_results)

        return {
            "avg_hit_rate": avg_hit,
            "avg_mrr": avg_mrr,
            "total_samples": len(dataset),
            "valid_samples": len(valid_results),
            "errors": [r for r in results if "error" in r],
            "details": results  # QUAN TRỌNG: dùng cho debug root cause
        }
