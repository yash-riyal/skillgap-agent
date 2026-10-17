from typing import Dict, Any, List
from app.services.llm.factory import get_llm_provider
from app.services.normalization.normalizer import skill_normalizer

class JobExtractor:
    def __init__(self):
        self.llm = get_llm_provider()

    def process_job_text(self, text: str, user_title: str = None, user_company: str = None) -> Dict[str, Any]:
        """
        Runs the LLM + Skill Normalization Pipeline:
        JOB SOURCE -> CLEAN TEXT -> LLM EXTRACTION -> SKILL NORMALIZATION -> CANONICAL REQUIREMENTS
        """
        raw_result = self.llm.extract_job_requirements(text)
        title = user_title or raw_result.get("title") or "Backend Engineer"
        company = user_company or raw_result.get("company") or "Tech Corp"
        raw_reqs = raw_result.get("requirements", [])

        normalized_requirements = []
        seen_canonical = set()

        for item in raw_reqs:
            raw_skill = item.get("skill", "")
            norm = skill_normalizer.normalize(raw_skill)
            canonical = norm["canonical_skill"]

            # Merge or keep the highest confidence item for each canonical skill
            if canonical in seen_canonical:
                continue
            seen_canonical.add(canonical)

            importance = item.get("importance", "required").lower()
            if importance not in ["required", "preferred"]:
                importance = "required"

            confidence = float(item.get("confidence", 0.90))
            source_text = item.get("source_text") or f"Requirement for {raw_skill}"

            normalized_requirements.append({
                "skill": raw_skill,
                "canonical_skill": canonical,
                "importance": importance,
                "confidence": round(confidence, 2),
                "source_text": source_text.strip(),
                "relationship": norm.get("relationship", "exact skill")
            })

        return {
            "title": title,
            "company": company,
            "requirements": normalized_requirements
        }

job_extractor = JobExtractor()
