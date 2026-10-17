# SkillProof AI — 5-Minute Live Hackathon Demo Script

Follow this step-by-step walkthrough to present the complete agentic assessment and reassessment workflow to judges.

---

## Demo Overview (5 Minutes)

| Part | Description | Time |
| :--- | :--- | :--- |
| **Part 1** | Target Job Input & Skill Normalization | 1 min |
| **Part 2** | Candidate GitHub & Scope Selection | 1 min |
| **Part 3** | Evidence Quality Detection (Novelty 1: Docker/SQL claims) | 1 min |
| **Part 4** | Repository Change & Automatic Reassessment | 1 min |
| **Part 5** | Job Requirement Change Detection (Novelty 2: AWS added) | 1 min |

---

## Step-by-Step Demo Procedure

### Part 1: Instant Launch or Job Input
1. Open `http://localhost:5173`.
2. Notice the modern developer interface with badge **W-PS-2**.
3. Click **"Instant 5-Min Demo"** (or click **"Analyze My GitHub"** and click **"Use Sample Posting"**).
4. Point out the **Skill Normalization Layer**:
   - Shows how raw phrases like *"relational database querying and SQL"* were mapped to canonical **SQL**.
   - Shows confidence percentages, importance flags (*Required* vs *Preferred*), and exact verbatim source text from the employer.

### Part 2: Repository Scope Selection
1. The GitHub Profile screen displays candidate repositories.
2. Highlight the ethical privacy disclosure:
   > *"Only selected repositories will be used as evidence for your career assessment."*
3. Demonstrate the **Select All** and **Clear All** controls.

### Part 3: Evidence Quality Detector (Novelty 1)
1. In the initial assessment dashboard:
   - Notice that **Docker** is marked as:
     **Weak Evidence (Claim Only)**
   - Explain to judges: The candidate's `README.md` stated *"Uses Docker containerization"*, but the repository contained **no Dockerfile or docker-compose.yml**.
   - Contrast this with verified code: **Python** and **REST API** are marked as **Demonstrated** with direct code lines in `app.py`.
2. Click **Docker** in the table to open the **Evidence Explorer**:
   - Show judges the exact line in `README.md` flagged as a claim only.

### Part 4: Git Push & Automatic Reassessment Loop
1. Show judges the live control bar at the top of the dashboard.
2. Click **"Simulate Commit (Push database.sql)"**:
   - This simulates a candidate pushing `database.sql` (with `CREATE TABLE`, `SELECT` queries) and a `Dockerfile`.
3. The continuous monitoring agent runs immediately:
   - It detects the new commit SHA.
   - It identifies that **SQL** and **Docker** are affected.
   - It automatically updates the assessment from **v1 to v2**.
4. The Match Score increases visibly!
5. **SQL** and **Docker** change from *Weak / Gap* to **Demonstrated**!
6. Scroll down to the **Assessment Change History & Audit Trail**:
   - Show the logged change event with commit SHA, timestamp, and status transition.

### Part 5: Job Requirement Change Detection (Novelty 2)
1. Explain to judges: *"Employers also update their requirements during hiring cycles."*
2. Click **"Simulate Job Change (+ AWS)"**:
   - The employer adds AWS cloud proficiency to the job posting.
3. The Job Requirement Monitor detects the change:
   - Updates Job version to **v2**.
   - Identifies `+ AWS` as a newly required skill.
   - Re-evaluates candidate repositories.
   - AWS is **Not Demonstrated** in the selected repositories.
   - The Job Match Score adjusts and AWS is highlighted under **High Priority Skill Gaps**.
4. Show judges the updated audit trail recording both candidate commits and job modifications working together.
