import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (makes sure tables are registered)
from .database import Base, engine
from .routers import auth, deployments, explain, monitoring, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # creates tables if they don't exist
    yield


app = FastAPI(title="Beginner-Friendly Deployment Platform", version="0.1.0", lifespan=lifespan)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(explain.router)
app.include_router(deployments.router)
app.include_router(monitoring.router)


@app.get("/health", tags=["monitoring"])
def health():
    """Used by Docker, CI/CD and monitoring to check that the app is alive."""
    return {"status": "ok"}


# In the Docker image the built React app is copied to /app/static and served here,
# so ONE container (one URL) gives you both the API and the dashboard.
# Locally this folder does not exist, so nothing is mounted.
# This must stay LAST: API routes above are matched first.
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parent.parent / "static"))
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
