"""Safe manual repository scan.

SAFETY DESIGN (important for your viva):
- We NEVER clone, download or run the user's code.
- We only ask the GitHub API which files exist in the repo root.
- The URL must match a strict pattern, and the request host is hard-coded to
  api.github.com, so a user cannot make our server call some other address (SSRF).
- This is a quick "pre-flight check", NOT a full security audit. The real checks
  (tests, Gitleaks, Trivy) run later inside GitHub Actions.
"""
import json
import os
import re
import urllib.error
import urllib.request

REPO_PATTERN = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]{1,39})/([A-Za-z0-9_.-]{1,100}?)(?:\.git)?/?$"
)


def validate_repo_url(url: str) -> tuple[str, str]:
    """Returns (owner, repo) or raises ValueError."""
    match = REPO_PATTERN.match(url.strip())
    if not match:
        raise ValueError("Repository URL must look like https://github.com/owner/repo")
    owner, repo = match.group(1), match.group(2)
    if owner in {".", ".."} or repo in {".", ".."}:
        raise ValueError("Invalid repository URL")
    return owner, repo


def _list_root_files(owner: str, repo: str) -> list[str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "deploy-platform-student-project",
    }
    token = os.getenv("GITHUB_TOKEN")  # optional, raises GitHub rate limits
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/contents/", headers=headers
    )
    with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310 (fixed https host)
        items = json.loads(resp.read().decode("utf-8"))
    return [item["name"] for item in items]


def scan_repo(repo_url: str) -> tuple[str, list[dict]]:
    """Returns (status, findings). status: passed / warnings / failed / error."""
    owner, repo = validate_repo_url(repo_url)

    try:
        names = _list_root_files(owner, repo)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            msg = "Repository not found, or it is private. Only public repos can be scanned."
        elif err.code == 403:
            msg = "GitHub rate limit reached. Try again in a few minutes."
        else:
            msg = f"GitHub returned an error (HTTP {err.code})."
        return "error", [{"severity": "ERROR", "title": "Could not read repository", "detail": msg}]
    except (urllib.error.URLError, TimeoutError, ValueError):
        return "error", [
            {"severity": "ERROR", "title": "Could not reach GitHub", "detail": "Network problem. Try again."}
        ]

    lower = {n.lower() for n in names}
    findings: list[dict] = []

    committed_env = sorted(
        n for n in names
        if n.lower().startswith(".env") and n.lower() not in {".env.example", ".env.sample", ".env.template"}
    )
    if committed_env:
        findings.append({
            "severity": "CRITICAL",
            "title": "Environment file committed",
            "detail": f"Found {', '.join(committed_env)} in the repo. These usually contain secrets. "
                      "Remove it from Git history and rotate any keys inside.",
        })
    if "dockerfile" not in lower:
        findings.append({
            "severity": "WARNING",
            "title": "No Dockerfile",
            "detail": "The platform deploys with Docker. Add a Dockerfile to the repo root.",
        })
    if "requirements.txt" not in lower:
        findings.append({
            "severity": "WARNING",
            "title": "No requirements.txt",
            "detail": "Python dependencies are not listed, so the build may fail.",
        })
    if ".gitignore" not in lower:
        findings.append({
            "severity": "WARNING",
            "title": "No .gitignore",
            "detail": "Without one, secrets and junk files are easier to commit by accident.",
        })
    if not ({"tests", "test"} & lower):
        findings.append({
            "severity": "INFO",
            "title": "No tests folder found",
            "detail": "Automated tests make the pipeline much more useful.",
        })

    if any(f["severity"] == "CRITICAL" for f in findings):
        status = "failed"
    elif any(f["severity"] == "WARNING" for f in findings):
        status = "warnings"
    else:
        status = "passed"
    return status, findings
