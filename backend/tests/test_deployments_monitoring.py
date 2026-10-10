from tests.conftest import register_and_login

GOOD = {"name": "My App", "repo_url": "https://github.com/octocat/Hello-World"}
TOKEN = "unit-test-deploy-token"


def make_project(client, headers):
    return client.post("/projects", json=GOOD, headers=headers).json()["id"]


# ---------- deployment report (called by CI/CD) ----------
def test_report_disabled_when_token_not_configured(client, auth_headers, monkeypatch):
    monkeypatch.delenv("DEPLOY_REPORT_TOKEN", raising=False)
    pid = make_project(client, auth_headers)
    res = client.post("/deployments/report", json={"project_id": pid, "status": "success"})
    assert res.status_code == 503


def test_report_rejects_missing_or_wrong_token(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DEPLOY_REPORT_TOKEN", TOKEN)
    pid = make_project(client, auth_headers)
    body = {"project_id": pid, "status": "success"}
    assert client.post("/deployments/report", json=body).status_code == 401
    assert client.post("/deployments/report", json=body, headers={"X-Deploy-Token": "nope"}).status_code == 401


def test_report_success_sets_live_url_and_status(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DEPLOY_REPORT_TOKEN", TOKEN)
    pid = make_project(client, auth_headers)
    body = {"project_id": pid, "status": "success", "message": "Deployed abc1234", "live_url": "http://203.0.113.10/"}
    res = client.post("/deployments/report", json=body, headers={"X-Deploy-Token": TOKEN})
    assert res.status_code == 201
    project = client.get(f"/projects/{pid}", headers=auth_headers).json()
    assert project["status"] == "deployed"
    assert project["live_url"] == "http://203.0.113.10"
    history = client.get(f"/projects/{pid}/deployments", headers=auth_headers).json()
    assert history[0]["status"] == "success"


def test_report_failed_marks_project_failed(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DEPLOY_REPORT_TOKEN", TOKEN)
    pid = make_project(client, auth_headers)
    body = {"project_id": pid, "status": "failed", "message": "Health check failed"}
    assert client.post("/deployments/report", json=body, headers={"X-Deploy-Token": TOKEN}).status_code == 201
    project = client.get(f"/projects/{pid}", headers=auth_headers).json()
    assert project["status"] == "deploy_failed"
    assert project["live_url"] is None


def test_report_rejects_dangerous_live_urls(client, auth_headers, monkeypatch):
    monkeypatch.setenv("DEPLOY_REPORT_TOKEN", TOKEN)
    pid = make_project(client, auth_headers)
    for bad in ["file:///etc/passwd", "http://user:pw@host", "http://host/path?x=1", "javascript:alert(1)"]:
        res = client.post(
            "/deployments/report",
            json={"project_id": pid, "status": "success", "live_url": bad},
            headers={"X-Deploy-Token": TOKEN},
        )
        assert res.status_code == 422, bad


def test_report_unknown_project(client, monkeypatch):
    monkeypatch.setenv("DEPLOY_REPORT_TOKEN", TOKEN)
    res = client.post(
        "/deployments/report", json={"project_id": 999, "status": "success"}, headers={"X-Deploy-Token": TOKEN}
    )
    assert res.status_code == 404


# ---------- monitoring ----------
def test_system_stats_require_login(client):
    assert client.get("/monitoring/system").status_code == 401


def test_system_stats_shape(client, auth_headers):
    res = client.get("/monitoring/system", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    for key in ["cpu_percent", "memory_percent", "memory_used_mb", "disk_percent", "app_uptime_seconds"]:
        assert key in body
    assert 0 <= body["memory_percent"] <= 100


def test_check_without_live_url_is_rejected(client, auth_headers):
    pid = make_project(client, auth_headers)
    assert client.post(f"/monitoring/projects/{pid}/check", headers=auth_headers).status_code == 400


def _deploy(client, headers, monkeypatch, pid):
    monkeypatch.setenv("DEPLOY_REPORT_TOKEN", TOKEN)
    client.post(
        "/deployments/report",
        json={"project_id": pid, "status": "success", "live_url": "http://203.0.113.10"},
        headers={"X-Deploy-Token": TOKEN},
    )


def test_health_checks_and_uptime_summary(client, auth_headers, monkeypatch):
    pid = make_project(client, auth_headers)
    _deploy(client, auth_headers, monkeypatch, pid)

    results = iter([(True, 200, 40, None), (True, 200, 60, None), (False, None, None, "Could not connect")])
    monkeypatch.setattr("app.routers.monitoring._fetch_health", lambda url: next(results))
    for _ in range(3):
        assert client.post(f"/monitoring/projects/{pid}/check", headers=auth_headers).status_code == 200

    summary = client.get(f"/monitoring/projects/{pid}/summary", headers=auth_headers).json()
    assert summary["total_checks"] == 3
    assert summary["successful_checks"] == 2
    assert summary["uptime_percent"] == 66.7
    assert summary["avg_response_ms"] == 50
    assert summary["last_ok"] is False
    assert len(client.get(f"/monitoring/projects/{pid}/checks", headers=auth_headers).json()) == 3


def test_summary_with_no_checks(client, auth_headers):
    pid = make_project(client, auth_headers)
    summary = client.get(f"/monitoring/projects/{pid}/summary", headers=auth_headers).json()
    assert summary["total_checks"] == 0 and summary["uptime_percent"] is None


def test_other_user_cannot_check_my_project(client, auth_headers, monkeypatch):
    pid = make_project(client, auth_headers)
    _deploy(client, auth_headers, monkeypatch, pid)
    other = register_and_login(client, username="mallory")
    assert client.post(f"/monitoring/projects/{pid}/check", headers=other).status_code == 404
    assert client.get(f"/monitoring/projects/{pid}/checks", headers=other).status_code == 404
