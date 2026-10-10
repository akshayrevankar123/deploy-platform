import urllib.error

import pytest

from app import scanner

URL = "https://github.com/someone/project"
GOOD_FILES = [".gitignore", "Dockerfile", "requirements.txt", "main.py", "tests"]


def use_files(monkeypatch, names):
    monkeypatch.setattr(scanner, "_list_root_files", lambda owner, repo: names)


def titles(findings):
    return [f["title"] for f in findings]


def test_clean_repo_passes(monkeypatch):
    use_files(monkeypatch, GOOD_FILES)
    status, findings = scanner.scan_repo(URL)
    assert status == "passed" and findings == []


def test_missing_dockerfile_is_a_warning(monkeypatch):
    use_files(monkeypatch, [n for n in GOOD_FILES if n != "Dockerfile"])
    status, findings = scanner.scan_repo(URL)
    assert status == "warnings"
    assert "No Dockerfile" in titles(findings)


def test_committed_env_file_is_critical_and_fails(monkeypatch):
    use_files(monkeypatch, GOOD_FILES + [".env"])
    status, findings = scanner.scan_repo(URL)
    assert status == "failed"
    assert findings[0]["severity"] == "CRITICAL"


def test_env_example_is_not_flagged(monkeypatch):
    use_files(monkeypatch, GOOD_FILES + [".env.example"])
    status, _ = scanner.scan_repo(URL)
    assert status == "passed"


def test_missing_tests_folder_is_info_only(monkeypatch):
    use_files(monkeypatch, [n for n in GOOD_FILES if n != "tests"])
    status, findings = scanner.scan_repo(URL)
    assert status == "passed"
    assert findings[0]["severity"] == "INFO"


def _raise(exc):
    def fake(owner, repo):
        raise exc
    return fake


def test_repo_not_found_gives_friendly_error(monkeypatch):
    err = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    monkeypatch.setattr(scanner, "_list_root_files", _raise(err))
    status, findings = scanner.scan_repo(URL)
    assert status == "error"
    assert "not found" in findings[0]["detail"].lower()


def test_rate_limit_gives_friendly_error(monkeypatch):
    err = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
    monkeypatch.setattr(scanner, "_list_root_files", _raise(err))
    status, findings = scanner.scan_repo(URL)
    assert status == "error"
    assert "rate limit" in findings[0]["detail"].lower()


def test_network_failure_gives_friendly_error(monkeypatch):
    monkeypatch.setattr(scanner, "_list_root_files", _raise(urllib.error.URLError("down")))
    status, findings = scanner.scan_repo(URL)
    assert status == "error"
    assert findings[0]["title"] == "Could not reach GitHub"


@pytest.mark.parametrize(
    "bad",
    [
        "http://github.com/a/b",
        "https://gitlab.com/a/b",
        "https://github.com/a",
        "https://github.com/a/b/c",
        "https://github.com/../b",
        "https://github.com/a/b?x=1",
        "git@github.com:a/b.git",
        "",
    ],
)
def test_validate_repo_url_rejects_bad_urls(bad):
    with pytest.raises(ValueError):
        scanner.validate_repo_url(bad)
