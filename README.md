# Beginner-Friendly Cloud Deployment Platform

Register a GitHub repo, run a safe pre-flight scan, request a deployment, monitor uptime, and get
plain-language explanations of error logs. Backend: FastAPI. Frontend: React + Vite.
CI/CD: GitHub Actions + Docker Hub + AWS EC2.

## Folder map

```
backend/             FastAPI app (auth, projects, scan, deployments, monitoring, explainer) + 61 tests
frontend/            React + Vite dashboard (projects, monitoring, error explanation)
deploy/              Scripts that run on the EC2 server (setup, deploy with rollback, report)
sample-app/          A tiny project that passes the scan, plus a CI template for student repos
.github/workflows/   ci.yml (tests, Gitleaks, Trivy), deploy.yml (build, push, deploy), uptime.yml (alert)
docs/                TEST_PLAN.md and REPORT_KIT.md (report, diagrams, viva, demo script)
Dockerfile           Multi-stage build: React app + Python backend in one image
docker-compose.yml   Backend + PostgreSQL on your own machine
RUNBOOK.md           Step-by-step: laptop > Docker > GitHub > AWS > automatic deploy > shut down
```

## Quick start (Windows PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
$env:SECRET_KEY = "any-long-random-text-for-local-use"
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs. In a second window: `cd frontend; npm install; npm run dev`, then open http://localhost:5173.

For everything else (Docker, GitHub, AWS, CI/CD, shutting down), follow **RUNBOOK.md**.

## Secrets

Never commit `.env` files or `.pem` keys. Copy `.env.example` to `.env` and fill in your own values.
GitHub Actions secrets are listed in `.github/workflows/deploy.yml` and `RUNBOOK.md`.

## What was tested

- Backend: 61 automated tests pass (auth, authorization, validation, scan rules, deployment reporting, monitoring, redaction).
- Frontend: production build succeeds; the built dashboard is served by the backend alongside the API.
- Not yet run: the Dockerfile build, docker-compose, and the GitHub Actions workflows, because they need Docker, GitHub and AWS. Their first real run happens on your side; use RUNBOOK.md and expect to fix small things.

## Honest limits

- The scan is a quick pre-flight check using the GitHub API. It never downloads or runs user code, and a clean result does not mean a project is secure.
- "Deploy project" records a request. The real pipeline deploys this application; deploying other users' repositories safely needs sandboxing this MVP does not have.
- The live site uses plain HTTP, one server, and SQLite. See RUNBOOK.md "Known limits".
