import asyncio
import os
from typing import List, Dict, Tuple
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

_SYSTEM_V1 = (
    "Bạn là trợ lý hỗ trợ nội bộ công ty. "
    "Trả lời câu hỏi của nhân viên dựa trên tài liệu được cung cấp. "
    "Nếu thông tin không có trong tài liệu, hãy nói rõ là bạn không có thông tin đó."
)

_SYSTEM_V2 = (
    "Bạn là trợ lý hỗ trợ nội bộ công ty chuyên nghiệp. Quy tắc bắt buộc:\n"
    "1. CHỈ sử dụng thông tin trong Context được cung cấp — không bịa đặt.\n"
    "2. Trích dẫn cụ thể số liệu, điều kiện, quy trình từ tài liệu.\n"
    "3. Nếu câu hỏi ngoài phạm vi tài liệu, từ chối lịch sự và nêu lý do.\n"
    "4. Trả lời đầy đủ, có cấu trúc rõ ràng."
)


class MainAgent:
    def __init__(self, chroma_db_path: str = None, system_prompt: str = None):
        self.name = "SupportAgent-v1"
        self._system_prompt = system_prompt or _SYSTEM_V1
        self.llm = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if chroma_db_path is None:
            chroma_db_path = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

        self.chroma_db_path = os.path.abspath(chroma_db_path)

        try:
            self.client = chromadb.PersistentClient(path=self.chroma_db_path)
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            # Không truyền embedding_function để tránh conflict với persisted "default"
            self.collection = self.client.get_collection(name="rag_lab")
            print(f"✅ Kết nối Chroma DB từ: {self.chroma_db_path}")
            print(f"   Collection: {self.collection.name}")
            print(f"   Số documents: {self.collection.count()}")
        except Exception as e:
            print(f"⚠️  Lỗi kết nối Chroma DB: {e}")
            print(f"   Đường dẫn: {self.chroma_db_path}")
            self.collection = None
            self.embedder = None

    async def retrieve(self, question: str, top_k: int = 3) -> List[Dict]:
        if self.collection is None:
            return []

        try:
            embedding = self.embedder.encode(question).tolist()
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
            )

            contexts = []
            if results and results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else None
                    chunk_id = results["ids"][0][i] if results.get("ids") else None

                    contexts.append({
                        "id": chunk_id,
                        "text": doc,
                        "metadata": metadata,
                        "similarity_score": 1 - distance if distance is not None else None,
                    })
            return contexts
        except Exception as e:
            print(f"❌ Lỗi retrieval: {e}")
            return []

    async def _generate(self, question: str, contexts: List[str]) -> Tuple[str, int]:
        context_str = "\n---\n".join(contexts) if contexts else "Không tìm thấy tài liệu liên quan."
        user_prompt = f"Context:\n{context_str}\n\nCâu hỏi: {question}"

        try:
            response = await self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=600,
            )
            return response.choices[0].message.content, response.usage.total_tokens
        except Exception as e:
            return f"Lỗi generation: {e}", 0

    async def query(self, question: str) -> Dict:
        contexts_data = await self.retrieve(question, top_k=3)
        contexts = [ctx["text"] for ctx in contexts_data]
        answer, tokens_used = await self._generate(question, contexts)

        return {
            "answer": answer,
            "contexts": contexts,
            "retrieved_ids": [c.get("id") for c in contexts_data if c.get("id")],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": tokens_used,
                "sources": [ctx["metadata"].get("source", "unknown") for ctx in contexts_data],
                "num_contexts": len(contexts),
                "retrieval_scores": [ctx["similarity_score"] for ctx in contexts_data],
            },
        }

    async def run(self, question: str) -> Dict:
        """Alias cho evaluate_batch path (_eval_one gọi agent.run)."""
        return await self.query(question)


class MainAgentV2(MainAgent):
    """
    V2 improvements over V1:
    - Retrieve top-5 then rerank by keyword overlap BEFORE generation
    - Stricter system prompt requiring exact citations and structured output
    """

    def __init__(self, chroma_db_path: str = None):
        super().__init__(chroma_db_path=chroma_db_path, system_prompt=_SYSTEM_V2)
        self.name = "SupportAgent-v2"

    async def query(self, question: str) -> Dict:
        # Retrieve more candidates, then rerank top-3 before generation
        contexts_data = await self.retrieve(question, top_k=5)

        q_words = [w.lower() for w in question.split() if len(w) > 2]

        def _keyword_score(ctx_dict: Dict) -> int:
            text = ctx_dict["text"].lower()
            return sum(1 for w in q_words if w in text)

        reranked = sorted(contexts_data, key=_keyword_score, reverse=True)[:3]
        contexts = [ctx["text"] for ctx in reranked]
        answer, tokens_used = await self._generate(question, contexts)

        return {
            "answer": answer,
            "contexts": contexts,
            "retrieved_ids": [c.get("id") for c in reranked if c.get("id")],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": tokens_used,
                "sources": [ctx["metadata"].get("source", "unknown") for ctx in reranked],
                "num_contexts": len(contexts),
                "retrieval_scores": [ctx["similarity_score"] for ctx in reranked],
            },
        }


if __name__ == "__main__":
    import json

    async def _test():
        agent = MainAgent()
        resp = await agent.query("Đổi mật khẩu thế nào?")
        print(json.dumps(resp, ensure_ascii=False, indent=2))

    asyncio.run(_test())
