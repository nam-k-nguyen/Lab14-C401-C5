import asyncio
import os
import json
from typing import Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv
from jinja2 import Template

load_dotenv()

class LLMJudge:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.rubric_path = os.path.join(os.path.dirname(__file__), "prompts", "rubric.md")
        self.rubric_content = self._load_rubric()

    def _load_rubric(self) -> str:
        if os.path.exists(self.rubric_path):
            with open(self.rubric_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Rubric not found."

    def build_judge_prompt(self, question: str, answer: str, ground_truth: str) -> str:
        prompt_template = """
# MISSION
You are an AI Judge. Please evaluate the assistant's response based on the following Rubric.

# EVALUATION RUBRIC
{{ rubric }}

# EVALUATION DATA
- **Question:** {{ question }}
- **Answer:** {{ answer }}
- **Ground Truth:** {{ ground_truth }}

# OUTPUT REQUIREMENT
Return the result in a single JSON format only, with no additional text outside the JSON.
"""
        template = Template(prompt_template)
        return template.render(
            rubric=self.rubric_content,
            question=question,
            answer=answer,
            ground_truth=ground_truth
        )

    async def evaluate_single_gpt(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        """
        Gọi GPT-4o-mini để đánh giá một case.
        """
        prompt = self.build_judge_prompt(question, answer, ground_truth)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs only JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            result = json.loads(response.choices[0].message.content)
            # Thêm thông tin model và cost (token usage)
            result["model"] = self.model
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            return result
        except Exception as e:
            print(f"Error calling GPT Judge: {e}")
            return {
                "accuracy": {"score": 0, "reason": str(e)},
                "final_score": 0,
                "model": self.model,
                "error": True
            }

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        """
        Thực hiện đánh giá từ các Judge. 
        Hiện tại tập trung vào GPT-4o-mini (Vai R4).
        """
        # Gọi GPT Judge
        gpt_result = await self.evaluate_single_gpt(question, answer, ground_truth)
        
        # Vai R4: Tập trung vào kết quả của GPT. 
        # Phần Gemini của R5 sẽ được tích hợp sau hoặc để placeholder.
        
        return {
            "final_score": gpt_result.get("final_score", 0),
            "agreement_rate": 1.0, # Mặc định 1.0 khi chỉ có 1 Judge hoạt động
            "individual_scores": {
                "gpt-4o-mini": gpt_result
            },
            "total_tokens": gpt_result.get("usage", {}).get("total_tokens", 0)
        }

    async def check_position_bias(self, response_a: str, response_b: str):
        """
        Nâng cao: Thực hiện đổi chỗ response A và B để xem Judge có thiên vị vị trí không.
        (Task bổ sung có thể thực hiện sau)
        """
        pass
