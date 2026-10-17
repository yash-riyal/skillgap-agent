from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseLLMProvider(ABC):
    @abstractmethod
    def extract_job_requirements(self, text: str) -> Dict[str, Any]:
        """
        Extracts structured job title, company, required skills, and preferred skills.
        Expected return format:
        {
            "title": str,
            "company": str,
            "requirements": [
                {
                    "skill": str,
                    "importance": "required" | "preferred",
                    "confidence": float,
                    "source_text": str
                }
            ]
        }
        """
        pass

    @abstractmethod
    def analyze_semantic_evidence(self, skill: str, file_snippets: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Interprets code snippets semantically for evidence of skill proficiency vs claims.
        """
        pass
