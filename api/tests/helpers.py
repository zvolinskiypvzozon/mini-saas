PASSWORD = "StrongPass123"


def login(client, email, password=PASSWORD):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_owner(client, email, org):
    response = client.post(
        "/api/auth/register",
        json={"organization_name": org, "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return login(client, email)


def create_user(client, admin_headers, email, role="member"):
    response = client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": email, "password": PASSWORD, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"], login(client, email)
