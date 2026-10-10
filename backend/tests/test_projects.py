from tests.conftest import register_and_login

GOOD = {"name": "My App", "repo_url": "https://github.com/octocat/Hello-World"}


def test_projects_require_login(client):
    assert client.get("/projects").status_code == 401
    assert client.post("/projects", json=GOOD).status_code == 401


def test_create_and_list_project(client, auth_headers):
    res = client.post("/projects", json=GOOD, headers=auth_headers)
    assert res.status_code == 201
    assert res.json()["status"] == "registered"
    listed = client.get("/projects", headers=auth_headers).json()
    assert len(listed) == 1 and listed[0]["name"] == "My App"


def test_invalid_repo_urls_rejected(client, auth_headers):
    bad_urls = [
        "http://github.com/octocat/Hello-World",          # not https
        "https://evil.com/octocat/Hello-World",           # wrong host
        "https://github.com/octocat",                     # no repo
        "https://github.com/octocat/repo; rm -rf /",      # injection attempt
        "file:///etc/passwd",
        "https://github.com.evil.com/a/b",
    ]
    for url in bad_urls:
        res = client.post("/projects", json={"name": "x", "repo_url": url}, headers=auth_headers)
        assert res.status_code == 422, url


def test_empty_name_rejected(client, auth_headers):
    res = client.post("/projects", json={"name": "", "repo_url": GOOD["repo_url"]}, headers=auth_headers)
    assert res.status_code == 422


def test_users_cannot_see_each_others_projects(client, auth_headers):
    created = client.post("/projects", json=GOOD, headers=auth_headers).json()
    other = register_and_login(client, username="mallory")
    assert client.get("/projects", headers=other).json() == []
    assert client.get(f"/projects/{created['id']}", headers=other).status_code == 404
    assert client.post(f"/projects/{created['id']}/scan", headers=other).status_code == 404
    assert client.post(f"/projects/{created['id']}/deploy", headers=other).status_code == 404


def test_scan_stores_result(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.routers.projects.scan_repo",
        lambda url: ("warnings", [{"severity": "WARNING", "title": "No Dockerfile", "detail": "x"}]),
    )
    pid = client.post("/projects", json=GOOD, headers=auth_headers).json()["id"]
    res = client.post(f"/projects/{pid}/scan", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "warnings"
    assert len(client.get(f"/projects/{pid}/scans", headers=auth_headers).json()) == 1


def test_deploy_blocked_without_scan(client, auth_headers):
    pid = client.post("/projects", json=GOOD, headers=auth_headers).json()["id"]
    assert client.post(f"/projects/{pid}/deploy", headers=auth_headers).status_code == 400


def test_deploy_blocked_when_scan_failed(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.routers.projects.scan_repo",
        lambda url: ("failed", [{"severity": "CRITICAL", "title": ".env committed", "detail": "x"}]),
    )
    pid = client.post("/projects", json=GOOD, headers=auth_headers).json()["id"]
    client.post(f"/projects/{pid}/scan", headers=auth_headers)
    assert client.post(f"/projects/{pid}/deploy", headers=auth_headers).status_code == 400


def test_deploy_allowed_after_passing_scan(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.routers.projects.scan_repo", lambda url: ("passed", []))
    pid = client.post("/projects", json=GOOD, headers=auth_headers).json()["id"]
    client.post(f"/projects/{pid}/scan", headers=auth_headers)
    res = client.post(f"/projects/{pid}/deploy", headers=auth_headers)
    assert res.status_code == 202
    assert res.json()["status"] == "queued"
    history = client.get(f"/projects/{pid}/deployments", headers=auth_headers).json()
    assert len(history) == 1
