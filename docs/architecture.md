# SkillProof AI — Architectural Specification

## 1. Executive Overview

**SkillProof AI** is an evidence-based agentic AI career coach built for hackathon challenge **W-PS-2**.

Instead of accepting resume claims or giving generic chatbot advice, SkillProof AI constructs an **evidence graph** linking real employer job postings to verified code artifacts in candidate GitHub repositories. It continuously maintains this graph across repository pushes and job posting mutations.

---

## 2. Core Agentic Workflow

```
REAL JOB REQUIREMENTS
        ↓
SKILL NORMALIZATION (Taxonomy + Aliases)
        ↓
GITHUB REPOSITORY EVIDENCE (Deterministic Inspector + Snippets)
        ↓
EVIDENCE QUALITY DETECTOR (Novelty 1: Claims vs Implementation)
        ↓
SKILL ASSESSMENT & EXPLAINABLE MATCH SCORE
        ↓
EVIDENCE-BACKED SKILL GAPS
        ↓
AUTOMATIC REASSESSMENT LOOP (Novelty 2: Git Pushes & Job Source Mutations)
```

---

## 3. The 9 Logical Agents & Services

1. **Job Research Agent (`job_fetcher.py`)**: Fetches HTML from public job links, strips extraneous tags, and cleans raw text.
2. **Job Extraction Agent (`job_extractor.py`)**: Identifies title, company, required competencies, and preferred qualifications with confidence ratings.
3. **Skill Normalization Agent (`normalizer.py`)**: Maps unstructured requirements to canonical skill entities via hierarchical JSON taxonomy.
4. **GitHub Profile Agent (`github/client.py`)**: Queries public GitHub APIs for repository metadata, branches, and commit SHAs.
5. **Repository Evidence Agent (`repo_inspector.py` & `extractor.py`)**: Filters repository files, inspects AST patterns, route decorators, test suites, and Dockerfiles.
6. **Evidence Quality Agent (`quality_detector.py` — Novelty 1)**: Evaluates documentation claims vs runnable code to prevent false positives.
7. **Skill Assessment Engine (`matcher.py`)**: Weighted scoring engine (75% Required / 25% Preferred) calculating explainable match score and gap alerts.
8. **GitHub Change Monitor (`github_monitor.py`)**: Detects commit changes, identifies diffs, and triggers automatic reassessment.
9. **Job Requirement Monitor (`job_monitor.py` — Novelty 2)**: Detects job posting changes, identifies added/removed skills, and updates match scores.

---

## 4. Novelty 1: Evidence Quality Detector

The system enforces rigorous separation between **claims** and **implementation evidence**:

| Level | Definition | Example |
| :--- | :--- | :--- |
| **Strong Evidence** | Executable source code, dedicated schemas, or tests. | `database.sql` containing real `SELECT` queries, `Dockerfile`, `tests/test_api.py` |
| **Moderate Evidence** | Direct code implementation with limited supporting tests. | Single route handler in `app.py` |
| **Weak Evidence** | Claimed in documentation or README without runnable code. | `README.md` mentions "Docker containerized", but repo has no container files |
| **Not Demonstrated** | No mentions or code found in candidate's selected repositories. | Candidate has no files or mentions of AWS |

> **Ethical Language Rule:** The system never declares *"Candidate does not know SQL"*; it states *"SQL is not demonstrated in the selected repositories."*

---

## 5. Novelty 2: Job Requirement Change Detection

Employer job descriptions are dynamic. When a job description changes:
1. The monitor fetches updated text or receives posting diffs.
2. The pipeline extracts and normalizes new skills.
3. Added or removed skills are isolated (`+ AWS`).
4. Selected candidate repositories are reassessed against the updated requirement set.
5. The Job Match Score updates with an audit trail entry.

---

## 6. Database Schema

- `jobs`: Stores posting metadata, company, title, source URL, and version number.
- `job_versions`: Historical snapshots of job descriptions.
- `job_requirements`: Normalized canonical skills, importance (`required` / `preferred`), confidence, and verbatim source snippets.
- `candidate_profiles`: GitHub profile details.
- `repositories`: Metadata, default branch, and latest commit SHA.
- `selected_repositories`: Scope links specifying candidate-chosen repositories.
- `repository_evidence`: Traceable code artifacts (file path, line number, snippet, GitHub URL).
- `assessments`: Versioned match scores and skill breakdown statistics.
- `assessment_items`: Granular skill status and explanatory verdicts.
- `change_events`: Auditable log of commits and job modifications triggering reassessments.
