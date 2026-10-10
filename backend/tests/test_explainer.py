from app.explainer import explain, sanitize
from app.scanner import validate_repo_url

# Fake secrets are built from pieces so secret scanners don't flag this test file.
FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"
FAKE_GH_TOKEN = "ghp_" + "a" * 36


def test_sanitize_removes_aws_key():
    out = sanitize(f"using key {FAKE_AWS_KEY} failed")
    assert FAKE_AWS_KEY not in out
    assert "[REDACTED_AWS_KEY]" in out


def test_sanitize_removes_github_token():
    assert FAKE_GH_TOKEN not in sanitize(f"token is {FAKE_GH_TOKEN}")


def test_sanitize_removes_password_assignments():
    out = sanitize("DB_PASSWORD=hunter2 and api_key: abc123")
    assert "hunter2" not in out and "abc123" not in out


def test_sanitize_removes_password_in_connection_url():
    out = sanitize("postgresql://admin:SuperSecret@db:5432/app")
    assert "SuperSecret" not in out
    assert "admin" in out


def test_sanitize_removes_email_and_bearer_token():
    out = sanitize("user a.b@example.com sent Authorization: Bearer abc.def.ghi")
    assert "a.b@example.com" not in out
    assert "abc.def.ghi" not in out


def test_sanitize_truncates_huge_logs():
    assert len(sanitize("x" * 50_000)) <= 10_000


def test_explain_module_not_found():
    titles = [r["title"] for r in explain("ModuleNotFoundError: No module named 'fastapi'")]
    assert "A Python package is missing" in titles


def test_explain_unknown_error_has_fallback():
    results = explain("zzzz something totally unknown qqqq")
    assert results[0]["title"] == "No known pattern matched"


def test_explain_endpoint_requires_login(client):
    assert client.post("/explain", json={"log": "error"}).status_code == 401


def test_explain_endpoint_sanitizes_and_explains(client, auth_headers):
    log = f"Connection refused while using password=hunter2 key {FAKE_AWS_KEY}"
    res = client.post("/explain", json={"log": log}, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "hunter2" not in body["sanitized_log"]
    assert FAKE_AWS_KEY not in body["sanitized_log"]
    assert body["results"][0]["title"] == "Nothing is listening at that address"
    assert "wrong" in body["disclaimer"]


def test_explain_endpoint_rejects_empty_log(client, auth_headers):
    assert client.post("/explain", json={"log": ""}, headers=auth_headers).status_code == 422


def test_validate_repo_url_accepts_good_urls():
    assert validate_repo_url("https://github.com/octocat/Hello-World") == ("octocat", "Hello-World")
    assert validate_repo_url("https://github.com/octocat/Hello-World.git") == ("octocat", "Hello-World")
