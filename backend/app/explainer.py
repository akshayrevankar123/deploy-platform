"""Rule-based error explainer (no AI API, no cost).

Two jobs:
1. sanitize(): remove secrets and personal data from a log.
   This MUST run before a log is stored or ever sent to any external AI service.
2. explain(): match the log against common error patterns and return
   a plain-language explanation plus things to check.
"""
import re

MAX_LOG_CHARS = 10_000

# Order matters: more specific patterns first.
_REDACTIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
     "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(\b[a-zA-Z][a-zA-Z0-9+.-]*://[^:\s/@]+):[^@\s]+@"), r"\1:[REDACTED]@"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer [REDACTED]"),
    # Matches whole names like DB_PASSWORD, SECRET_KEY, access_token, api-key
    (re.compile(
        r"(?i)([A-Za-z0-9_.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)[A-Za-z0-9_.-]*)"
        r"(\s*[=:]\s*)\S+"),
     r"\1\2[REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
]


def sanitize(log: str) -> str:
    text = log[:MAX_LOG_CHARS]
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


_RULES: list[dict] = [
    {
        "pattern": r"ModuleNotFoundError|No module named|ImportError",
        "title": "A Python package is missing",
        "explanation": "Your code imports a library that is not installed in this environment.",
        "checks": [
            "Is the package listed in requirements.txt?",
            "Did the Docker build run 'pip install -r requirements.txt'?",
            "Is the package name spelled correctly (pip name can differ from import name)?",
        ],
    },
    {
        "pattern": r"Address already in use|port is already allocated|EADDRINUSE",
        "title": "The port is already taken",
        "explanation": "Another program or container is already using the port your app wants.",
        "checks": [
            "Run 'docker ps' and stop the old container.",
            "Change the host port, e.g. -p 8001:8000.",
        ],
    },
    {
        "pattern": r"Connection refused|ECONNREFUSED|could not connect to server",
        "title": "Nothing is listening at that address",
        "explanation": "Your app tried to reach a service (database, API) that is not running or not reachable.",
        "checks": [
            "Is the other service (e.g. PostgreSQL) running?",
            "Inside Docker, use the service name (like 'db'), not 'localhost'.",
            "Is the hostname and port in your environment variables correct?",
        ],
    },
    {
        "pattern": r"Permission denied \(publickey\)|Permission denied.*ssh",
        "title": "SSH key was rejected",
        "explanation": "The server did not accept your SSH key.",
        "checks": [
            "Are you using the key pair chosen when the EC2 instance was created?",
            "Is the username right? (ec2-user for Amazon Linux, ubuntu for Ubuntu)",
            "Is the key file in the correct format and not shared with other users?",
        ],
    },
    {
        "pattern": r"permission denied.*docker\.sock|Cannot connect to the Docker daemon|docker daemon",
        "title": "Docker is not running or not allowed",
        "explanation": "The Docker command could not talk to the Docker engine.",
        "checks": [
            "On Windows, open Docker Desktop and wait for 'Engine running'.",
            "On Linux, check 'sudo systemctl status docker' and that your user is in the docker group.",
        ],
    },
    {
        "pattern": r"No space left on device",
        "title": "The disk is full",
        "explanation": "The machine has no free storage left.",
        "checks": [
            "Run 'df -h' to see disk usage.",
            "Clean old Docker data with 'docker system prune' (read the warning first).",
        ],
    },
    {
        "pattern": r"Killed|OOMKilled|exit code 137|Out of memory",
        "title": "The app ran out of memory",
        "explanation": "The system stopped your program because it used more memory than available.",
        "checks": [
            "Check memory with 'free -m' or 'docker stats'.",
            "Use a smaller workload or a larger instance (this costs more).",
        ],
    },
    {
        "pattern": r"\b401\b|Unauthorized|Invalid or expired token",
        "title": "Not authenticated",
        "explanation": "The request had no valid login or token.",
        "checks": ["Log in again.", "Is the Authorization header 'Bearer <token>'?"],
    },
    {
        "pattern": r"\b403\b|Forbidden",
        "title": "Access forbidden",
        "explanation": "You are logged in but not allowed to do this.",
        "checks": ["Do you own this resource?", "Check permissions or security group rules."],
    },
    {
        "pattern": r"\b404\b|Not Found",
        "title": "Resource not found",
        "explanation": "The URL or item you asked for does not exist.",
        "checks": ["Check the URL for typos.", "Does the item exist and belong to you?"],
    },
    {
        "pattern": r"timed? ?out|TimeoutError|ETIMEDOUT",
        "title": "The request timed out",
        "explanation": "Something took too long to answer.",
        "checks": [
            "Is the server running?",
            "On AWS, does the security group allow the port you are calling?",
        ],
    },
    {
        "pattern": r"SyntaxError|IndentationError",
        "title": "Python syntax error",
        "explanation": "Python could not read your code because of a typo or wrong indentation.",
        "checks": ["Look at the line number in the log.", "Check brackets, colons and indentation."],
    },
    {
        "pattern": r"KeyError: '?[A-Z_]{3,}'?|environment variable|not set",
        "title": "A setting (environment variable) is missing",
        "explanation": "Your app expects a configuration value that was not provided.",
        "checks": [
            "Compare your .env file with .env.example.",
            "Was the variable passed to the container (-e or env_file)?",
        ],
    },
    {
        "pattern": r"OperationalError|password authentication failed|database .* does not exist",
        "title": "Database connection problem",
        "explanation": "The app could not log in to, or find, the database.",
        "checks": [
            "Check DATABASE_URL (user, host, port, database name).",
            "Is the database container healthy?",
        ],
    },
]

DISCLAIMER = (
    "These are automated suggestions based on common patterns. They can be wrong or incomplete. "
    "Always verify before changing production systems."
)


def explain(sanitized_log: str) -> list[dict]:
    matches = []
    for rule in _RULES:
        if re.search(rule["pattern"], sanitized_log, flags=re.IGNORECASE):
            matches.append(
                {"title": rule["title"], "explanation": rule["explanation"], "checks": rule["checks"]}
            )
    if not matches:
        matches.append({
            "title": "No known pattern matched",
            "explanation": "This error is not in our built-in list yet.",
            "checks": [
                "Read the LAST lines of the log first; the real cause is usually near the end.",
                "Search the exact error message (without secrets) online.",
                "Check what changed right before the error started.",
            ],
        })
    return matches
