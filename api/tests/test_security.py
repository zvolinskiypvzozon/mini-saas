from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import PASSWORD, register_owner

CSRF = {"X-Requested-With": "fetch"}


def login(client, email="owner@a.ru", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def set_cookie_headers(response):
    return [value.lower() for value in response.headers.get_list("set-cookie")]


def test_login_sets_httponly_strict_cookies(client):
    register_owner(client, "owner@a.ru", "Org A")
    cookies = set_cookie_headers(login(client))
    access = next(c for c in cookies if c.startswith("access_token="))
    refresh = next(c for c in cookies if c.startswith("refresh_token="))
    for cookie in (access, refresh):
        assert "httponly" in cookie
        assert "samesite=strict" in cookie
    assert "path=/api;" in access or access.endswith("path=/api")
    assert "path=/api/auth" in refresh


def test_cookie_auth_and_csrf_header(client):
    register_owner(client, "owner@a.ru", "Org A")
    login(client)

    assert client.get("/api/me").json()["email"] == "owner@a.ru"

    no_header = client.post("/api/projects", json={"name": "Website"})
    assert no_header.status_code == 403
    with_header = client.post("/api/projects", json={"name": "Website"}, headers=CSRF)
    assert with_header.status_code == 201


def test_invalid_bearer_is_not_rescued_by_cookie(client):
    register_owner(client, "owner@a.ru", "Org A")
    login(client)
    response = client.get("/api/me", headers={"Authorization": "Bearer broken"})
    assert response.status_code == 401


def test_refresh_rotates_and_detects_reuse(client):
    register_owner(client, "owner@a.ru", "Org A")
    login(client)
    first = client.cookies.get("refresh_token")

    assert client.post("/api/auth/refresh").status_code == 403

    rotated = client.post("/api/auth/refresh", headers=CSRF)
    assert rotated.status_code == 200
    second = client.cookies.get("refresh_token")
    assert second and second != first

    attacker = TestClient(app)
    attacker.cookies.set("refresh_token", first)
    reuse = attacker.post("/api/auth/refresh", headers=CSRF)
    assert reuse.status_code == 401
    assert reuse.json()["detail"] == "Refresh token reuse detected"

    assert client.post("/api/auth/refresh", headers=CSRF).status_code == 401


def test_logout_revokes_session(client):
    register_owner(client, "owner@a.ru", "Org A")
    login(client)
    refresh_token = client.cookies.get("refresh_token")

    assert client.post("/api/auth/logout", headers=CSRF).status_code == 204
    assert client.get("/api/me").status_code == 401

    replay = TestClient(app)
    replay.cookies.set("refresh_token", refresh_token)
    assert replay.post("/api/auth/refresh", headers=CSRF).status_code == 401


def test_login_rate_limit(client):
    register_owner(client, "owner@a.ru", "Org A")
    for _ in range(5):
        assert login(client, password="wrong-password").status_code == 401

    blocked = login(client)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0

    register_owner(client, "owner@b.ru", "Org B")
    assert login(client, email="owner@b.ru").status_code == 200
