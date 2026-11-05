import pytest

from tests.helpers import PASSWORD, create_user, register_owner


@pytest.fixture
def org(client):
    owner = register_owner(client, "owner@a.ru", "Org A")
    m1_id, m1 = create_user(client, owner, "m1@a.ru")
    m2_id, m2 = create_user(client, owner, "m2@a.ru")
    return {"owner": owner, "m1": m1, "m1_id": m1_id, "m2": m2, "m2_id": m2_id}


def create_project(client, headers, name="Website"):
    return client.post("/api/projects", headers=headers, json={"name": name})


def add_member(client, headers, project_id, user_id):
    return client.post(
        f"/api/projects/{project_id}/members", headers=headers, json={"user_id": user_id}
    )


def test_member_cannot_create_project_or_users(client, org):
    assert create_project(client, org["m1"]).status_code == 403
    response = client.post(
        "/api/users",
        headers=org["m1"],
        json={"email": "x@a.ru", "password": PASSWORD, "role": "member"},
    )
    assert response.status_code == 403


def test_owner_role_cannot_be_granted(client, org):
    response = client.post(
        "/api/users",
        headers=org["owner"],
        json={"email": "boss@a.ru", "password": PASSWORD, "role": "owner"},
    )
    assert response.status_code == 422


def test_project_visible_only_to_members(client, org):
    project_id = create_project(client, org["owner"]).json()["id"]

    assert client.get("/api/projects", headers=org["m1"]).json() == []
    assert client.get(f"/api/projects/{project_id}", headers=org["m1"]).status_code == 404

    assert add_member(client, org["owner"], project_id, org["m1_id"]).status_code == 201
    visible = client.get("/api/projects", headers=org["m1"]).json()
    assert [p["id"] for p in visible] == [project_id]
    assert client.get("/api/projects", headers=org["m2"]).json() == []


def test_duplicate_project_name(client, org):
    assert create_project(client, org["owner"]).status_code == 201
    assert create_project(client, org["owner"]).status_code == 409


def test_add_member_rules(client, org):
    project_id = create_project(client, org["owner"]).json()["id"]
    assert add_member(client, org["owner"], project_id, org["m1_id"]).status_code == 201
    assert add_member(client, org["owner"], project_id, org["m1_id"]).status_code == 409

    other_owner = register_owner(client, "owner@b.ru", "Org B")
    other_id = client.get("/api/me", headers=other_owner).json()["id"]
    assert add_member(client, org["owner"], project_id, other_id).status_code == 404


def test_task_lifecycle(client, org):
    project_id = create_project(client, org["owner"]).json()["id"]
    add_member(client, org["owner"], project_id, org["m1_id"])
    tasks_url = f"/api/projects/{project_id}/tasks"

    response = client.post(
        tasks_url,
        headers=org["m1"],
        json={"title": "Set up CI", "assignee_id": org["m1_id"], "due_date": "2026-12-01"},
    )
    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "todo"
    assert task["due_date"] == "2026-12-01"

    not_member = client.post(
        tasks_url, headers=org["m1"], json={"title": "X", "assignee_id": org["m2_id"]}
    )
    assert not_member.status_code == 422

    task_url = f"/api/tasks/{task['id']}"
    updated = client.patch(task_url, headers=org["m1"], json={"status": "done"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert updated.json()["title"] == "Set up CI"

    assert client.patch(task_url, headers=org["m1"], json={"status": "finished"}).status_code == 422
    assert client.patch(task_url, headers=org["m1"], json={"title": None}).status_code == 422

    client.post(tasks_url, headers=org["m1"], json={"title": "Write docs"})
    done = client.get(tasks_url, headers=org["m1"], params={"status": "done"}).json()
    assert [t["title"] for t in done] == ["Set up CI"]

    assert client.get(tasks_url, headers=org["m2"]).status_code == 404


def test_other_org_cannot_access_project_or_task(client, org):
    project_id = create_project(client, org["owner"]).json()["id"]
    tasks_url = f"/api/projects/{project_id}/tasks"
    task_id = client.post(tasks_url, headers=org["owner"], json={"title": "Secret"}).json()["id"]

    other = register_owner(client, "owner@b.ru", "Org B")
    assert client.get(f"/api/projects/{project_id}", headers=other).status_code == 404
    assert client.get(tasks_url, headers=other).status_code == 404
    assert client.patch(f"/api/tasks/{task_id}", headers=other, json={"status": "done"}).status_code == 404
    assert client.delete(f"/api/projects/{project_id}", headers=other).status_code == 404


def test_delete_project_cascades_tasks(client, org):
    project_id = create_project(client, org["owner"]).json()["id"]
    task_id = client.post(
        f"/api/projects/{project_id}/tasks", headers=org["owner"], json={"title": "T"}
    ).json()["id"]

    assert client.delete(f"/api/projects/{project_id}", headers=org["owner"]).status_code == 204
    assert client.patch(f"/api/tasks/{task_id}", headers=org["owner"], json={"status": "done"}).status_code == 404
