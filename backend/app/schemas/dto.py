from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class JobAnalyzeRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None

class ExtractedRequirementDTO(BaseModel):
    skill: str
    canonical_skill: str
    importance: str = "required"  # "required" or "preferred"
    confidence: float = 0.9
    source_text: str

class JobAnalyzeResponse(BaseModel):
    job_id: int
    version: int
    title: str
    company: str
    source_url: Optional[str]
    requirements: List[ExtractedRequirementDTO]

class GithubProfileRequest(BaseModel):
    username: str

class RepositoryDTO(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    html_url: str
    default_branch: str = "main"
    latest_commit_sha: Optional[str] = None
    is_demo_fixture: bool = False

class GithubProfileResponse(BaseModel):
    username: str
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None
    repositories: List[RepositoryDTO]

class StartAnalysisRequest(BaseModel):
    job_id: int
    username: str
    selected_repo_ids: List[int]

class EvidenceDTO(BaseModel):
    id: int
    repo_name: str
    skill: str
    evidence_type: str
    file_path: str
    line_number: Optional[int] = None
    snippet: Optional[str] = None
    github_url: Optional[str] = None
    evidence_strength: str
    explanation: str
    is_claim_only: bool

class AssessmentItemDTO(BaseModel):
    canonical_skill: str
    importance: str
    status: str
    evidence_strength: str
    confidence: float
    explanation: str
    source_requirement_text: Optional[str] = None
    evidence: List[EvidenceDTO] = []

class ScoreBreakdownDTO(BaseModel):
    required_count: int
    preferred_count: int
    demonstrated_count: int
    partial_count: int
    weak_count: int
    not_demonstrated_count: int
    formula_explanation: str

class ChangeEventDTO(BaseModel):
    id: int
    event_type: str
    trigger_details: str
    affected_skills: List[str]
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    created_at: str

class AssessmentDashboardResponse(BaseModel):
    assessment_id: int
    version_number: int
    job: Dict[str, Any]
    profile: Dict[str, Any]
    match_score: float
    score_breakdown: ScoreBreakdownDTO
    skills: List[AssessmentItemDTO]
    high_priority_gaps: List[AssessmentItemDTO]
    selected_repositories: List[RepositoryDTO]
    change_events: List[ChangeEventDTO]

class JobChangeTriggerRequest(BaseModel):
    job_id: int
    updated_description: Optional[str] = None
    add_skills: Optional[List[str]] = None

class RepoCommitTriggerRequest(BaseModel):
    assessment_id: int
    repository_id: int
    commit_sha: Optional[str] = None
    added_files: Optional[Dict[str, str]] = None  # filename -> content
