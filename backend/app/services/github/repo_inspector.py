from typing import Dict, Any, List, Set
from app.services.github.client import github_client

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", "__pycache__", 
    ".pytest_cache", "venv", ".venv", "env", "target", "vendor", ".idea", ".vscode"
}

PRIORITY_FILES = {
    "readme.md", "readme", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "requirements.txt", "pyproject.toml", "package.json", "setup.py", "gemfile",
    "pom.xml", "build.gradle", "schema.sql", "database.sql", "main.py", "app.py",
    "index.ts", "index.js", "server.js", "server.ts"
}

ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".js", ".sql", ".json", ".yml", ".yaml", ".md", ".toml", 
    ".txt", ".sh", ".java", ".go", ".rs", ".html", ".css"
}

class RepoInspector:
    def __init__(self, client=github_client):
        self.client = client

    def inspect_repository(self, owner: str, repo: str, branch: str = "main", max_files: int = 25) -> List[Dict[str, Any]]:
        """
        Traverses repo structure selectively, downloading relevant source/config/test files up to max_files.
        Returns a list of dicts: {"path": str, "content": str, "type": "readme"|"config"|"source"|"test"|"sql"}
        """
        collected_files: List[Dict[str, Any]] = []
        visited_dirs: Set[str] = set()

        def traverse_dir(path: str = ""):
            if len(collected_files) >= max_files:
                return
            if path in visited_dirs or path.lower() in IGNORED_DIRS:
                return
            visited_dirs.add(path)

            try:
                items = self.client.get_repo_contents(owner, repo, path)
            except Exception:
                return

            subdirs = []
            files_to_check = []

            for item in items:
                name = item.get("name", "")
                item_type = item.get("type", "")
                item_path = item.get("path", "")

                if item_type == "dir":
                    if name.lower() not in IGNORED_DIRS:
                        subdirs.append(item_path)
                elif item_type == "file":
                    lower_name = name.lower()
                    # Check if priority or allowed extension
                    is_priority = lower_name in PRIORITY_FILES or "test" in lower_name or "docker" in lower_name
                    has_ext = any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS)
                    
                    if is_priority:
                        files_to_check.insert(0, (item_path, lower_name, item.get("size", 0)))
                    elif has_ext:
                        files_to_check.append((item_path, lower_name, item.get("size", 0)))

            # Process files in current directory
            for fpath, fname, fsize in files_to_check:
                if len(collected_files) >= max_files:
                    break
                # Skip files larger than 150KB
                if fsize > 150 * 1024:
                    continue

                content = self.client.get_raw_file_content(owner, repo, fpath, branch)
                if content:
                    file_category = self._categorize_file(fpath, fname)
                    collected_files.append({
                        "path": fpath,
                        "content": content[:15000],  # keep first 15KB per file
                        "category": file_category,
                        "size": fsize
                    })

            # Recurse into subdirectories prioritizing tests/routes/src/controllers
            subdirs.sort(key=lambda d: 0 if any(k in d.lower() for k in ["test", "api", "route", "service", "src", "db"]) else 1)
            for sdir in subdirs:
                if len(collected_files) >= max_files:
                    break
                traverse_dir(sdir)

        traverse_dir("")
        return collected_files

    def _categorize_file(self, path: str, name: str) -> str:
        lower = path.lower()
        if "readme" in lower:
            return "readme"
        elif "test" in lower or "spec" in lower:
            return "test"
        elif lower.endswith(".sql") or "migration" in lower or "database" in lower:
            return "sql"
        elif "docker" in lower:
            return "docker"
        elif any(lower.endswith(cfg) for cfg in ["package.json", "requirements.txt", "pyproject.toml", "pom.xml"]):
            return "config"
        elif any(lower.endswith(ext) for ext in [".py", ".ts", ".js", ".java", ".go"]):
            return "source"
        return "other"

repo_inspector = RepoInspector()
