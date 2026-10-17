import httpx
from typing import Dict, Any, List, Optional
from app.config import GITHUB_TOKEN

class GitHubClient:
    def __init__(self, token: str = GITHUB_TOKEN):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SkillProof-AI-Career-Coach"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def get_user_profile(self, username: str) -> Dict[str, Any]:
        """
        Fetches GitHub user details.
        """
        url = f"{self.base_url}/users/{username}"
        with httpx.Client(timeout=10.0) as client:
            res = client.get(url, headers=self.headers)
            if res.status_code == 404:
                raise ValueError(f"GitHub user '{username}' was not found.")
            elif res.status_code == 403 and "rate limit" in res.text.lower():
                raise PermissionError("GitHub API rate limit reached. Add GITHUB_TOKEN to backend/.env or try again later.")
            elif res.status_code != 200:
                raise RuntimeError(f"GitHub API error: {res.status_code} - {res.text}")
            return res.json()

    def get_user_repositories(self, username: str) -> List[Dict[str, Any]]:
        """
        Fetches public repositories for the user.
        """
        url = f"{self.base_url}/users/{username}/repos?sort=updated&per_page=30"
        with httpx.Client(timeout=15.0) as client:
            res = client.get(url, headers=self.headers)
            if res.status_code == 404:
                raise ValueError(f"GitHub user '{username}' not found.")
            elif res.status_code == 403 and "rate limit" in res.text.lower():
                raise PermissionError("GitHub API rate limit reached. Add GITHUB_TOKEN to backend/.env or try again later.")
            elif res.status_code != 200:
                raise RuntimeError(f"GitHub API error: {res.status_code} - {res.text}")
            return res.json()

    def get_latest_commit_sha(self, owner: str, repo: str) -> Optional[str]:
        """
        Fetches latest commit SHA from default branch.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits?per_page=1"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=self.headers)
                if res.status_code == 200:
                    commits = res.json()
                    if commits:
                        return commits[0].get("sha")
        except Exception:
            pass
        return None

    def get_repo_contents(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """
        Fetches items at path in repository.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        with httpx.Client(timeout=10.0) as client:
            res = client.get(url, headers=self.headers)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
            return []

    def get_raw_file_content(self, owner: str, repo: str, file_path: str, branch: str = "main") -> Optional[str]:
        """
        Fetches raw text content of a file.
        """
        # Try raw.githubusercontent.com first
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(raw_url, headers=self.headers)
                if res.status_code == 200:
                    return res.text
        except Exception:
            pass

        # Fallback to contents API
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=self.headers)
                if res.status_code == 200:
                    import base64
                    content_b64 = res.json().get("content", "")
                    return base64.b64decode(content_b64).decode("utf-8", errors="ignore")
        except Exception:
            pass
        return None

github_client = GitHubClient()
