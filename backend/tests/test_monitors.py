import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.entities import (
    Base, Job, JobVersion, JobRequirement, CandidateProfile, Repository, 
    Assessment, SelectedRepository, AssessmentItem
)
from app.services.monitoring.github_monitor import github_monitor
from app.services.monitoring.job_monitor import job_monitor
from app.demo.fixtures import DEMO_USERNAME, reset_demo_store, simulate_git_commit

@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

def test_full_github_change_and_reassessment_cycle(db_session):
    reset_demo_store()

    # 1. Setup Job
    job = Job(title="Backend Engineer", company="Demo Corp", current_version=1)
    db_session.add(job)
    db_session.flush()

    jv = JobVersion(job_id=job.id, version_number=1, raw_description="Requires SQL and Python.")
    db_session.add(jv)
    db_session.flush()

    req_sql = JobRequirement(job_version_id=jv.id, raw_skill="SQL", canonical_skill="SQL", importance="required", source_text="Must know SQL")
    req_py = JobRequirement(job_version_id=jv.id, raw_skill="Python", canonical_skill="Python", importance="required", source_text="Must know Python")
    db_session.add_all([req_sql, req_py])
    db_session.flush()

    # 2. Setup Profile & Repository
    profile = CandidateProfile(username=DEMO_USERNAME)
    db_session.add(profile)
    db_session.flush()

    repo = Repository(
        profile_id=profile.id,
        name="fastapi-ecommerce-service",
        full_name="demo-candidate/fastapi-ecommerce-service",
        html_url="https://github.com/demo-candidate/fastapi-ecommerce-service",
        latest_commit_sha="init-commit-e4f1a0",
        is_demo_fixture=True
    )
    db_session.add(repo)
    db_session.flush()

    # 3. Assessment v1: SQL is claim-only (in README), Python is demonstrated
    ass = Assessment(job_id=job.id, profile_id=profile.id, version_number=1, match_score=50.0)
    db_session.add(ass)
    db_session.flush()

    sel = SelectedRepository(assessment_id=ass.id, repository_id=repo.id)
    db_session.add(sel)

    item_sql = AssessmentItem(
        assessment_id=ass.id, canonical_skill="SQL", importance="required",
        status="weak_evidence", evidence_strength="weak", confidence=0.85,
        explanation="Claimed in README, but no actual implementation detected."
    )
    item_py = AssessmentItem(
        assessment_id=ass.id, canonical_skill="Python", importance="required",
        status="demonstrated", evidence_strength="strong", confidence=0.95,
        explanation="Implementation code found in app.py."
    )
    db_session.add_all([item_sql, item_py])
    db_session.commit()

    # Verify no change before commit
    check1 = github_monitor.check_for_changes(ass.id, db_session)
    assert check1["changed"] is False

    # 4. Candidate pushes commit with database.sql
    simulate_git_commit("commit-a81f2c")

    # 5. Monitor detects change and triggers automatic reassessment!
    check2 = github_monitor.check_for_changes(ass.id, db_session)
    assert check2["changed"] is True
    assert check2["new_version"] == 2
    assert "SQL" in check2["affected_skills"]

    # In v2, SQL must be Demonstrated
    updated_sql_item = db_session.query(AssessmentItem).filter(
        AssessmentItem.assessment_id == ass.id,
        AssessmentItem.canonical_skill == "SQL"
    ).first()
    assert updated_sql_item.status == "demonstrated"
    assert updated_sql_item.evidence_strength == "strong"

    # Match score should increase
    assert check2["new_score"] > check2["previous_score"]

    # 6. Novelty 2: Job requirement changes - Employer adds AWS
    job_change = job_monitor.check_for_job_changes(job.id, db_session, added_skills=["AWS"])
    assert job_change["changed"] is True
    assert "AWS" in job_change["added_skills"]

    # Check updated assessment item for AWS
    aws_item = db_session.query(AssessmentItem).filter(
        AssessmentItem.assessment_id == ass.id,
        AssessmentItem.canonical_skill == "AWS"
    ).first()
    assert aws_item is not None
    assert aws_item.status == "not_demonstrated"

    reset_demo_store()
