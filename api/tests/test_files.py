from app import storage

PASSWORD = "StrongPass123"


def auth_headers(client, email, org):
    client.post(
        "/api/auth/register",
        json={"organization_name": org, "email": email, "password": PASSWORD},
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client, headers, name="report.txt", content=b"hello", content_type="text/plain"):
    return client.post("/api/files", headers=headers, files={"file": (name, content, content_type)})


def s3_keys():
    response = storage.s3().list_objects_v2(Bucket=storage.BUCKET)
    return [obj["Key"] for obj in response.get("Contents", [])]


def test_upload_list_download_delete(client):
    headers = auth_headers(client, "a@demo.ru", "Org A")

    response = upload(client, headers)
    assert response.status_code == 201
    uploaded = response.json()
    assert uploaded["filename"] == "report.txt"
    assert uploaded["size"] == 5

    listed = client.get("/api/files", headers=headers).json()
    assert [f["id"] for f in listed] == [uploaded["id"]]

    keys = s3_keys()
    assert len(keys) == 1 and keys[0].endswith(uploaded["id"])

    download = client.get(f"/api/files/{uploaded['id']}/download", headers=headers)
    assert download.status_code == 200
    assert "X-Amz-Signature" in download.json()["url"]

    assert client.delete(f"/api/files/{uploaded['id']}", headers=headers).status_code == 204
    assert client.get("/api/files", headers=headers).json() == []
    assert s3_keys() == []


def test_other_organization_cannot_access_file(client):
    org_a = auth_headers(client, "a@demo.ru", "Org A")
    org_b = auth_headers(client, "b@demo.ru", "Org B")
    file_id = upload(client, org_a).json()["id"]

    assert client.get("/api/files", headers=org_b).json() == []
    assert client.get(f"/api/files/{file_id}/download", headers=org_b).status_code == 404
    assert client.delete(f"/api/files/{file_id}", headers=org_b).status_code == 404
    assert client.get(f"/api/files/{file_id}/download", headers=org_a).status_code == 200


def test_upload_requires_auth(client):
    response = client.post("/api/files", files={"file": ("a.txt", b"x", "text/plain")})
    assert response.status_code == 401


def test_upload_too_large(client, monkeypatch):
    from app.routers import files as files_router

    monkeypatch.setattr(files_router, "MAX_UPLOAD_BYTES", 10)
    headers = auth_headers(client, "a@demo.ru", "Org A")
    assert upload(client, headers, content=b"x" * 11).status_code == 413
    assert s3_keys() == []


def test_filename_path_is_stripped(client):
    headers = auth_headers(client, "a@demo.ru", "Org A")
    response = upload(client, headers, name="../../etc/passwd")
    assert response.status_code == 201
    assert response.json()["filename"] == "passwd"
