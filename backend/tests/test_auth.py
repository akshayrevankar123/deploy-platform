from tests.conftest import register_and_login


def test_register_success(client):
    res = client.post("/auth/register", json={"username": "bob_1", "password": "StrongPass123"})
    assert res.status_code == 201
    assert res.json()["username"] == "bob_1"
    assert "password" not in res.json()


def test_register_duplicate_username(client):
    body = {"username": "bob", "password": "StrongPass123"}
    client.post("/auth/register", json=body)
    assert client.post("/auth/register", json=body).status_code == 409


def test_register_weak_password_rejected(client):
    res = client.post("/auth/register", json={"username": "bob", "password": "short"})
    assert res.status_code == 422


def test_register_invalid_username_rejected(client):
    res = client.post("/auth/register", json={"username": "bad name!", "password": "StrongPass123"})
    assert res.status_code == 422


def test_login_success_returns_token(client):
    client.post("/auth/register", json={"username": "bob", "password": "StrongPass123"})
    res = client.post("/auth/login", json={"username": "bob", "password": "StrongPass123"})
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "bob", "password": "StrongPass123"})
    res = client.post("/auth/login", json={"username": "bob", "password": "WrongPass999"})
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = client.post("/auth/login", json={"username": "ghost", "password": "StrongPass123"})
    assert res.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_me_with_valid_token(client, auth_headers):
    res = client.get("/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "alice"


def test_password_is_not_stored_in_plain_text(client):
    from app.database import SessionLocal
    from app.models import User

    client.post("/auth/register", json={"username": "bob", "password": "StrongPass123"})
    with SessionLocal() as db:
        user = db.query(User).filter_by(username="bob").one()
        assert user.password_hash != "StrongPass123"
        assert user.password_hash.startswith("$2")  # bcrypt marker
