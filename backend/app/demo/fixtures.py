from typing import Dict, Any, List

DEMO_USERNAME = "demo-candidate"

DEMO_REPOSITORIES = [
    {
        "id": 901,
        "name": "fastapi-ecommerce-service",
        "full_name": "demo-candidate/fastapi-ecommerce-service",
        "description": "Production e-commerce backend service with order processing and user management.",
        "language": "Python",
        "stars": 14,
        "html_url": "https://github.com/demo-candidate/fastapi-ecommerce-service",
        "default_branch": "main",
        "latest_commit_sha": "init-commit-e4f1a0",
        "is_demo_fixture": True
    },
    {
        "id": 902,
        "name": "developer-portfolio-web",
        "full_name": "demo-candidate/developer-portfolio-web",
        "description": "Personal developer portfolio and project showcase built with modern React and TypeScript.",
        "language": "TypeScript",
        "stars": 6,
        "html_url": "https://github.com/demo-candidate/developer-portfolio-web",
        "default_branch": "main",
        "latest_commit_sha": "port-commit-b7c2d9",
        "is_demo_fixture": True
    }
]

# Initial files in fastapi-ecommerce-service (v1 state: Mentions Docker and SQL in README, but NO Dockerfile, NO SQL files)
DEMO_REPO_FILES_V1: Dict[str, str] = {
    "README.md": (
        "# FastAPI E-Commerce Service\n\n"
        "A scalable backend built with Python.\n"
        "This project uses Docker containerization and SQL database persistence.\n"
        "Features automated testing and RESTful endpoints.\n"
    ),
    "app.py": (
        "from fastapi import FastAPI, HTTPException\n\n"
        "app = FastAPI(title='E-Commerce API')\n\n"
        "@app.get('/api/v1/products')\n"
        "def list_products():\n"
        "    return [{'id': 1, 'name': 'Laptop', 'price': 999.99}]\n\n"
        "@app.post('/api/v1/orders')\n"
        "def create_order(item: dict):\n"
        "    return {'status': 'created', 'order_id': 101}\n"
    ),
    "tests/test_api.py": (
        "import pytest\n"
        "from fastapi.testclient import TestClient\n"
        "from app import app\n\n"
        "client = TestClient(app)\n\n"
        "def test_list_products():\n"
        "    response = client.get('/api/v1/products')\n"
        "    assert response.status_code == 200\n"
        "    assert len(response.json()) > 0\n"
    ),
    "requirements.txt": (
        "fastapi==0.110.0\n"
        "uvicorn==0.28.0\n"
        "pytest==8.0.0\n"
    ),
    ".gitignore": (
        "__pycache__/\n"
        "*.pyc\n"
        ".env\n"
    )
}

# In-memory store for demo repo state during runtime so simulated commits persist across requests
DEMO_RUNTIME_STORE: Dict[str, Any] = {
    "latest_commit": "init-commit-e4f1a0",
    "files": dict(DEMO_REPO_FILES_V1),
    "commit_history": [
        {"sha": "init-commit-e4f1a0", "message": "Initial release of backend service", "files": list(DEMO_REPO_FILES_V1.keys())}
    ]
}

def get_demo_files(repo_name: str) -> List[Dict[str, Any]]:
    files = []
    store_files = DEMO_RUNTIME_STORE["files"]
    for path, content in store_files.items():
        cat = "readme" if "readme" in path.lower() else ("test" if "test" in path.lower() else ("config" if "requirements" in path.lower() else "source"))
        if path.endswith(".sql"):
            cat = "sql"
        elif "docker" in path.lower():
            cat = "docker"
        files.append({
            "path": path,
            "content": content,
            "category": cat,
            "size": len(content)
        })
    return files

def simulate_git_commit(new_commit_sha: str = "commit-a81f2c", new_files: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Simulates a git push to the demo repository adding new files (e.g., database.sql with real queries).
    """
    if new_files is None:
        new_files = {
            "database.sql": (
                "-- User and Order Database Schema\n"
                "CREATE TABLE users (\n"
                "    id SERIAL PRIMARY KEY,\n"
                "    username VARCHAR(100) NOT NULL,\n"
                "    email VARCHAR(255) UNIQUE NOT NULL\n"
                ");\n\n"
                "CREATE TABLE orders (\n"
                "    id SERIAL PRIMARY KEY,\n"
                "    user_id INT REFERENCES users(id),\n"
                "    amount NUMERIC(10,2),\n"
                "    status VARCHAR(50)\n"
                ");\n\n"
                "SELECT u.username, COUNT(o.id) FROM users u\n"
                "JOIN orders o ON u.id = o.user_id\n"
                "GROUP BY u.username;\n"
            ),
            "Dockerfile": (
                "FROM python:3.11-slim\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\n"
                "COPY . .\n"
                "EXPOSE 8000\n"
                "CMD [\"uvicorn\", \"app:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n"
            )
        }

    DEMO_RUNTIME_STORE["files"].update(new_files)
    DEMO_RUNTIME_STORE["latest_commit"] = new_commit_sha
    DEMO_RUNTIME_STORE["commit_history"].append({
        "sha": new_commit_sha,
        "message": "Add PostgreSQL database schema and Dockerfile containerization",
        "files": list(new_files.keys())
    })

    return {
        "commit_sha": new_commit_sha,
        "changed_files": list(new_files.keys()),
        "message": "Commit pushed successfully to demo repository."
    }

def reset_demo_store():
    """
    Resets demo store to initial v1 state.
    """
    DEMO_RUNTIME_STORE["latest_commit"] = "init-commit-e4f1a0"
    DEMO_RUNTIME_STORE["files"] = dict(DEMO_REPO_FILES_V1)
    DEMO_RUNTIME_STORE["commit_history"] = [
        {"sha": "init-commit-e4f1a0", "message": "Initial release of backend service", "files": list(DEMO_REPO_FILES_V1.keys())}
    ]
