import asyncio
import json
import os
import re
from typing import Any, Dict

import google.generativeai as genai
from dotenv import load_dotenv
from jinja2 import Template
from openai import AsyncOpenAI

load_dotenv()


class LLMJudge:
    def __init__(
        self,
        gpt_model: str = "gpt-4o-mini",
        gemini_model: str = "gemini-1.5-pro",
        tie_breaker_model: str = "gpt-4o",
    ):
        self.gpt_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.gpt_model = gpt_model
        self.tie_breaker_model = tie_breaker_model

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY not set in environment.")
        genai.configure(api_key=api_key)
        self.gemini_model_name = gemini_model

        self.rubric_path = os.path.join(
            os.path.dirname(__file__), "prompts", "rubric.md"
        )
        self.rubric_content = self._load_rubric()

    def _load_rubric(self) -> str:
        if os.path.exists(self.rubric_path):
            with open(self.rubric_path, "r", encoding="utf-8") as f:
                return f.read()
        return "Rubric not found."

    def build_judge_prompt(
        self, question: str, answer: str, ground_truth: str
    ) -> str:
        template = Template(
            """
# MISSION
You are an AI Judge. Evaluate the assistant's response based on the Rubric.

# EVALUATION RUBRIC
{{ rubric }}

# EVALUATION DATA
- **Question:** {{ question }}
- **Answer:** {{ answer }}
- **Ground Truth:** {{ ground_truth }}

# OUTPUT REQUIREMENT
Return a single JSON object only. No extra text.
"""
        )
        return template.render(
            rubric=self.rubric_content,
            question=question,
            answer=answer,
            ground_truth=ground_truth,
        )

    async def evaluate_single_gpt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        model: str = None,
    ) -> Dict[str, Any]:
        """Call OpenAI GPT Judge. Returns rubric dict with final_score + usage."""
        model = model or self.gpt_model
        prompt = self.build_judge_prompt(question, answer, ground_truth)

        try:
            response = await self.gpt_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that outputs only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            result = json.loads(response.choices[0].message.content)
            result["model"] = model
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return result
        except Exception as e:
            return {"final_score": 0, "model": model, "error": str(e)}

    async def evaluate_single_gemini(
        self, question: str, answer: str, ground_truth: str
    ) -> Dict[str, Any]:
        """Call Google Gemini Judge with the same rubric prompt as GPT."""
        prompt = self.build_judge_prompt(question, answer, ground_truth)
        try:
            model = genai.GenerativeModel(self.gemini_model_name)
            response = await asyncio.to_thread(model.generate_content, prompt)
            text = response.text or ""
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return {
                    "final_score": 0,
                    "model": self.gemini_model_name,
                    "error": "no JSON in response",
                }
            data = json.loads(match.group(0))
            data["model"] = self.gemini_model_name
            usage_meta = getattr(response, "usage_metadata", None)
            data["usage"] = {
                "prompt_tokens": getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0,
                "completion_tokens": getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0,
                "total_tokens": getattr(usage_meta, "total_token_count", 0) if usage_meta else 0,
            }
            return data
        except Exception as e:
            return {
                "final_score": 0,
                "model": self.gemini_model_name,
                "error": str(e),
            }

    def _extract_score(self, judge_result: Dict) -> float:
        """Pull numeric score from judge output (supports nested rubric or flat shape)."""
        if "final_score" in judge_result:
            try:
                return float(judge_result["final_score"])
            except (TypeError, ValueError):
                pass
        acc = judge_result.get("accuracy")
        if isinstance(acc, dict) and "score" in acc:
            return float(acc["score"])
        if isinstance(acc, (int, float)):
            return float(acc)
        return 0.0

    async def evaluate_multi_judge(
        self, question: str, answer: str, ground_truth: str
    ) -> Dict[str, Any]:
        """
        Consensus of GPT + Gemini with optional tie-breaker.
        - agreement_rate: 1.0 when |Δ|≤1, scales linearly to 0 at |Δ|=4
        - tie-breaker: called when |Δ|>1; 3-way average used as final
        """
        gpt_result, gemini_result = await asyncio.gather(
            self.evaluate_single_gpt(question, answer, ground_truth),
            self.evaluate_single_gemini(question, answer, ground_truth),
        )
        score_gpt = self._extract_score(gpt_result)
        score_gemini = self._extract_score(gemini_result)
        delta = abs(score_gpt - score_gemini)
        agreement_rate = max(0.0, 1.0 - (delta / 4.0))

        tie_breaker_result = None
        if delta > 1.0:
            tie_breaker_result = await self.evaluate_single_gpt(
                question, answer, ground_truth, model=self.tie_breaker_model
            )
            score_tb = self._extract_score(tie_breaker_result)
            final_score = (score_gpt + score_gemini + score_tb) / 3
        else:
            final_score = (score_gpt + score_gemini) / 2

        total_tokens = (
            gpt_result.get("usage", {}).get("total_tokens", 0)
            + gemini_result.get("usage", {}).get("total_tokens", 0)
            + (
                tie_breaker_result.get("usage", {}).get("total_tokens", 0)
                if tie_breaker_result
                else 0
            )
        )
        individual = {"gpt": gpt_result, "gemini": gemini_result}
        if tie_breaker_result is not None:
            individual["tie_breaker"] = tie_breaker_result

        return {
            "final_score": final_score,
            "agreement_rate": agreement_rate,
            "delta": delta,
            "individual_scores": individual,
            "total_tokens": total_tokens,
        }

    async def check_position_bias(
        self,
        question: str,
        answer_a: str,
        answer_b: str,
        ground_truth: str,
    ) -> Dict[str, Any]:
        """
        Test whether Judge favors positional ordering:
        score answer pair in (A,B) order and (B,A) order. |Δ|>1 signals bias.
        """
        pair_ab = await self.evaluate_single_gpt(
            question, f"Answer A: {answer_a}\nAnswer B: {answer_b}", ground_truth
        )
        pair_ba = await self.evaluate_single_gpt(
            question, f"Answer A: {answer_b}\nAnswer B: {answer_a}", ground_truth
        )
        score_ab = self._extract_score(pair_ab)
        score_ba = self._extract_score(pair_ba)
        return {
            "score_ab_order": score_ab,
            "score_ba_order": score_ba,
            "positional_delta": abs(score_ab - score_ba),
        }
