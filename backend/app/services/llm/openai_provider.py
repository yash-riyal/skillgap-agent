import json
from typing import Dict, Any, List
from app.services.llm.provider import BaseLLMProvider
from app.services.llm.heuristic_provider import HeuristicLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback = HeuristicLLMProvider()

    def extract_job_requirements(self, text: str) -> Dict[str, Any]:
        if not self.api_key:
            return self.fallback.extract_job_requirements(text)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            prompt = (
                "You are an expert technical career AI. Analyze the following job posting text. "
                "Extract the Job Title, Company Name, and all technical skills required or preferred. "
                "Output strictly a JSON object matching this schema:\n"
                "{\n"
                '  "title": "string",\n'
                '  "company": "string",\n'
                '  "requirements": [\n'
                '    {\n'
                '      "skill": "string",\n'
                '      "canonical_skill": "string",\n'
                '      "importance": "required" or "preferred",\n'
                '      "confidence": float between 0.0 and 1.0,\n'
                '      "source_text": "verbatim text segment from posting"\n'
                "    }\n"
                "  ]\n"
                "}\n\n"
                f"JOB POSTING TEXT:\n{text[:4000]}"
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"[OpenAIProvider] Warning: {e}, falling back to heuristic provider.")
            return self.fallback.extract_job_requirements(text)

    def analyze_semantic_evidence(self, skill: str, file_snippets: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.api_key:
            return self.fallback.analyze_semantic_evidence(skill, file_snippets)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            prompt = (
                f"Assess evidence for skill '{skill}' based on repository snippets.\n"
                "Distinguish CLAIM ONLY (README or description mention without code) from REAL IMPLEMENTATION.\n"
                "Output strictly JSON:\n"
                "{\n"
                '  "evidence_strength": "strong" | "moderate" | "weak" | "insufficient",\n'
                '  "is_claim_only": boolean,\n'
                '  "explanation": "concise explanation"\n'
                "}\n\n"
                f"SNIPPETS:\n{json.dumps(file_snippets[:6])}"
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return self.fallback.analyze_semantic_evidence(skill, file_snippets)
