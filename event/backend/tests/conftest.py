import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

TEST_DB = Path(__file__).parent / "m3-test.db"
TEST_STORAGE = Path(__file__).parent / "test-storage"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["BOOTSTRAP_DEMO_DATA"] = "true"
os.environ["COOKIE_SECURE"] = "false"
os.environ["STORAGE_ROOT"] = str(TEST_STORAGE)

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def client():
    shutil.rmtree(TEST_STORAGE, ignore_errors=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    shutil.rmtree(TEST_STORAGE, ignore_errors=True)


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        yield session
    Base.metadata.drop_all(bind=engine)


def login(client: TestClient, username: str, password: str = "demo123"):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


@pytest.fixture()
def reviewer_client(client: TestClient):
    response = login(client, "reviewer")
    assert response.status_code == 200
    return client


@pytest.fixture()
def limited_client(client: TestClient):
    response = login(client, "reviewer_limited")
    assert response.status_code == 200
    return client


@pytest.fixture()
def admin_client(client: TestClient):
    response = login(client, "admin")
    assert response.status_code == 200
    return client
