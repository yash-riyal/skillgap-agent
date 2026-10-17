# SkillProof AI — Evidence-Based AI Career Coach

> **Hackathon Track:** W-PS-2 — AI Career Coach  
> **Tagline:** Know what your portfolio actually proves.

SkillProof AI compares real job requirements with verified implementation evidence from candidate GitHub repositories, distinguishing unverified documentation claims from working code, and continuously updates the assessment as candidate work or employer requirements change.

---

## 1. Problem Statement (W-PS-2)

Traditional career tools rely on unverified resume claims or generate generic AI advice. SkillProof AI answers the fundamental technical career question:

> *"What skills does this real job require, what does the candidate's actual GitHub work prove, what skills are missing or weakly demonstrated, and how does that assessment change when the candidate's work or the job requirements change?"*

### Required Agentic Loop
```
REAL JOB REQUIREMENTS
        ↓
GITHUB REPOSITORY EVIDENCE
        ↓
SKILL ASSESSMENT
        ↓
SKILL GAPS
        ↓
REPOSITORY CHANGE
        ↓
AUTOMATIC REASSESSMENT
```

---

## 2. Key Novelties & Capabilities

### Novelty 1: Evidence Quality Detector
The system differentiates between **claimed skills** and **executable implementation**:
- **Claim-Only:** A skill mentioned in `README.md` without runnable code or configuration (e.g. claiming Docker with no `Dockerfile` or `docker-compose.yml`) is categorized as **Weak Evidence**.
- **Verified Implementation:** Direct code, dedicated schemas (e.g. `database.sql`), and test suites qualify as **Strong Evidence**.
- **Ethical Language:** The system never says *"You do not know SQL"*; it uses:
  > *"SQL is not demonstrated in the selected repositories."*

### Novelty 2: Job Requirement Change Detection
Employer job postings are dynamic:
- Monitors the job posting source URL or description.
- Automatically extracts and normalizes newly added requirements (e.g. `+ AWS`).
- Automatically reassesses candidate repositories against the updated requirement set and updates the Job Match Score and Gap Priority alerts.

### Candidate-Controlled Selective Scope
Candidates choose which repositories count as evidence (*Select All* / *Clear All*). Only selected repositories are inspected and monitored.

---

## 3. Technology Stack

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide React
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, BeautifulSoup4, Pydantic v2, Pytest
- **Database:** SQLite (local zero-setup default) / PostgreSQL ready
- **LLM Engine:** Provider-agnostic abstraction supporting **Heuristic** (instant offline mode), **OpenAI**, and **Gemini** via environment variables
- **Integrations:** GitHub REST API v3

---

## 4. Project Structure

```
AI-Career-Coach/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI server entrypoint & CORS
│   │   ├── config.py                  # Environment config
│   │   ├── api/
│   │   │   └── routes.py              # Endpoints for job, github, analysis, monitoring
│   │   ├── models/
│   │   │   └── entities.py            # SQLAlchemy database models
│   │   ├── schemas/
│   │   │   └── dto.py                 # Pydantic request/response schemas
│   │   ├── database/
│   │   │   └── session.py             # Engine & SessionLocal
│   │   ├── services/
│   │   │   ├── jobs/                  # Fetcher & requirement extractor
│   │   │   ├── normalization/         # Taxonomy & skill normalizer
│   │   │   ├── github/                # GitHub client & repo inspector
│   │   │   ├── evidence/              # Evidence extractor & Quality Detector (Novelty 1)
│   │   │   ├── assessment/            # Skill matching engine & explainable scorer
│   │   │   ├── monitoring/            # Commit monitor & Job monitor (Novelty 2)
│   │   │   └── llm/                   # Provider abstraction (Heuristic, OpenAI, Gemini)
│   │   └── demo/
│   │       └── fixtures.py            # Controlled demo repositories (v1/v2 commits)
│   ├── tests/
│   │   ├── test_core.py               # Normalization, quality detector & scoring tests
│   │   └── test_monitors.py           # Full reassessment loop integration tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/                # Navbar, LandingHero, JobInput, GithubRepo, Dashboard
│   │   ├── services/                  # Frontend API client
│   │   ├── types/                     # TypeScript data interfaces
│   │   ├── App.tsx                    # Main state machine & flow controller
│   │   └── index.css                  # Tailwind styles
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docs/
│   ├── architecture.md               # Detailed system design
│   └── demo.md                       # 5-minute hackathon judge demo script
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 5. Quick Start Instructions

### Prerequisites
- Node.js 18+ & npm
- Python 3.10+

### Option A: Local Run (Recommended for Hackathon Demo)

#### 1. Start the Backend
```bash
# In project root
cd backend

# (Optional) Activate your virtual environment
python -m pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Backend API will start at: `http://127.0.0.1:8000`  
Interactive Swagger docs: `http://127.0.0.1:8000/docs`

#### 2. Start the Frontend
```bash
# In a separate terminal
cd frontend

npm install
npm run dev
```
Frontend application will open at: `http://localhost:5173`

---

## 6. Environment Variables (`backend/.env`)

```env
# Database: SQLite by default; use PostgreSQL in production
DATABASE_URL=sqlite:///./skillproof.db

# GitHub API Token (Optional: increases rate limits from 60 to 5,000 req/hr)
GITHUB_TOKEN=

# LLM Provider: 'heuristic' (zero-cost offline mode), 'openai', or 'gemini'
LLM_PROVIDER=heuristic

# Provider API Keys (Only required if LLM_PROVIDER is openai or gemini)
OPENAI_API_KEY=
GEMINI_API_KEY=

PORT=8000
FRONTEND_URL=http://localhost:5173
```

---

## 7. Running Tests

Run the backend unit and integration test suite:
```bash
# In project root
$env:PYTHONPATH="backend"
python -m pytest backend/tests -v
```

All 5 core suites test:
1. Skill normalization & canonical taxonomy lookup
2. Evidence quality detection (Claims vs Implementation)
3. Job requirement extraction & explainable scoring
4. Demo commit simulation & state transitions
5. Full continuous reassessment loop (Git commit + Job posting changes)

---

## 8. Live Demo Walkthrough (5 Minutes)

1. Open `http://localhost:5173`.
2. Click **"Instant 5-Min Demo"** to load the controlled demo candidate (`demo-candidate`).
3. View initial assessment:
   - **Docker** is marked **Weak Evidence (Claim Only)** because `README.md` claims Docker, but no `Dockerfile` exists.
   - **SQL** is marked **Not Demonstrated** because no queries or schemas exist yet.
4. Click **"Simulate Commit (Push database.sql)"**:
   - Pushes a simulated commit containing `database.sql` and `Dockerfile`.
   - The monitoring agent detects the commit automatically.
   - Assessment advances from **v1 to v2**.
   - **SQL** and **Docker** transition to **Demonstrated**!
   - Job Match Score increases visibly!
5. Click **"Simulate Job Change (+ AWS)"**:
   - The employer adds AWS to the job requirements.
   - The Job Requirement Monitor detects the addition, advances to **v3**, and marks AWS as a **High Priority Gap**.
6. Check the **Audit Trail & Change History** at the bottom of the page to review every automated event with commit SHAs and timestamps.

---

## 9. Known Limitations & Next Steps

- **Private Repositories:** Current MVP targets public repositories. GitHub OAuth can be added to support private repos securely.
- **AST Parsing:** Enhanced deep AST analysis for specialized languages (e.g. Rust, Go).
- **Automated Webhooks:** In production, GitHub Webhooks and job board RSS/APIs can complement polling monitors.

---

## 10. License

Built for the Agentic AI Hackathon (W-PS-2). MIT License.
