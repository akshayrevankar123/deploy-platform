# Build context is the REPO ROOT:  docker build -t deploy-platform .

# ---------- Stage 1: build the React frontend ----------
FROM node:22-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: the Python backend (final image) ----------
# Small official Python image (slim = fewer packages = smaller and safer).
FROM python:3.13-slim

# Don't write .pyc files; print logs immediately instead of buffering them.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first so Docker can cache the install step.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# The built dashboard. The backend serves it at "/".
COPY --from=frontend /web/dist ./static

# Run as a normal user, not root. If the app is attacked, the damage is smaller.
# /data holds the SQLite file. A Docker volume mounted here keeps data across redeploys.
RUN useradd --create-home appuser && mkdir /data && chown -R appuser /app /data
USER appuser

EXPOSE 8000

# Docker marks the container "unhealthy" if /health stops answering.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
