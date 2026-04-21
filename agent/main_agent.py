import asyncio
from typing import List, Dict


class MainAgent:
    """
    Đây là Agent mẫu sử dụng kiến trúc RAG đơn giản.
    Sinh viên nên thay thế phần này bằng Agent thực tế đã phát triển ở các buổi trước.
    """

    def __init__(self):
        self.name = "SupportAgent-v1"

    async def query(self, question: str) -> Dict:
        """
        Mô phỏng quy trình RAG:
        1. Retrieval: Tìm kiếm context liên quan.
        2. Generation: Gọi LLM để sinh câu trả lời.
        """
        # Giả lập độ trễ mạng/LLM
        await asyncio.sleep(0.5)

        # Giả lập dữ liệu trả về
        return {
            "answer": f"Dựa trên tài liệu hệ thống, tôi xin trả lời câu hỏi '{question}' như sau: [Câu trả lời mẫu].",
            "contexts": [
                "Đoạn văn bản trích dẫn 1 dùng để trả lời...",
                "Đoạn văn bản trích dẫn 2 dùng để trả lời...",
            ],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": 150,
                "sources": ["policy_handbook.pdf"],
            },
        }


class MainAgentV2(MainAgent):
    def __init__(self):
        super().__init__()
        self.name = "SupportAgent-v2"

    async def query(self, question: str) -> Dict:
        # 1) call existing retrieval to get contexts + retrieved_ids
        resp = await super().query(question)
        contexts = resp.get("contexts", [])

        # 2) simple reranker: sort by keyword overlap with question
        def score_ctx(ctx):
            return sum(1 for w in question.split() if w in ctx)

        contexts = sorted(contexts, key=score_ctx, reverse=True)
        # 3) stricter prompt: ask LLM to only use provided contexts
        resp["contexts"] = contexts
        resp["answer"] = f"[V2 enforced-from-context] {resp['answer']}"
        return resp


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)

    asyncio.run(test())
