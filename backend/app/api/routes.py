import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import (
    Job, JobVersion, JobRequirement, CandidateProfile, Repository,
    Assessment, AssessmentItem, SelectedRepository, RepositoryEvidence, ChangeEvent
)
from app.schemas.dto import (
    JobAnalyzeRequest, JobAnalyzeResponse, ExtractedRequirementDTO,
    GithubProfileRequest, GithubProfileResponse, RepositoryDTO,
    StartAnalysisRequest, AssessmentDashboardResponse, ChangeEventDTO,
    ScoreBreakdownDTO, AssessmentItemDTO, EvidenceDTO,
    JobChangeTriggerRequest, RepoCommitTriggerRequest
)
from app.services.jobs.job_fetcher import fetch_and_clean_job_url
from app.services.jobs.job_extractor import job_extractor
from app.services.github.client import github_client
from app.services.github.repo_inspector import repo_inspector
from app.services.evidence.extractor import evidence_extractor
from app.services.assessment.matcher import skill_matcher
from app.services.monitoring.github_monitor import github_monitor
from app.services.monitoring.job_monitor import job_monitor
from app.demo.fixtures import (
    DEMO_USERNAME, DEMO_REPOSITORIES, DEMO_RUNTIME_STORE,
    get_demo_files, simulate_git_commit, reset_demo_store
)

router = APIRouter(prefix="/api")

@router.post("/jobs/analyze", response_model=JobAnalyzeResponse)
def analyze_job(req: JobAnalyzeRequest, db: Session = Depends(get_db)):
    raw_text = req.text or ""
    source_url = req.url

    if source_url:
        fetched_text, error = fetch_and_clean_job_url(source_url)
        if error and not raw_text:
            raise HTTPException(status_code=400, detail=error)
        elif fetched_text:
            raw_text = fetched_text

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Please provide either a valid job posting URL or paste the job description text.")

    extracted = job_extractor.process_job_text(raw_text, user_title=req.title, user_company=req.company)

    # Persist Job
    job = Job(
        title=extracted["title"],
        company=extracted["company"],
        source_url=source_url,
        current_version=1
    )
    db.add(job)
    db.flush()

    job_version = JobVersion(
        job_id=job.id,
        version_number=1,
        raw_description=raw_text
    )
    db.add(job_version)
    db.flush()

    response_reqs = []
    for r in extracted["requirements"]:
        db_req = JobRequirement(
            job_version_id=job_version.id,
            raw_skill=r["skill"],
            canonical_skill=r["canonical_skill"],
            importance=r["importance"],
            confidence=r["confidence"],
            source_text=r["source_text"]
        )
        db.add(db_req)
        response_reqs.append(ExtractedRequirementDTO(
            skill=r["skill"],
            canonical_skill=r["canonical_skill"],
            importance=r["importance"],
            confidence=r["confidence"],
            source_text=r["source_text"]
        ))

    db.commit()

    return JobAnalyzeResponse(
        job_id=job.id,
        version=1,
        title=job.title,
        company=job.company,
        source_url=job.source_url,
        requirements=response_reqs
    )

@router.post("/github/profile", response_model=GithubProfileResponse)
def get_github_profile(req: GithubProfileRequest, db: Session = Depends(get_db)):
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")

    # 1. Check for Demo User
    if username.lower() == DEMO_USERNAME.lower():
        profile = db.query(CandidateProfile).filter(CandidateProfile.username == DEMO_USERNAME).first()
        if not profile:
            profile = CandidateProfile(
                username=DEMO_USERNAME,
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
                html_url="https://github.com/demo-candidate"
            )
            db.add(profile)
            db.flush()

        # Sync demo repositories
        repo_dtos = []
        for d_repo in DEMO_REPOSITORIES:
            existing = db.query(Repository).filter(
                Repository.profile_id == profile.id,
                Repository.name == d_repo["name"]
            ).first()
            if not existing:
                existing = Repository(
                    profile_id=profile.id,
                    github_id=d_repo["id"],
                    name=d_repo["name"],
                    full_name=d_repo["full_name"],
                    description=d_repo["description"],
                    language=d_repo["language"],
                    stars=d_repo["stars"],
                    html_url=d_repo["html_url"],
                    default_branch=d_repo["default_branch"],
                    latest_commit_sha=DEMO_RUNTIME_STORE["latest_commit"] if d_repo["id"] == 901 else d_repo["latest_commit_sha"],
                    is_demo_fixture=True
                )
                db.add(existing)
                db.flush()
            else:
                if d_repo["id"] == 901:
                    existing.latest_commit_sha = DEMO_RUNTIME_STORE["latest_commit"]
                db.flush()

            repo_dtos.append(RepositoryDTO(
                id=existing.id,
                name=existing.name,
                full_name=existing.full_name,
                description=existing.description,
                language=existing.language,
                stars=existing.stars,
                html_url=existing.html_url,
                default_branch=existing.default_branch,
                latest_commit_sha=existing.latest_commit_sha,
                is_demo_fixture=True
            ))

        db.commit()
        return GithubProfileResponse(
            username=profile.username,
            avatar_url=profile.avatar_url,
            html_url=profile.html_url,
            repositories=repo_dtos
        )

    # 2. Real GitHub User
    try:
        user_info = github_client.get_user_profile(username)
        raw_repos = github_client.get_user_repositories(username)
    except PermissionError as pe:
        raise HTTPException(status_code=429, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch GitHub profile: {str(e)}")

    profile = db.query(CandidateProfile).filter(CandidateProfile.username == username).first()
    if not profile:
        profile = CandidateProfile(
            username=username,
            avatar_url=user_info.get("avatar_url"),
            html_url=user_info.get("html_url")
        )
        db.add(profile)
        db.flush()
    else:
        profile.avatar_url = user_info.get("avatar_url")
        profile.html_url = user_info.get("html_url")

    repo_dtos = []
    for r in raw_repos:
        repo_name = r.get("name")
        full_name = r.get("full_name")
        existing_repo = db.query(Repository).filter(
            Repository.profile_id == profile.id,
            Repository.name == repo_name
        ).first()

        latest_sha = github_client.get_latest_commit_sha(username, repo_name) or "head"

        if not existing_repo:
            existing_repo = Repository(
                profile_id=profile.id,
                github_id=r.get("id"),
                name=repo_name,
                full_name=full_name,
                description=r.get("description"),
                language=r.get("language"),
                stars=r.get("stargazers_count", 0),
                html_url=r.get("html_url"),
                default_branch=r.get("default_branch", "main"),
                latest_commit_sha=latest_sha,
                is_demo_fixture=False
            )
            db.add(existing_repo)
            db.flush()
        else:
            existing_repo.description = r.get("description")
            existing_repo.stars = r.get("stargazers_count", 0)
            existing_repo.latest_commit_sha = latest_sha

        repo_dtos.append(RepositoryDTO(
            id=existing_repo.id,
            name=existing_repo.name,
            full_name=existing_repo.full_name,
            description=existing_repo.description,
            language=existing_repo.language,
            stars=existing_repo.stars,
            html_url=existing_repo.html_url,
            default_branch=existing_repo.default_branch,
            latest_commit_sha=existing_repo.latest_commit_sha,
            is_demo_fixture=False
        ))

    db.commit()
    return GithubProfileResponse(
        username=profile.username,
        avatar_url=profile.avatar_url,
        html_url=profile.html_url,
        repositories=repo_dtos
    )

@router.post("/analysis/start", response_model=AssessmentDashboardResponse)
def start_analysis(req: StartAnalysisRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    profile = db.query(CandidateProfile).filter(CandidateProfile.username == req.username).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    if not req.selected_repo_ids:
        raise HTTPException(status_code=400, detail="Please select at least one GitHub repository to analyze.")

    repositories = db.query(Repository).filter(
        Repository.id.in_(req.selected_repo_ids),
        Repository.profile_id == profile.id
    ).all()

    if not repositories:
        raise HTTPException(status_code=400, detail="No matching repositories found.")

    # Fetch latest job requirements
    latest_job_version = job.versions[-1]
    req_dicts = [
        {
            "canonical_skill": r.canonical_skill,
            "importance": r.importance,
            "source_text": r.source_text
        }
        for r in latest_job_version.requirements
    ]

    # Create Assessment
    assessment = Assessment(
        job_id=job.id,
        profile_id=profile.id,
        version_number=1
    )
    db.add(assessment)
    db.flush()

    # Link Selected Repositories
    for repo in repositories:
        sel = SelectedRepository(assessment_id=assessment.id, repository_id=repo.id)
        db.add(sel)

    # Inspect Repositories and Extract Evidence
    evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}

    for repo in repositories:
        if repo.is_demo_fixture:
            repo_files = get_demo_files(repo.name)
        else:
            parts = repo.full_name.split("/")
            repo_files = repo_inspector.inspect_repository(parts[0], parts[1], repo.default_branch)

        for req_item in req_dicts:
            can_skill = req_item["canonical_skill"]
            extracted_items = evidence_extractor.extract_evidence_from_files(can_skill, repo_files, repo.html_url)
            for ev in extracted_items:
                ev["repo_name"] = repo.name
                # Persist to repository_evidence table
                db_ev = RepositoryEvidence(
                    repository_id=repo.id,
                    skill=can_skill,
                    evidence_type=ev.get("evidence_type", "code"),
                    file_path=ev.get("file_path", ""),
                    line_number=ev.get("line_number"),
                    snippet=ev.get("snippet"),
                    github_url=ev.get("github_url"),
                    evidence_strength=ev.get("evidence_strength", "moderate"),
                    explanation=ev.get("explanation", ""),
                    is_claim_only=ev.get("is_claim_only", False)
                )
                db.add(db_ev)
                db.flush()
                ev["id"] = db_ev.id

                if can_skill not in evidence_by_skill:
                    evidence_by_skill[can_skill] = []
                evidence_by_skill[can_skill].append(ev)

    # Run Skill Matching Engine
    assessment_result = skill_matcher.assess(req_dicts, evidence_by_skill)

    assessment.match_score = assessment_result["match_score"]
    assessment.required_skills_count = assessment_result["score_breakdown"]["required_count"]
    assessment.preferred_skills_count = assessment_result["score_breakdown"]["preferred_count"]
    assessment.demonstrated_count = assessment_result["score_breakdown"]["demonstrated_count"]
    assessment.partial_count = assessment_result["score_breakdown"]["partial_count"]
    assessment.weak_count = assessment_result["score_breakdown"]["weak_count"]
    assessment.not_demonstrated_count = assessment_result["score_breakdown"]["not_demonstrated_count"]

    # Persist Assessment Items
    for it in assessment_result["items"]:
        item = AssessmentItem(
            assessment_id=assessment.id,
            canonical_skill=it["canonical_skill"],
            importance=it["importance"],
            status=it["status"],
            evidence_strength=it["evidence_strength"],
            confidence=it["confidence"],
            explanation=it["explanation"],
            source_requirement_text=it["source_requirement_text"]
        )
        db.add(item)

    # Initial Change Event Log
    initial_event = ChangeEvent(
        assessment_id=assessment.id,
        event_type="INITIAL_ASSESSMENT",
        trigger_details=f"Initial evidence evaluation completed across {len(repositories)} selected repositories.",
        affected_skills=json.dumps([r["canonical_skill"] for r in req_dicts]),
        previous_state=None,
        new_state=json.dumps({"match_score": assessment.match_score, "version": 1})
    )
    db.add(initial_event)
    db.commit()

    return build_dashboard_response(assessment.id, db)

@router.get("/dashboard/{assessment_id}", response_model=AssessmentDashboardResponse)
def get_dashboard(assessment_id: int, db: Session = Depends(get_db)):
    return build_dashboard_response(assessment_id, db)

@router.post("/monitor/check/{assessment_id}")
def run_monitor_check(assessment_id: int, db: Session = Depends(get_db)):
    """
    Executes background monitor check immediately on demand:
    Checks for commit changes across selected repositories & checks for job source updates.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    repo_result = github_monitor.check_for_changes(assessment_id, db)
    job_result = job_monitor.check_for_job_changes(assessment.job_id, db)

    any_change = repo_result.get("changed", False) or job_result.get("changed", False)

    return {
        "status": "success",
        "changed": any_change,
        "github_monitor": repo_result,
        "job_monitor": job_result,
        "dashboard": build_dashboard_response(assessment_id, db) if any_change else None
    }

@router.post("/demo/commit")
def trigger_demo_commit(req: RepoCommitTriggerRequest, db: Session = Depends(get_db)):
    """
    Simulates a git push to demo repository (adds database.sql + Dockerfile).
    Note: Does not manually rewrite assessment; the monitor must be run (or polled)
    to automatically detect the change and perform reassessment!
    """
    sim_res = simulate_git_commit(
        new_commit_sha=req.commit_sha or "commit-a81f2c",
        new_files=req.added_files
    )
    return {
        "status": "pushed",
        "commit_sha": sim_res["commit_sha"],
        "changed_files": sim_res["changed_files"],
        "message": "Commit pushed to demo repository. Run monitor check to trigger automatic reassessment!"
    }

@router.post("/demo/job-change")
def trigger_demo_job_change(req: JobChangeTriggerRequest, db: Session = Depends(get_db)):
    """
    Simulates a change in the employer's job requirements (e.g. adding AWS).
    Triggers the Job Requirement Change Detector.
    """
    add_skills = req.add_skills or ["AWS"]
    res = job_monitor.check_for_job_changes(
        job_id=req.job_id,
        db=db,
        simulated_new_text=req.updated_description,
        added_skills=add_skills
    )
    return res

@router.post("/demo/reset")
def reset_demo():
    reset_demo_store()
    return {"status": "reset", "message": "Demo fixtures reset to v1 state."}

def build_dashboard_response(assessment_id: int, db: Session) -> AssessmentDashboardResponse:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    job = assessment.job
    profile = assessment.profile

    selected_links = db.query(SelectedRepository).filter(SelectedRepository.assessment_id == assessment.id).all()
    repo_ids = [sl.repository_id for sl in selected_links]
    selected_repos = db.query(Repository).filter(Repository.id.in_(repo_ids)).all()

    repo_dtos = [
        RepositoryDTO(
            id=r.id,
            name=r.name,
            full_name=r.full_name,
            description=r.description,
            language=r.language,
            stars=r.stars,
            html_url=r.html_url,
            default_branch=r.default_branch,
            latest_commit_sha=r.latest_commit_sha,
            is_demo_fixture=r.is_demo_fixture
        )
        for r in selected_repos
    ]

    # Gather evidence items for each skill
    all_evidence = db.query(RepositoryEvidence).filter(
        RepositoryEvidence.repository_id.in_(repo_ids)
    ).all()

    evidence_by_skill: Dict[str, List[EvidenceDTO]] = {}
    for ev in all_evidence:
        dto = EvidenceDTO(
            id=ev.id,
            repo_name=ev.repository.name,
            skill=ev.skill,
            evidence_type=ev.evidence_type,
            file_path=ev.file_path,
            line_number=ev.line_number,
            snippet=ev.snippet,
            github_url=ev.github_url,
            evidence_strength=ev.evidence_strength,
            explanation=ev.explanation,
            is_claim_only=ev.is_claim_only
        )
        if ev.skill not in evidence_by_skill:
            evidence_by_skill[ev.skill] = []
        evidence_by_skill[ev.skill].append(dto)

    skill_dtos = []
    high_priority_gaps = []

    for item in assessment.items:
        s_dto = AssessmentItemDTO(
            canonical_skill=item.canonical_skill,
            importance=item.importance,
            status=item.status,
            evidence_strength=item.evidence_strength,
            confidence=item.confidence,
            explanation=item.explanation,
            source_requirement_text=item.source_requirement_text,
            evidence=evidence_by_skill.get(item.canonical_skill, [])
        )
        skill_dtos.append(s_dto)
        if item.importance == "required" and item.status in ["weak_evidence", "not_demonstrated", "uncertain"]:
            high_priority_gaps.append(s_dto)

    change_events_dtos = []
    for ce in reversed(assessment.change_events):
        aff_list = []
        try:
            aff_list = json.loads(ce.affected_skills)
        except Exception:
            aff_list = [ce.affected_skills]

        change_events_dtos.append(ChangeEventDTO(
            id=ce.id,
            event_type=ce.event_type,
            trigger_details=ce.trigger_details,
            affected_skills=aff_list,
            previous_state=json.loads(ce.previous_state) if ce.previous_state else None,
            new_state=json.loads(ce.new_state) if ce.new_state else None,
            created_at=ce.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        ))

    score_breakdown = ScoreBreakdownDTO(
        required_count=assessment.required_skills_count,
        preferred_count=assessment.preferred_skills_count,
        demonstrated_count=assessment.demonstrated_count,
        partial_count=assessment.partial_count,
        weak_count=assessment.weak_count,
        not_demonstrated_count=assessment.not_demonstrated_count,
        formula_explanation=(
            f"Calculated from {assessment.required_skills_count} required skills (weighted 75%) and "
            f"{assessment.preferred_skills_count} preferred skills (weighted 25%). "
            "Demonstrated = 100%, Partially Demonstrated = 50%, Weak Claim = 15%, Not Demonstrated = 0%."
        )
    )

    return AssessmentDashboardResponse(
        assessment_id=assessment.id,
        version_number=assessment.version_number,
        job={
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "source_url": job.source_url,
            "current_version": job.current_version,
            "updated_at": job.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        },
        profile={
            "id": profile.id,
            "username": profile.username,
            "avatar_url": profile.avatar_url,
            "html_url": profile.html_url
        },
        match_score=assessment.match_score,
        score_breakdown=score_breakdown,
        skills=skill_dtos,
        high_priority_gaps=high_priority_gaps,
        selected_repositories=repo_dtos,
        change_events=change_events_dtos
    )
