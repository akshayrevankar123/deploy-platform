"""Basic monitoring: server resources + uptime checks of deployed projects.

Metrics (CPU, memory, disk) describe the machine THIS backend runs on.
Uptime checks call <live_url>/health on a deployed project and store the result.
"""
import time
import urllib.error
import urllib.request

import psutil
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import HealthCheck, User
from ..schemas import HealthCheckOut, HealthSummary, SystemStats
from .projects import get_owned_project

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

_STARTED = time.time()


def _fetch_health(base_url: str) -> tuple[bool, int | None, int | None, str | None]:
    """Calls <base_url>/health. Returns (ok, status_code, response_ms, error).

    SECURITY NOTE: live_url can only be set by the CI/CD pipeline (it needs the secret
    deploy token) and is validated to be plain http(s)://host[:port]. Users cannot
    point this server at arbitrary addresses.
    """
    url = base_url.rstrip("/") + "/health"
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
            ms = int((time.perf_counter() - started) * 1000)
            return resp.status == 200, resp.status, ms, None
    except urllib.error.HTTPError as err:
        ms = int((time.perf_counter() - started) * 1000)
        return False, err.code, ms, f"HTTP {err.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, None, None, "Could not connect, or timed out after 5 seconds"


@router.get("/system", response_model=SystemStats)
def system_stats(user: User = Depends(get_current_user)):
    memory = psutil.virtual_memory()
    return SystemStats(
        cpu_percent=psutil.cpu_percent(interval=0.2),
        memory_percent=memory.percent,
        memory_used_mb=int(memory.used / 1024 / 1024),
        disk_percent=psutil.disk_usage("/").percent,
        app_uptime_seconds=int(time.time() - _STARTED),
    )


@router.post("/projects/{project_id}/check", response_model=HealthCheckOut)
def run_check(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = get_owned_project(project_id, db, user)
    if not project.live_url:
        raise HTTPException(status_code=400, detail="This project has no live URL yet. Deploy it first.")
    ok, status_code, ms, error = _fetch_health(project.live_url)
    check = HealthCheck(
        project_id=project.id, ok=ok, status_code=status_code, response_ms=ms, error=error
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


@router.get("/projects/{project_id}/checks", response_model=list[HealthCheckOut])
def list_checks(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = get_owned_project(project_id, db, user)
    rows = db.scalars(
        select(HealthCheck)
        .where(HealthCheck.project_id == project.id)
        .order_by(HealthCheck.id.desc())
        .limit(50)
    )
    return list(rows)


@router.get("/projects/{project_id}/summary", response_model=HealthSummary)
def summary(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = get_owned_project(project_id, db, user)
    rows = list(
        db.scalars(
            select(HealthCheck)
            .where(HealthCheck.project_id == project.id)
            .order_by(HealthCheck.id.desc())
            .limit(100)
        )
    )
    if not rows:
        return HealthSummary(
            total_checks=0, successful_checks=0, uptime_percent=None, avg_response_ms=None, last_ok=None
        )
    ok_rows = [r for r in rows if r.ok]
    times = [r.response_ms for r in ok_rows if r.response_ms is not None]
    return HealthSummary(
        total_checks=len(rows),
        successful_checks=len(ok_rows),
        uptime_percent=round(100 * len(ok_rows) / len(rows), 1),
        avg_response_ms=int(sum(times) / len(times)) if times else None,
        last_ok=rows[0].ok,
    )
