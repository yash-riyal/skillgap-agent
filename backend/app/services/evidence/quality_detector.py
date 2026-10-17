from typing import List, Dict, Any

class EvidenceQualityDetector:
    """
    Novelty 1: Evaluates evidence quality by contrasting claims (in README or doc files)
    against actual working implementation (code, configuration, tests, schemas).
    """

    def evaluate_skill_quality(self, skill: str, evidence_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not evidence_items:
            return {
                "skill": skill,
                "status": "not_demonstrated",
                "evidence_strength": "none",
                "is_claim_only": False,
                "confidence": 0.90,
                "explanation": f"{skill} is not demonstrated in the selected repositories."
            }

        code_items = [e for e in evidence_items if not e.get("is_claim_only", False)]
        claim_items = [e for e in evidence_items if e.get("is_claim_only", False)]

        # Case 1: Claims exist in README / docs, but NO code/config implementation was found
        if claim_items and not code_items:
            claim_files = list({c.get("file_path", "README") for c in claim_items})
            return {
                "skill": skill,
                "status": "weak_evidence",
                "evidence_strength": "weak",
                "is_claim_only": True,
                "confidence": 0.85,
                "explanation": f"Claimed in {', '.join(claim_files[:2])}, but no actual implementation or configuration was detected."
            }

        # Case 2: Code/config implementation found
        distinct_files = list({c.get("file_path") for c in code_items})
        has_tests = any(c.get("evidence_type") == "test" for c in code_items)
        has_config = any(c.get("evidence_type") == "config" for c in code_items)
        has_dedicated_file = any(
            any(f.lower().endswith(ext) for ext in [".sql", "dockerfile", "docker-compose.yml", "docker-compose.yaml"])
            for f in distinct_files
        )

        # Strong: Dedicated schema/containerization file, multiple distinct files, or code + tests/config
        if has_dedicated_file or len(distinct_files) >= 2 or (has_tests or has_config):
            return {
                "skill": skill,
                "status": "demonstrated",
                "evidence_strength": "strong",
                "is_claim_only": False,
                "confidence": 0.95,
                "explanation": f"Implementation code and supporting artifacts verified in: {', '.join(distinct_files[:3])}."
            }

        # Moderate: 1 code file found
        if len(distinct_files) >= 1:
            return {
                "skill": skill,
                "status": "partially_demonstrated",
                "evidence_strength": "moderate",
                "is_claim_only": False,
                "confidence": 0.80,
                "explanation": f"Direct implementation detected in {distinct_files[0]}, but limited supporting tests or configurations."
            }

        return {
            "skill": skill,
            "status": "not_demonstrated",
            "evidence_strength": "none",
            "is_claim_only": False,
            "confidence": 0.85,
            "explanation": f"{skill} is not demonstrated in the selected repositories."
        }

quality_detector = EvidenceQualityDetector()
