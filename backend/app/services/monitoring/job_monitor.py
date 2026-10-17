import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.entities import (
    Job, JobVersion, JobRequirement, Assessment, AssessmentItem, 
    SelectedRepository, Repository, ChangeEvent
)
from app.services.jobs.job_fetcher import fetch_and_clean_job_url
from app.services.jobs.job_extractor import job_extractor
from app.services.github.repo_inspector import repo_inspector
from app.services.evidence.extractor import evidence_extractor
from app.services.assessment.matcher import skill_matcher
from app.demo.fixtures import get_demo_files

class JobRequirementChangeMonitor:
    """
    Novelty 2: Monitors the job source for updates, detects newly added or removed requirements,
    re-runs skill assessment against candidate's selected repositories, updates job match score,
    and logs job requirement version history.
    """

    def check_for_job_changes(
        self,
        job_id: int,
        db: Session,
        simulated_new_text: Optional[str] = None,
        added_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        latest_version = job.versions[-1] if job.versions else None
        current_reqs = latest_version.requirements if latest_version else []
        old_canonical_skills = {r.canonical_skill: r for r in current_reqs}

        # 1. Fetch updated text (from URL, simulated text, or injected skills)
        new_text = None
        if simulated_new_text:
            new_text = simulated_new_text
        elif added_skills:
            # Append newly added skills to the previous job description
            appended = "\n\nAdditional Requirements:\n" + "\n".join([f"- Hands-on proficiency in {s}" for s in added_skills])
            new_text = (latest_version.raw_description if latest_version else "") + appended
        elif job.source_url:
            fetched, err = fetch_and_clean_job_url(job.source_url)
            if fetched and fetched != latest_version.raw_description:
                new_text = fetched

        if not new_text or (latest_version and new_text.strip() == latest_version.raw_description.strip()):
            return {
                "changed": False,
                "message": "Job requirements are unchanged.",
                "job_id": job_id,
                "current_version": job.current_version
            }

        # 2. Extract and normalize new requirements
        extracted = job_extractor.process_job_text(new_text, user_title=job.title, user_company=job.company)
        new_req_list = extracted["requirements"]
        new_canonical_skills = {r["canonical_skill"]: r for r in new_req_list}

        # 3. Detect Added and Removed skills
        added = [s for s in new_canonical_skills if s not in old_canonical_skills]
        removed = [s for s in old_canonical_skills if s not in new_canonical_skills]

        if not added and not removed:
            return {
                "changed": False,
                "message": "Job description refreshed, but no skill changes detected.",
                "job_id": job_id,
                "current_version": job.current_version
            }

        # 4. Create new JobVersion
        new_version_num = job.current_version + 1
        job.current_version = new_version_num
        new_jv = JobVersion(
            job_id=job.id,
            version_number=new_version_num,
            raw_description=new_text
        )
        db.add(new_jv)
        db.flush()

        for req in new_req_list:
            db_req = JobRequirement(
                job_version_id=new_jv.id,
                raw_skill=req["skill"],
                canonical_skill=req["canonical_skill"],
                importance=req["importance"],
                confidence=req["confidence"],
                source_text=req["source_text"]
            )
            db.add(db_req)
        db.commit()

        # 5. Automatically trigger reassessment for all active assessments referencing this job
        assessments = db.query(Assessment).filter(Assessment.job_id == job.id).all()
        reassessment_summaries = []

        for ass in assessments:
            res = self._reassess_for_job_change(ass, new_req_list, added, removed, db)
            reassessment_summaries.append(res)

        return {
            "changed": True,
            "event_type": "JOB_REQUIREMENT_CHANGED",
            "job_id": job.id,
            "job_version": new_version_num,
            "added_skills": added,
            "removed_skills": removed,
            "reassessments": reassessment_summaries,
            "message": f"Job requirement change detected! Added: {', '.join(added) if added else 'None'}. Removed: {', '.join(removed) if removed else 'None'}."
        }

    def _reassess_for_job_change(
        self,
        assessment: Assessment,
        new_req_list: List[Dict[str, Any]],
        added: List[str],
        removed: List[str],
        db: Session
    ) -> Dict[str, Any]:
        selected_links = db.query(SelectedRepository).filter(SelectedRepository.assessment_id == assessment.id).all()
        repo_ids = [sl.repository_id for sl in selected_links]
        repositories = db.query(Repository).filter(Repository.id.in_(repo_ids)).all()

        # Gather evidence across selected repos for all new requirements
        all_evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for repo in repositories:
            if repo.is_demo_fixture:
                repo_files = get_demo_files(repo.name)
            else:
                parts = repo.full_name.split("/")
                repo_files = repo_inspector.inspect_repository(parts[0], parts[1], repo.default_branch)

            for req in new_req_list:
                can_skill = req["canonical_skill"]
                extracted = evidence_extractor.extract_evidence_from_files(can_skill, repo_files, repo.html_url)
                if extracted:
                    if can_skill not in all_evidence_by_skill:
                        all_evidence_by_skill[can_skill] = []
                    all_evidence_by_skill[can_skill].extend(extracted)

        prev_score = assessment.match_score
        prev_items = {it.canonical_skill: it.status for it in assessment.items}

        assessment_result = skill_matcher.assess(new_req_list, all_evidence_by_skill)

        assessment.version_number += 1
        assessment.match_score = assessment_result["match_score"]
        assessment.demonstrated_count = assessment_result["score_breakdown"]["demonstrated_count"]
        assessment.partial_count = assessment_result["score_breakdown"]["partial_count"]
        assessment.weak_count = assessment_result["score_breakdown"]["weak_count"]
        assessment.not_demonstrated_count = assessment_result["score_breakdown"]["not_demonstrated_count"]

        # Clear old items & save updated items
        db.query(AssessmentItem).filter(AssessmentItem.assessment_id == assessment.id).delete()
        for it in assessment_result["items"]:
            db_item = AssessmentItem(
                assessment_id=assessment.id,
                canonical_skill=it["canonical_skill"],
                importance=it["importance"],
                status=it["status"],
                evidence_strength=it["evidence_strength"],
                confidence=it["confidence"],
                explanation=it["explanation"],
                source_requirement_text=it["source_requirement_text"]
            )
            db.add(db_item)

        new_items = {it["canonical_skill"]: it["status"] for it in assessment_result["items"]}

        event = ChangeEvent(
            assessment_id=assessment.id,
            event_type="JOB_REQUIREMENT_CHANGED",
            trigger_details=f"Job posting updated: Added skills [{', '.join(added)}]. Score changed from {prev_score}% to {assessment.match_score}%.",
            affected_skills=json.dumps(added + removed),
            previous_state=json.dumps({"match_score": prev_score, "items": prev_items}),
            new_state=json.dumps({"match_score": assessment.match_score, "items": new_items})
        )
        db.add(event)
        db.commit()

        return {
            "assessment_id": assessment.id,
            "version": assessment.version_number,
            "previous_score": prev_score,
            "new_score": assessment.match_score
        }

job_monitor = JobRequirementChangeMonitor()
