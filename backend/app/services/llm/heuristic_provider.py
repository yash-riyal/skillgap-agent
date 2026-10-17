import re
from typing import Dict, Any, List
from app.services.llm.provider import BaseLLMProvider
from app.services.normalization.normalizer import skill_normalizer

class HeuristicLLMProvider(BaseLLMProvider):
    """
    Deterministic rule & NLP-based provider. Provides immediate zero-cost execution
    and reliable fallback without requiring API keys.
    """

    def extract_job_requirements(self, text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 1. Detect Title and Company if available
        title = "Backend Developer"
        company = "Tech Innovations"
        for line in lines[:5]:
            if "role:" in line.lower() or "job:" in line.lower() or "title:" in line.lower():
                parts = line.split(":", 1)
                title = parts[1].strip()
            elif "company:" in line.lower() or "at " in line.lower():
                parts = line.split(":", 1)
                company = parts[1].strip() if len(parts) > 1 else line.strip()

        # 2. Segment text into Required vs Preferred
        required_text_blocks = []
        preferred_text_blocks = []
        current_section = "required"

        for line in lines:
            lower = line.lower()
            if any(k in lower for k in ["preferred", "nice to have", "bonus", "plus", "good to have", "optional"]):
                current_section = "preferred"
            elif any(k in lower for k in ["requirement", "qualifications", "must have", "what we're looking for", "skills"]):
                current_section = "required"

            if current_section == "preferred":
                preferred_text_blocks.append(line)
            else:
                required_text_blocks.append(line)

        # 3. Scan for tech skills across text blocks
        recognized_skills = set()
        requirements = []

        all_taxa = skill_normalizer.taxonomy

        # Check each sentence or bullet
        for section_name, blocks in [("required", required_text_blocks), ("preferred", preferred_text_blocks)]:
            combined_section = " \n ".join(blocks)
            for line in blocks:
                for canonical, data in all_taxa.items():
                    if canonical in recognized_skills:
                        continue
                    
                    # Match canonical or aliases
                    candidates = [canonical] + data.get("aliases", []) + data.get("sub_skills", [])
                    matched = False
                    for cand in candidates:
                        pattern = r"\b" + re.escape(cand) + r"\b"
                        if re.search(pattern, line, re.IGNORECASE):
                            recognized_skills.add(canonical)
                            requirements.append({
                                "skill": cand,
                                "canonical_skill": canonical,
                                "importance": section_name,
                                "confidence": 0.94 if cand.lower() == canonical.lower() else 0.88,
                                "source_text": line
                            })
                            matched = True
                            break

        # Fallback if no skills parsed (e.g. plain description without taxonomy match)
        if not requirements:
            common_skills = ["Python", "SQL", "REST API", "Docker", "Git", "Automated Testing"]
            for s in common_skills:
                requirements.append({
                    "skill": s,
                    "canonical_skill": s,
                    "importance": "required",
                    "confidence": 0.85,
                    "source_text": f"Foundational engineering capability: {s}"
                })

        return {
            "title": title,
            "company": company,
            "requirements": requirements
        }

    def analyze_semantic_evidence(self, skill: str, file_snippets: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyzes file snippets to see if they represent real implementation or merely a claim/mention.
        """
        if not file_snippets:
            return {
                "evidence_strength": "insufficient",
                "is_claim_only": False,
                "explanation": f"{skill} is not demonstrated in the selected repositories."
            }

        has_code_impl = False
        has_claim_only = False
        relevant_files = []

        for item in file_snippets:
            path = item.get("file_path", "").lower()
            snippet = item.get("snippet", "")
            
            if "readme" in path or "docs" in path:
                has_claim_only = True
            elif any(ext in path for ext in [".py", ".ts", ".js", ".sql", ".java", ".go", ".rs", "dockerfile", ".yml", ".yaml"]):
                has_code_impl = True
                relevant_files.append(item.get("file_path"))

        if has_code_impl:
            return {
                "evidence_strength": "strong" if len(relevant_files) >= 2 else "moderate",
                "is_claim_only": False,
                "explanation": f"Implementation files and code references detected in: {', '.join(relevant_files[:3])}."
            }
        elif has_claim_only:
            return {
                "evidence_strength": "weak",
                "is_claim_only": True,
                "explanation": f"Skill is mentioned in documentation/README, but no runnable implementation was detected."
            }

        return {
            "evidence_strength": "insufficient",
            "is_claim_only": False,
            "explanation": f"No concrete implementation of {skill} found in selected files."
        }
