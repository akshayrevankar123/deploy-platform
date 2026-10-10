from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Deployment, Project, Scan, User
from ..scanner import scan_repo
from ..schemas import DeploymentOut, ProjectCreate, ProjectOut, ScanOut

router = APIRouter(prefix="/projects", tags=["projects"])


def get_owned_project(project_id: int, db: Session, user: User) -> Project:
    project = db.get(Project, project_id)
    # 404 (not 403) so we don't reveal that someone else's project exists.
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    data: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = Project(owner_id=user.id, name=data.name.strip(), repo_url=data.repo_url)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(Project).where(Project.owner_id == user.id).order_by(Project.id.desc())
    )
    return list(rows)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return get_owned_project(project_id, db, user)


@router.post("/{project_id}/scan", response_model=ScanOut)
def run_scan(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = get_owned_project(project_id, db, user)
    status, findings = scan_repo(project.repo_url)
    scan = Scan(project_id=project.id, status=status, findings=findings)
    db.add(scan)
    project.status = f"scan_{status}"
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/{project_id}/scans", response_model=list[ScanOut])
def list_scans(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = get_owned_project(project_id, db, user)
    rows = db.scalars(select(Scan).where(Scan.project_id == project.id).order_by(Scan.id.desc()))
    return list(rows)


@router.post("/{project_id}/deploy", response_model=DeploymentOut, status_code=202)
def request_deploy(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """For now this only RECORDS a deployment request.
    In Phase 10 the GitHub Actions pipeline will do the real work and report back."""
    project = get_owned_project(project_id, db, user)

    last_scan = db.scalar(
        select(Scan).where(Scan.project_id == project.id).order_by(Scan.id.desc())
    )
    if last_scan is None:
        raise HTTPException(status_code=400, detail="Run a scan before deploying")
    if last_scan.status in {"failed", "error"}:
        raise HTTPException(
            status_code=400, detail="Latest scan did not pass. Fix the problems and scan again."
        )

    deployment = Deployment(
        project_id=project.id,
        status="queued",
        message="Deployment requested. The CI/CD pipeline will pick this up (added in Phase 10).",
    )
    db.add(deployment)
    project.status = "deploy_requested"
    db.commit()
    db.refresh(deployment)
    return deployment


@router.get("/{project_id}/deployments", response_model=list[DeploymentOut])
def list_deployments(
    project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project = get_owned_project(project_id, db, user)
    rows = db.scalars(
        select(Deployment).where(Deployment.project_id == project.id).order_by(Deployment.id.desc())
    )
    return list(rows)
