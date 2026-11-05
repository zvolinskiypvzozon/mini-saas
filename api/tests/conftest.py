import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy import text

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["S3_ENDPOINT"] = ""
os.environ["S3_PUBLIC_ENDPOINT"] = ""
os.environ["S3_ACCESS_KEY"] = "test"
os.environ["S3_SECRET_KEY"] = "test"
os.environ["S3_REGION"] = "us-east-1"

from app import storage  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, organizations CASCADE"))


@pytest.fixture(autouse=True)
def s3_mock():
    with mock_aws():
        storage.ensure_bucket()
        yield


@pytest.fixture
def client():
    return TestClient(app)
