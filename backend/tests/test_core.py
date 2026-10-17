import pytest
from app.services.normalization.normalizer import skill_normalizer
from app.services.evidence.quality_detector import quality_detector
from app.services.jobs.job_extractor import job_extractor
from app.services.assessment.matcher import skill_matcher
from app.demo.fixtures import (
    DEMO_USERNAME, DEMO_REPOSITORIES, DEMO_REPO_FILES_V1, 
    simulate_git_commit, reset_demo_store, get_demo_files
)

def test_skill_normalization():
    # Exact alias
    norm1 = skill_normalizer.normalize("relational database proficiency")
    assert norm1["canonical_skill"] == "SQL"
    assert "exact skill" in norm1["relationship"]

    # Sub-skill
    norm2 = skill_normalizer.normalize("MySQL experience")
    assert norm2["canonical_skill"] == "SQL"

    # Containerization
    norm3 = skill_normalizer.normalize("Containerization")
    assert norm3["canonical_skill"] == "Docker"

    # RESTful API
    norm4 = skill_normalizer.normalize("RESTful API development")
    assert norm4["canonical_skill"] == "REST API"

def test_evidence_quality_detector_claims_vs_implementation():
    # Only claim in README
    claim_only_evidence = [
        {
            "file_path": "README.md",
            "is_claim_only": True,
            "evidence_type": "claim",
            "snippet": "This project uses Docker."
        }
    ]
    res1 = quality_detector.evaluate_skill_quality("Docker", claim_only_evidence)
    assert res1["status"] == "weak_evidence"
    assert res1["evidence_strength"] == "weak"
    assert res1["is_claim_only"] is True

    # Real implementation code
    real_code_evidence = [
        {
            "file_path": "database.sql",
            "is_claim_only": False,
            "evidence_type": "code",
            "snippet": "SELECT * FROM users;"
        },
        {
            "file_path": "services/db.py",
            "is_claim_only": False,
            "evidence_type": "code",
            "snippet": "cursor.execute('SELECT 1')"
        }
    ]
    res2 = quality_detector.evaluate_skill_quality("SQL", real_code_evidence)
    assert res2["status"] == "demonstrated"
    assert res2["evidence_strength"] == "strong"
    assert res2["is_claim_only"] is False

    # No evidence found
    res3 = quality_detector.evaluate_skill_quality("AWS", [])
    assert res3["status"] == "not_demonstrated"
    assert res3["evidence_strength"] == "none"
    assert "not demonstrated in the selected repositories" in res3["explanation"]

def test_job_extractor_and_match_scoring():
    sample_job = (
        "Role: Senior Backend Engineer\n"
        "Company: Acme Cloud\n"
        "Requirements:\n"
        "- Strong experience with Python and RESTful API development\n"
        "- Experience querying relational databases with SQL\n"
        "- Automated testing and unit test suites\n"
        "Preferred Qualifications:\n"
        "- Docker and containerization experience\n"
        "- Knowledge of AWS cloud services\n"
    )
    extracted = job_extractor.process_job_text(sample_job)
    canonical_skills = [r["canonical_skill"] for r in extracted["requirements"]]
    assert "Python" in canonical_skills
    assert "REST API" in canonical_skills
    assert "SQL" in canonical_skills
    assert "Docker" in canonical_skills
    assert "Automated Testing" in canonical_skills

    # Match scoring
    evidence = {
        "Python": [{"file_path": "app.py", "is_claim_only": False, "evidence_type": "code", "snippet": "def main():"}],
        "REST API": [{"file_path": "app.py", "is_claim_only": False, "evidence_type": "code", "snippet": "@app.get('/api')"}],
        "SQL": [],
        "Docker": [{"file_path": "README.md", "is_claim_only": True, "evidence_type": "claim", "snippet": "Uses Docker"}]
    }

    match_result = skill_matcher.assess(extracted["requirements"], evidence)
    assert "match_score" in match_result
    assert match_result["match_score"] > 0
    # SQL is required but missing -> must be in high_priority_gaps
    gap_skills = [g["canonical_skill"] for g in match_result["high_priority_gaps"]]
    assert "SQL" in gap_skills

def test_demo_commit_simulation():
    reset_demo_store()
    v1_files = get_demo_files("fastapi-ecommerce-service")
    file_names_v1 = [f["path"] for f in v1_files]
    assert "database.sql" not in file_names_v1

    # Simulate commit
    sim = simulate_git_commit(new_commit_sha="commit-a81f2c")
    assert sim["commit_sha"] == "commit-a81f2c"

    v2_files = get_demo_files("fastapi-ecommerce-service")
    file_names_v2 = [f["path"] for f in v2_files]
    assert "database.sql" in file_names_v2
    assert "Dockerfile" in file_names_v2

    reset_demo_store()
