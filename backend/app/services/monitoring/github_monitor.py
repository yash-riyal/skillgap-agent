import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.entities import (
    Assessment, AssessmentItem, SelectedRepository, Repository, 
    RepositoryEvidence, ChangeEvent, JobRequirement
)
from app.services.github.client import github_client
from app.services.github.repo_inspector import repo_inspector
from app.services.evidence.extractor import evidence_extractor
from app.services.assessment.matcher import skill_matcher
from app.demo.fixtures import DEMO_RUNTIME_STORE, get_demo_files

class GitHubChangeMonitor:
    """
    Monitors candidate repositories for new commits, identifies changed files,
    reassesses affected skills, updates assessment version, and logs change events.
    """

    def check_for_changes(self, assessment_id: int, db: Session) -> Dict[str, Any]:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found.")

        selected_links = db.query(SelectedRepository).filter(SelectedRepository.assessment_id == assessment_id).all()
        repo_ids = [sl.repository_id for sl in selected_links]
        repositories = db.query(Repository).filter(Repository.id.in_(repo_ids)).all()

        detected_changes = []

        for repo in repositories:
            latest_remote_sha = None
            if repo.is_demo_fixture:
                latest_remote_sha = DEMO_RUNTIME_STORE.get("latest_commit")
            else:
                parts = repo.full_name.split("/")
                if len(parts) == 2:
                    latest_remote_sha = github_client.get_latest_commit_sha(parts[0], parts[1])

            if latest_remote_sha and latest_remote_sha != repo.latest_commit_sha:
                prev_sha = repo.latest_commit_sha
                repo.latest_commit_sha = latest_remote_sha
                db.commit()

                detected_changes.append({
                    "repository": repo,
                    "previous_sha": prev_sha,
                    "new_sha": latest_remote_sha
                })

        if not detected_changes:
            return {
                "changed": False,
                "message": "No new commits detected across selected repositories.",
                "assessment_id": assessment_id,
                "version": assessment.version_number
            }

        # Repositories changed! Trigger automatic reassessment
        return self._reassess_assessment(assessment, detected_changes, db)

    def _reassess_assessment(self, assessment: Assessment, changes: List[Dict[str, Any]], db: Session) -> Dict[str, Any]:
        # 1. Fetch current job requirements
        latest_job_version = assessment.job.versions[-1]
        job_reqs = latest_job_version.requirements
        req_dicts = [
            {
                "canonical_skill": r.canonical_skill,
                "importance": r.importance,
                "source_text": r.source_text
            }
            for r in job_reqs
        ]

        # 2. Gather all files from selected repositories
        selected_links = db.query(SelectedRepository).filter(SelectedRepository.assessment_id == assessment.id).all()
        repo_ids = [sl.repository_id for sl in selected_links]
        repositories = db.query(Repository).filter(Repository.id.in_(repo_ids)).all()

        all_evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        affected_skills_set = set()

        for repo in repositories:
            if repo.is_demo_fixture:
                repo_files = get_demo_files(repo.name)
            else:
                parts = repo.full_name.split("/")
                repo_files = repo_inspector.inspect_repository(parts[0], parts[1], repo.default_branch)

            for req in req_dicts:
                can_skill = req["canonical_skill"]
                extracted = evidence_extractor.extract_evidence_from_files(can_skill, repo_files, repo.html_url)
                if extracted:
                    if can_skill not in all_evidence_by_skill:
                        all_evidence_by_skill[can_skill] = []
                    all_evidence_by_skill[can_skill].extend(extracted)
                    affected_skills_set.add(can_skill)

        # 3. Capture previous state summary for audit trail
        prev_score = assessment.match_score
        prev_items = {it.canonical_skill: it.status for it in assessment.items}

        # 4. Run skill matching engine
        assessment_result = skill_matcher.assess(req_dicts, all_evidence_by_skill)

        # 5. Update assessment record
        assessment.version_number += 1
        assessment.match_score = assessment_result["match_score"]
        assessment.demonstrated_count = assessment_result["score_breakdown"]["demonstrated_count"]
        assessment.partial_count = assessment_result["score_breakdown"]["partial_count"]
        assessment.weak_count = assessment_result["score_breakdown"]["weak_count"]
        assessment.not_demonstrated_count = assessment_result["score_breakdown"]["not_demonstrated_count"]

        # Clear old assessment items and persist new items
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

        # 6. Build Change Event
        change_desc = []
        for ch in changes:
            r = ch["repository"]
            change_desc.append(f"{r.name} commit {ch['previous_sha'][:7] if ch['previous_sha'] else 'init'} -> {ch['new_sha'][:7]}")

        new_items = {it["canonical_skill"]: it["status"] for it in assessment_result["items"]}

        # Identify skills that changed status
        status_transitions = []
        for s, new_st in new_items.items():
            old_st = prev_items.get(s, "not_demonstrated")
            if old_st != new_st:
                status_transitions.append(f"{s}: {old_st} -> {new_st}")
                affected_skills_set.add(s)

        event = ChangeEvent(
            assessment_id=assessment.id,
            event_type="GITHUB_REPOSITORY_CHANGED",
            trigger_details=f"GitHub commit detected: {'; '.join(change_desc)}. Updated: {', '.join(status_transitions) if status_transitions else 'Evidence refreshed'}.",
            affected_skills=json.dumps(list(affected_skills_set)),
            previous_state=json.dumps({"match_score": prev_score, "items": prev_items}),
            new_state=json.dumps({"match_score": assessment.match_score, "items": new_items})
        )
        db.add(event)
        db.commit()

        return {
            "changed": True,
            "event_type": "GITHUB_REPOSITORY_CHANGED",
            "assessment_id": assessment.id,
            "new_version": assessment.version_number,
            "previous_score": prev_score,
            "new_score": assessment.match_score,
            "affected_skills": list(affected_skills_set),
            "status_transitions": status_transitions,
            "message": f"Detected new commit! Automatically reassessed {len(affected_skills_set)} skills. Match score updated from {prev_score}% to {assessment.match_score}%."
        }

github_monitor = GitHubChangeMonitor()
