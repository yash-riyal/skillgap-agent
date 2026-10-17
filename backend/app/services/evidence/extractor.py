import re
from typing import Dict, Any, List

class EvidenceExtractor:
    """
    Performs deterministic pattern matching on repository files to extract
    direct implementation evidence, configurations, tests, and documentation claims.
    """

    PATTERNS = {
        "SQL": {
            "file_patterns": [r"\.sql$", r"schema", r"migration"],
            "code_patterns": [
                r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|ALTER TABLE|JOIN)\b",
                r"\b(sqlalchemy|sqlite3|psycopg2|mysql\.connector|typeorm|prisma)\b"
            ],
            "claim_patterns": [r"\b(sql|database|postgres|mysql|sqlite)\b"]
        },
        "Docker": {
            "file_patterns": [r"dockerfile", r"docker-compose\.ya?ml"],
            "code_patterns": [
                r"^FROM\s+[\w\/\:\.\-]+",
                r"version:\s*['\"]?[23][\.\d]*['\"]?",
                r"services:\s*"
            ],
            "claim_patterns": [r"\bdocker\b", r"\bcontainer\b", r"\bcontainerization\b"]
        },
        "REST API": {
            "file_patterns": [r"route", r"controller", r"endpoint", r"api"],
            "code_patterns": [
                r"@(app|router)\.(get|post|put|delete|patch)",
                r"app\.(get|post|put|delete|patch)\(",
                r"router\.(get|post|put|delete|patch)\(",
                r"ResponseEntity|@RestController|@RequestMapping"
            ],
            "claim_patterns": [r"\brest\s*api\b", r"\brestful\b", r"\bapi\b"]
        },
        "Python": {
            "file_patterns": [r"\.py$", r"requirements\.txt", r"pyproject\.toml", r"setup\.py"],
            "code_patterns": [
                r"\bdef\s+\w+\s*\(",
                r"\bclass\s+\w+[\(\:]",
                r"\bimport\s+[\w\.]+",
                r"\bfrom\s+[\w\.]+\s+import"
            ],
            "claim_patterns": [r"\bpython\b", r"\bpython3\b"]
        },
        "Automated Testing": {
            "file_patterns": [r"test_.*\.py$", r".*_test\.py$", r"\.test\.(js|ts|jsx|tsx)$", r"\.spec\.(js|ts)$"],
            "code_patterns": [
                r"\bdef\s+test_\w+\s*\(",
                r"\bassert\s+",
                r"\b(describe|it|test)\s*\(",
                r"\bexpect\s*\(",
                r"@pytest\.fixture"
            ],
            "claim_patterns": [r"\bunit test\b", r"\bpytest\b", r"\bjest\b", r"\btesting\b"]
        },
        "Git": {
            "file_patterns": [r"\.gitignore$", r"\.github\/workflows"],
            "code_patterns": [
                r"name:\s*[\w\s]+",
                r"on:\s*\[?push"
            ],
            "claim_patterns": [r"\bgit\b", r"\bgithub\b"]
        },
        "AWS": {
            "file_patterns": [r"aws", r"cloudformation", r"serverless\.yml"],
            "code_patterns": [
                r"\bboto3\b",
                r"@aws-sdk\/",
                r"\baws_access_key_id\b",
                r"AWS::"
            ],
            "claim_patterns": [r"\baws\b", r"\bamazon web services\b", r"\bs3\b", r"\bec2\b"]
        },
        "TypeScript": {
            "file_patterns": [r"\.tsx?$", r"tsconfig\.json"],
            "code_patterns": [
                r"interface\s+\w+",
                r"type\s+\w+\s*=",
                r":\s*(string|number|boolean|any)[\s\,\;\)]"
            ],
            "claim_patterns": [r"\btypescript\b"]
        },
        "React": {
            "file_patterns": [r"\.jsx$", r"\.tsx$", r"react"],
            "code_patterns": [
                r"import\s+React\b",
                r"use(State|Effect|Context|Reducer|Ref|Memo|Callback)\(",
                r"<\w+[\s\>].*<\/\w+>"
            ],
            "claim_patterns": [r"\breact\b", r"\breactjs\b"]
        },
        "GraphQL": {
            "file_patterns": [r"\.graphql$", r"\.gql$", r"schema"],
            "code_patterns": [
                r"\btype\s+Query\b",
                r"\btype\s+Mutation\b",
                r"gql`",
                r"buildSchema\("
            ],
            "claim_patterns": [r"\bgraphql\b"]
        },
        "CI/CD": {
            "file_patterns": [r"\.github\/workflows\/.*\.ya?ml$", r"\.gitlab-ci\.yml$", r"Jenkinsfile$"],
            "code_patterns": [
                r"runs-on:\s*ubuntu",
                r"steps:\s*-",
                r"actions\/checkout"
            ],
            "claim_patterns": [r"\bci\/cd\b", r"\bcontinuous integration\b", r"\bgithub actions\b"]
        },
        "Redis": {
            "file_patterns": [r"redis"],
            "code_patterns": [
                r"\bredis\.(createClient|Redis)\(",
                r"import\s+redis",
                r"StrictRedis"
            ],
            "claim_patterns": [r"\bredis\b", r"\bcaching\b"]
        }
    }

    def extract_evidence_from_files(self, skill: str, files: List[Dict[str, Any]], repo_url: str = "") -> List[Dict[str, Any]]:
        evidence_list = []
        rules = self.PATTERNS.get(skill)

        # If skill not in exact pattern dict, create default heuristic rules
        if not rules:
            safe_skill = re.escape(skill.lower())
            rules = {
                "file_patterns": [safe_skill],
                "code_patterns": [rf"\b{safe_skill}\b"],
                "claim_patterns": [rf"\b{safe_skill}\b"]
            }

        for file_info in files:
            path = file_info["path"]
            content = file_info["content"]
            category = file_info.get("category", "")
            lines = content.splitlines()

            # Check if file name itself matches file patterns
            matched_file_pattern = False
            for fp in rules["file_patterns"]:
                if re.search(fp, path, re.IGNORECASE):
                    matched_file_pattern = True
                    break

            # Search in lines for code patterns or claim patterns
            for idx, line in enumerate(lines[:300]):  # check up to first 300 lines
                line_no = idx + 1
                stripped = line.strip()
                if not stripped:
                    continue

                # 1. Is this README / Doc file? Then it's a claim
                if category == "readme" or "doc" in path.lower():
                    for cp in rules["claim_patterns"]:
                        if re.search(cp, stripped, re.IGNORECASE):
                            evidence_list.append({
                                "file_path": path,
                                "line_number": line_no,
                                "snippet": stripped[:160],
                                "evidence_type": "claim",
                                "is_claim_only": True,
                                "github_url": f"{repo_url}/blob/main/{path}#L{line_no}" if repo_url else path,
                                "explanation": f"Claimed or mentioned in documentation ({path})."
                            })
                            break
                    continue

                # 2. Check code implementation patterns
                code_matched = False
                for cp in rules["code_patterns"]:
                    if re.search(cp, stripped, re.IGNORECASE):
                        code_matched = True
                        evidence_type = "test" if category == "test" else ("config" if category in ["config", "docker"] else "code")
                        evidence_list.append({
                            "file_path": path,
                            "line_number": line_no,
                            "snippet": stripped[:160],
                            "evidence_type": evidence_type,
                            "is_claim_only": False,
                            "github_url": f"{repo_url}/blob/main/{path}#L{line_no}" if repo_url else path,
                            "explanation": f"Implementation code detected in {path} at line {line_no}."
                        })
                        break

                # 3. If file pattern matched (e.g. Dockerfile or schema.sql), even single configuration line is strong
                if not code_matched and matched_file_pattern and idx < 5:
                    evidence_list.append({
                        "file_path": path,
                        "line_number": line_no,
                        "snippet": stripped[:160],
                        "evidence_type": "config" if "docker" in path.lower() else "code",
                        "is_claim_only": False,
                        "github_url": f"{repo_url}/blob/main/{path}#L{line_no}" if repo_url else path,
                        "explanation": f"Dedicated configuration/implementation file ({path})."
                    })
                    break

        return evidence_list

evidence_extractor = EvidenceExtractor()
