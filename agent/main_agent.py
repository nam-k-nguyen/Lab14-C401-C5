import asyncio
import os
from typing import List, Dict
import chromadb
from chromadb.config import Settings

class MainAgent:
    """
    Agent RAG với Chroma DB vector store.
    Sinh viên nên thay thế phần Generation bằng actual LLM integration.
    """
    def __init__(self, chroma_db_path: str = None):
        self.name = "SupportAgent-v1"
        
        # Khởi tạo Chroma DB
        if chroma_db_path is None:
            # Tìm chroma_db folder từ thư mục làm việc hiện tại
            chroma_db_path = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
        
        self.chroma_db_path = os.path.abspath(chroma_db_path)
        
        try:
            # Kết nối đến Chroma DB (persistent client)
            self.client = chromadb.PersistentClient(path=self.chroma_db_path)
            
            # Lấy collection (tên mặc định)
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ Kết nối Chroma DB từ: {self.chroma_db_path}")
            print(f"   Collection: {self.collection.name}")
            print(f"   Số documents: {self.collection.count()}")
        except Exception as e:
            print(f"⚠️  Lỗi kết nối Chroma DB: {e}")
            print(f"   Đường dẫn: {self.chroma_db_path}")
            self.collection = None

    async def retrieve(self, question: str, top_k: int = 3) -> List[Dict]:
        """
        Thực hiện retrieval từ Chroma DB.
        Args:
            question: Câu hỏi của user
            top_k: Số lượng documents trả về
        Returns:
            Danh sách documents liên quan
        """
        if self.collection is None:
            print(f"⚠️  Không có collection, trả về empty results")
            return []
        
        try:
            # Query Chroma DB
            results = self.collection.query(
                query_texts=[question],
                n_results=top_k
            )
            
            # Format lại kết quả
            contexts = []
            if results and results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else None
                    
                    contexts.append({
                        "text": doc,
                        "metadata": metadata,
                        "similarity_score": 1 - distance if distance is not None else None  # Convert distance to similarity
                    })
            
            return contexts
        except Exception as e:
            print(f"❌ Lỗi retrieval: {e}")
            return []

    async def query(self, question: str) -> Dict:
        """
        Quy trình RAG:
        1. Retrieval: Tìm kiếm context liên quan từ Chroma DB.
        2. Generation: Gọi LLM để sinh câu trả lời (TODO: integrate LLM).
        """
        # 1. Retrieval
        contexts_data = await self.retrieve(question, top_k=3)
        
        # 2. Chuẩn bị context cho generation
        contexts = [ctx["text"] for ctx in contexts_data]
        
        # 3. Generation (giờ mới giả lập, sau thay bằng LLM thực tế)
        await asyncio.sleep(0.3)
        
        context_str = "\n---\n".join(contexts) if contexts else "Không tìm thấy tài liệu liên quan."
        
        return {
            "answer": f"Dựa trên tài liệu: {question}\n\nContext:\n{context_str}",
            "contexts": contexts,
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": 150,
                "sources": [ctx["metadata"].get("source", "unknown") for ctx in contexts_data],
                "num_contexts": len(contexts),
                "retrieval_scores": [ctx["similarity_score"] for ctx in contexts_data]
            }
        }

if __name__ == "__main__":
    agent = MainAgent()
    
    async def test():
        print(\"\\n🔍 Testing retrieval + query...\\n\")
        resp = await agent.query(\"Làm thế nào để đổi mật khẩu?\")
        print(\"\\n📝 Response:\")\n        import json
        print(json.dumps(resp, ensure_ascii=False, indent=2))
    
    asyncio.run(test())
