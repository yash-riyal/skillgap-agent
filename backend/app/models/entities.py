import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), default="Unknown")
    source_url = Column(Text, nullable=True)
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    versions = relationship("JobVersion", back_populates="job", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="job")

class JobVersion(Base):
    __tablename__ = "job_versions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    raw_description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="versions")
    requirements = relationship("JobRequirement", back_populates="version", cascade="all, delete-orphan")

class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id = Column(Integer, primary_key=True, index=True)
    job_version_id = Column(Integer, ForeignKey("job_versions.id"), nullable=False)
    raw_skill = Column(String(100), nullable=False)
    canonical_skill = Column(String(100), nullable=False, index=True)
    importance = Column(String(20), default="required")  # "required" or "preferred"
    confidence = Column(Float, default=0.9)
    source_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    version = relationship("JobVersion", back_populates="requirements")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    avatar_url = Column(String(255), nullable=True)
    html_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    repositories = relationship("Repository", back_populates="profile", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="profile")

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    github_id = Column(Integer, nullable=True)
    name = Column(String(100), nullable=False)
    full_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(50), nullable=True)
    stars = Column(Integer, default=0)
    html_url = Column(String(255), nullable=False)
    default_branch = Column(String(50), default="main")
    latest_commit_sha = Column(String(50), nullable=True)
    is_demo_fixture = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    profile = relationship("CandidateProfile", back_populates="repositories")
    evidence_items = relationship("RepositoryEvidence", back_populates="repository", cascade="all, delete-orphan")

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    version_number = Column(Integer, default=1)
    match_score = Column(Float, default=0.0)
    required_skills_count = Column(Integer, default=0)
    preferred_skills_count = Column(Integer, default=0)
    demonstrated_count = Column(Integer, default=0)
    partial_count = Column(Integer, default=0)
    weak_count = Column(Integer, default=0)
    not_demonstrated_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="assessments")
    profile = relationship("CandidateProfile", back_populates="assessments")
    items = relationship("AssessmentItem", back_populates="assessment", cascade="all, delete-orphan")
    change_events = relationship("ChangeEvent", back_populates="assessment", cascade="all, delete-orphan")
    selected_repos = relationship("SelectedRepository", back_populates="assessment", cascade="all, delete-orphan")

class SelectedRepository(Base):
    __tablename__ = "selected_repositories"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)

    assessment = relationship("Assessment", back_populates="selected_repos")
    repository = relationship("Repository")

class RepositoryEvidence(Base):
    __tablename__ = "repository_evidence"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    skill = Column(String(100), nullable=False, index=True)
    evidence_type = Column(String(50), default="code")  # code, config, test, claim, dependency
    file_path = Column(String(255), nullable=False)
    line_number = Column(Integer, nullable=True)
    snippet = Column(Text, nullable=True)
    github_url = Column(String(500), nullable=True)
    evidence_strength = Column(String(20), default="moderate")  # strong, moderate, weak, insufficient
    explanation = Column(Text, nullable=False)
    is_claim_only = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    repository = relationship("Repository", back_populates="evidence_items")

class AssessmentItem(Base):
    __tablename__ = "assessment_items"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    canonical_skill = Column(String(100), nullable=False)
    importance = Column(String(20), default="required")
    status = Column(String(30), default="not_demonstrated")  # demonstrated, partially_demonstrated, weak_evidence, not_demonstrated, uncertain
    evidence_strength = Column(String(20), default="none")  # strong, moderate, weak, insufficient, none
    confidence = Column(Float, default=0.8)
    explanation = Column(Text, nullable=False)
    source_requirement_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assessment = relationship("Assessment", back_populates="items")

class ChangeEvent(Base):
    __tablename__ = "change_events"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # GITHUB_REPOSITORY_CHANGED, JOB_REQUIREMENT_CHANGED
    trigger_details = Column(Text, nullable=False)  # JSON or text describing trigger
    affected_skills = Column(Text, nullable=False)   # comma-separated or JSON list
    previous_state = Column(Text, nullable=True)    # JSON state summary
    new_state = Column(Text, nullable=True)         # JSON state summary
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assessment = relationship("Assessment", back_populates="change_events")
