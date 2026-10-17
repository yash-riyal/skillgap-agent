import json
import httpx
from typing import Dict, Any, List
from app.services.llm.provider import BaseLLMProvider
from app.services.llm.heuristic_provider import HeuristicLLMProvider

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback = HeuristicLLMProvider()

    def extract_job_requirements(self, text: str) -> Dict[str, Any]:
        if not self.api_key:
            return self.fallback.extract_job_requirements(text)
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            prompt = (
                "You are an expert technical career AI. Analyze the following job posting text. "
                "Extract the Job Title, Company Name, and all technical skills required or preferred. "
                "Output strictly a JSON object with: title, company, requirements (list of skill, canonical_skill, importance ['required'|'preferred'], confidence, source_text).\n"
                f"JOB POSTING:\n{text[:4000]}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
            }
            with httpx.Client(timeout=20.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(content)
                else:
                    return self.fallback.extract_job_requirements(text)
        except Exception:
            return self.fallback.extract_job_requirements(text)

    def analyze_semantic_evidence(self, skill: str, file_snippets: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.api_key:
            return self.fallback.analyze_semantic_evidence(skill, file_snippets)
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            prompt = (
                f"Assess evidence for skill '{skill}' based on repository snippets.\n"
                "Distinguish CLAIM ONLY (README or description mention without code) from REAL IMPLEMENTATION.\n"
                "Output strictly JSON with fields: evidence_strength ('strong'|'moderate'|'weak'|'insufficient'), is_claim_only (bool), explanation (str).\n\n"
                f"SNIPPETS:\n{json.dumps(file_snippets[:6])}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
            }
            with httpx.Client(timeout=20.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(content)
                else:
                    return self.fallback.analyze_semantic_evidence(skill, file_snippets)
        except Exception:
            return self.fallback.analyze_semantic_evidence(skill, file_snippets)
