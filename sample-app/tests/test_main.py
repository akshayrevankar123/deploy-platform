from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_home():
    assert client.get("/").status_code == 200


def test_add():
    assert client.get("/add", params={"a": 2, "b": 3}).json() == {"result": 5}


def test_add_rejects_text():
    assert client.get("/add", params={"a": "x", "b": 3}).status_code == 422
