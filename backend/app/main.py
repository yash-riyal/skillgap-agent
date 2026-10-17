import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import PORT, FRONTEND_URL
from app.database.session import Base, engine
from app.api.routes import router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SkillProof AI — Evidence-Based AI Career Coach API",
    description="Agentic career coach that compares real job requirements with candidate GitHub repository evidence.",
    version="1.0.0"
)

# Enable CORS for frontend Vite application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "name": "SkillProof AI API",
        "description": "Evidence-Based AI Career Coach",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "job_analysis": "POST /api/jobs/analyze",
            "github_profile": "POST /api/github/profile",
            "start_analysis": "POST /api/analysis/start",
            "dashboard": "GET /api/dashboard/{assessment_id}",
            "monitor_check": "POST /api/monitor/check/{assessment_id}",
            "demo_commit": "POST /api/demo/commit",
            "demo_job_change": "POST /api/demo/job-change",
            "demo_reset": "POST /api/demo/reset"
        }
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
