"""Endpoint the CI/CD pipeline calls to report a deployment result.

SECURITY: this endpoint is NOT protected by a user login (a pipeline has no user).
It is protected by a shared secret instead (DEPLOY_REPORT_TOKEN), sent in the
X-Deploy-Token header. If the token is not configured, the endpoint is disabled.
"""
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Deployment, Project
from ..schemas import DeploymentOut, DeploymentReport

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("/report", response_model=DeploymentOut, status_code=201)
def report_deployment(
    data: DeploymentReport,
    x_deploy_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    expected = os.getenv("DEPLOY_REPORT_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="Deployment reporting is not configured")
    # compare_digest avoids leaking the token through response-time differences.
    if not x_deploy_token or not hmac.compare_digest(x_deploy_token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid deploy token")

    project = db.get(Project, data.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    deployment = Deployment(project_id=project.id, status=data.status, message=data.message)
    db.add(deployment)
    if data.status == "success":
        project.status = "deployed"
        if data.live_url:
            project.live_url = data.live_url
    else:
        project.status = "deploy_failed"
    db.commit()
    db.refresh(deployment)
    return deployment
