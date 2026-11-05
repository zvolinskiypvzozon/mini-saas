import pytest
from sqlalchemy import text

from app.db import engine

PASSWORD = "StrongPass123"


def register(client, email="owner@demo.ru", org="Demo LLC", password=PASSWORD):
    return client.post(
        "/api/auth/register",
        json={"organization_name": org, "email": email, "password": password},
    )


def login(client, email="owner@demo.ru", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_register_creates_owner(client):
    response = register(client, email="Owner@Demo.ru")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "owner@demo.ru"
    assert body["role"] == "owner"
    assert "password_hash" not in body


def test_register_duplicate_email_case_insensitive(client):
    register(client)
    response = register(client, email="OWNER@demo.ru", org="Other")
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"organization_name": "Demo", "email": "not-an-email", "password": PASSWORD},
        {"organization_name": "Demo", "email": "a@demo.ru", "password": "123"},
        {"organization_name": "X", "email": "a@demo.ru", "password": PASSWORD},
    ],
)
def test_register_validation(client, payload):
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_login_wrong_password(client):
    register(client)
    assert login(client, password="wrong-password").status_code == 401


def test_login_unknown_email_gives_same_error(client):
    register(client)
    wrong_password = login(client, password="wrong-password")
    unknown_email = login(client, email="nobody@demo.ru")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_token(client):
    assert client.get("/api/me").status_code == 401


def test_me_with_token(client):
    register(client)
    token = login(client).json()["access_token"]
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "owner@demo.ru"


def test_me_rejects_tampered_token(client):
    register(client)
    token = login(client).json()["access_token"]
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}x"})
    assert response.status_code == 401


def test_password_is_hashed_in_db(client):
    register(client)
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users")).scalar_one()
    assert stored.startswith("$2b$")
    assert PASSWORD not in stored
