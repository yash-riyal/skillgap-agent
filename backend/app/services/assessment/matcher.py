from typing import List, Dict, Any, Tuple
from app.services.evidence.quality_detector import quality_detector

class SkillMatchingEngine:
    """
    Skill Matching Engine: compares normalized job requirements against repository evidence,
    calculates an explainable evidence-based match score, and surfaces high-priority gaps.
    """

    WEIGHTS = {
        "demonstrated": 1.0,
        "partially_demonstrated": 0.5,
        "weak_evidence": 0.15,
        "not_demonstrated": 0.0,
        "uncertain": 0.25
    }

    def assess(
        self,
        requirements: List[Dict[str, Any]],
        evidence_by_skill: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        items = []
        high_priority_gaps = []

        demonstrated_count = 0
        partial_count = 0
        weak_count = 0
        not_demonstrated_count = 0

        required_skills = [r for r in requirements if r.get("importance") == "required"]
        preferred_skills = [r for r in requirements if r.get("importance") == "preferred"]

        total_req_points = 0.0
        max_req_points = max(len(required_skills), 1)

        total_pref_points = 0.0
        max_pref_points = max(len(preferred_skills), 1)

        for req in requirements:
            canonical = req.get("canonical_skill")
            importance = req.get("importance", "required")
            ev_list = evidence_by_skill.get(canonical, [])

            evaluation = quality_detector.evaluate_skill_quality(canonical, ev_list)
            status = evaluation["status"]
            strength = evaluation["evidence_strength"]

            if status == "demonstrated":
                demonstrated_count += 1
            elif status == "partially_demonstrated":
                partial_count += 1
            elif status == "weak_evidence":
                weak_count += 1
            else:
                not_demonstrated_count += 1

            # Point tallying
            earned_multiplier = self.WEIGHTS.get(status, 0.0)
            if importance == "required":
                total_req_points += earned_multiplier
            else:
                total_pref_points += earned_multiplier

            item_dto = {
                "canonical_skill": canonical,
                "importance": importance,
                "status": status,
                "evidence_strength": strength,
                "confidence": evaluation.get("confidence", 0.90),
                "explanation": evaluation.get("explanation"),
                "source_requirement_text": req.get("source_text", ""),
                "evidence": ev_list
            }
            items.append(item_dto)

            # High priority gap: Required skill that is either weak evidence or not demonstrated
            if importance == "required" and status in ["weak_evidence", "not_demonstrated", "uncertain"]:
                high_priority_gaps.append(item_dto)

        # Weighted calculation: 75% for Required skills, 25% for Preferred skills
        if required_skills and preferred_skills:
            req_score = (total_req_points / len(required_skills)) * 75.0
            pref_score = (total_pref_points / len(preferred_skills)) * 25.0
            match_score = round(req_score + pref_score, 1)
        elif required_skills:
            match_score = round((total_req_points / len(required_skills)) * 100.0, 1)
        elif preferred_skills:
            match_score = round((total_pref_points / len(preferred_skills)) * 100.0, 1)
        else:
            match_score = 0.0

        # Build score breakdown
        breakdown = {
            "required_count": len(required_skills),
            "preferred_count": len(preferred_skills),
            "demonstrated_count": demonstrated_count,
            "partial_count": partial_count,
            "weak_count": weak_count,
            "not_demonstrated_count": not_demonstrated_count,
            "formula_explanation": (
                f"Calculated from {len(required_skills)} required skills (weighted 75%) and "
                f"{len(preferred_skills)} preferred skills (weighted 25%). "
                "Demonstrated = 100%, Partially Demonstrated = 50%, Weak Claim = 15%, Not Demonstrated = 0%."
            )
        }

        return {
            "match_score": match_score,
            "score_breakdown": breakdown,
            "items": items,
            "high_priority_gaps": high_priority_gaps
        }

skill_matcher = SkillMatchingEngine()
