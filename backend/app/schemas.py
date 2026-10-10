"""Request and response shapes. FastAPI uses these to validate input automatically."""
import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .scanner import validate_repo_url


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,30}$")
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    repo_url: str = Field(max_length=200)

    @field_validator("repo_url")
    @classmethod
    def check_repo_url(cls, value: str) -> str:
        value = value.strip()
        validate_repo_url(value)  # raises ValueError -> becomes a 422 response
        return value


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    repo_url: str
    status: str
    live_url: str | None
    created_at: dt.datetime


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    findings: list
    created_at: dt.datetime


class DeploymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    message: str
    created_at: dt.datetime


class ExplainIn(BaseModel):
    log: str = Field(min_length=1, max_length=10_000)


class ExplainOut(BaseModel):
    sanitized_log: str
    results: list
    disclaimer: str


# ---------- Deployment report (sent by the CI/CD pipeline) ----------
import re  # noqa: E402
from typing import Literal  # noqa: E402

_LIVE_URL = re.compile(r"^https?://[A-Za-z0-9.-]{1,100}(:\d{1,5})?/?$")


class DeploymentReport(BaseModel):
    project_id: int
    status: Literal["success", "failed"]
    message: str = Field(default="", max_length=300)
    live_url: str | None = Field(default=None, max_length=200)

    @field_validator("live_url")
    @classmethod
    def check_live_url(cls, value):
        if value is None:
            return None
        value = value.strip()
        # Only scheme://host[:port]. No paths, no usernames, no query strings.
        if not _LIVE_URL.match(value):
            raise ValueError("live_url must look like http://host or http://host:port")
        return value.rstrip("/")


# ---------- Monitoring ----------
class HealthCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ok: bool
    status_code: int | None
    response_ms: int | None
    error: str | None
    created_at: dt.datetime


class HealthSummary(BaseModel):
    total_checks: int
    successful_checks: int
    uptime_percent: float | None
    avg_response_ms: int | None
    last_ok: bool | None


class SystemStats(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: int
    disk_percent: float
    app_uptime_seconds: int
