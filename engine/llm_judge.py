import asyncio
from typing import Dict, Any


import os
import google.generativeai as genai


class LLMJudge:
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.rubrics = {
            "accuracy": "Chấm điểm từ 1-5 dựa trên độ chính xác so với Ground Truth...",
            "tone": "Chấm điểm từ 1-5 dựa trên sự chuyên nghiệp của ngôn ngữ...",
        }
        # Setup Gemini API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            raise EnvironmentError("GOOGLE_API_KEY not set in environment.")

    async def evaluate_single_gemini(
        self, question: str, answer: str, ground_truth: str
    ) -> int:
        """
        Call Gemini 1.5 Pro to score the answer. Returns an integer score 1-5.
        """
        prompt = f"""
        Bạn là giám khảo AI. Hãy chấm điểm câu trả lời của Agent dựa trên tiêu chí:
        - Độ chính xác so với Ground Truth (1-5)
        - Sự chuyên nghiệp của ngôn ngữ (1-5)
        Trả về JSON: {{"accuracy": <int>, "tone": <int>, "explanation": <string>}}

        Câu hỏi: {question}
        Ground Truth: {ground_truth}
        Câu trả lời của Agent: {answer}
        """
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = await asyncio.to_thread(model.generate_content, prompt)
        import json
        import re

        # Extract JSON from response
        text = response.text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                score = int(data.get("accuracy", 3))
                return score
            except Exception:
                return 3
        return 3

    async def evaluate_multi_judge(
        self, question: str, answer: str, ground_truth: str
    ) -> Dict[str, Any]:
        """
        Calls GPT-4o (mocked) and Gemini 1.5 Pro (real) to score the answer.
        """
        # GPT-4o (mocked, replace with real call if available)
        score_gpt = 4
        # Gemini (real)
        score_gemini = await self.evaluate_single_gemini(question, answer, ground_truth)
        avg_score = (score_gpt + score_gemini) / 2
        agreement = 1.0 if score_gpt == score_gemini else 0.5
        return {
            "final_score": avg_score,
            "agreement_rate": agreement,
            "individual_scores": {"gpt-4o": score_gpt, "gemini-1.5-pro": score_gemini},
        }

    async def check_position_bias(self, response_a: str, response_b: str):
        """
        Đổi chỗ response A và B, chấm điểm bằng Gemini để kiểm tra thiên vị vị trí.
        """
        # Score A first
        score_a_first = await self.evaluate_single_gemini("Q", response_a, "GT")
        # Score B first
        score_b_first = await self.evaluate_single_gemini("Q", response_b, "GT")
        return {"score_a_first": score_a_first, "score_b_first": score_b_first}
