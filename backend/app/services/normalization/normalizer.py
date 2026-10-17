import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

TAXONOMY_PATH = Path(__file__).resolve().parent / "taxonomy.json"

class SkillNormalizer:
    def __init__(self, taxonomy_file: Path = TAXONOMY_PATH):
        self.taxonomy: Dict[str, Any] = {}
        if taxonomy_file.exists():
            with open(taxonomy_file, "r", encoding="utf-8") as f:
                self.taxonomy = json.load(f)
        self._build_lookup_index()

    def _build_lookup_index(self):
        self.alias_to_canonical = {}
        self.subskill_to_canonical = {}
        self.related_to_canonical = {}

        for canonical, data in self.taxonomy.items():
            # Exact canonical (lowercase)
            self.alias_to_canonical[canonical.lower()] = (canonical, "exact skill", 1.0)

            # Aliases
            for alias in data.get("aliases", []):
                self.alias_to_canonical[alias.lower().strip()] = (canonical, "exact skill", 0.95)

            # Sub-skills
            for sub in data.get("sub_skills", []):
                self.subskill_to_canonical[sub.lower().strip()] = (canonical, f"sub-skill: {sub}", 0.90)

            # Related
            for rel in data.get("related", []):
                self.related_to_canonical[rel.lower().strip()] = (canonical, f"related technology: {rel}", 0.75)

    def normalize(self, raw_skill: str) -> Dict[str, Any]:
        """
        Normalizes a raw skill string into a canonical skill with relationship classification.
        """
        cleaned = raw_skill.strip()
        lowered = cleaned.lower()
        # Remove common bullet points, numbering, or fluff words
        cleaned_search = re.sub(r"^(experience with|proficiency in|knowledge of|hands-on with|familiarity with|strong understanding of)\s+", "", lowered, flags=re.IGNORECASE)
        cleaned_search = re.sub(r"[^\w\s\+\#\.\-]", " ", cleaned_search).strip()

        # 1. Exact alias match
        if lowered in self.alias_to_canonical:
            can, rel, conf = self.alias_to_canonical[lowered]
            return {
                "raw_skill": raw_skill,
                "canonical_skill": can,
                "relationship": rel,
                "confidence": conf
            }

        if cleaned_search in self.alias_to_canonical:
            can, rel, conf = self.alias_to_canonical[cleaned_search]
            return {
                "raw_skill": raw_skill,
                "canonical_skill": can,
                "relationship": rel,
                "confidence": conf
            }

        # 2. Sub-skill match
        if cleaned_search in self.subskill_to_canonical:
            can, rel, conf = self.subskill_to_canonical[cleaned_search]
            return {
                "raw_skill": raw_skill,
                "canonical_skill": can,
                "relationship": rel,
                "confidence": conf
            }

        # 3. Substring/token match in aliases
        for alias, (can, rel, conf) in self.alias_to_canonical.items():
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, cleaned_search, re.IGNORECASE):
                return {
                    "raw_skill": raw_skill,
                    "canonical_skill": can,
                    "relationship": rel,
                    "confidence": conf * 0.92
                }

        # 4. Check sub-skills within text
        for sub, (can, rel, conf) in self.subskill_to_canonical.items():
            pattern = r"\b" + re.escape(sub) + r"\b"
            if re.search(pattern, cleaned_search, re.IGNORECASE):
                return {
                    "raw_skill": raw_skill,
                    "canonical_skill": can,
                    "relationship": rel,
                    "confidence": conf * 0.88
                }

        # 5. Check related technologies
        for rel_item, (can, rel, conf) in self.related_to_canonical.items():
            pattern = r"\b" + re.escape(rel_item) + r"\b"
            if re.search(pattern, cleaned_search, re.IGNORECASE):
                return {
                    "raw_skill": raw_skill,
                    "canonical_skill": can,
                    "relationship": rel,
                    "confidence": conf * 0.80
                }

        # 6. Uncertain / Raw fallback
        title_cased = cleaned.title()
        return {
            "raw_skill": raw_skill,
            "canonical_skill": title_cased,
            "relationship": "uncertain",
            "confidence": 0.50
        }

skill_normalizer = SkillNormalizer()
