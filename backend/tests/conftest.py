import os

# These must be set BEFORE the app is imported, so tests use a throwaway database.
os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["SECRET_KEY"] = "test-only-key-not-used-anywhere-else"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def register_and_login(client, username="alice", password="StrongPass123"):
    client.post("/auth/register", json={"username": username, "password": password})
    res = client.post("/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def auth_headers(client):
    return register_and_login(client)
