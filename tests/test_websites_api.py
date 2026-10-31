
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import Website, MonitoringResult


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_create_website(client):
    response = client.post(
        "/api/v1/websites",
        json={
            "name": "Example Website",
            "url": "https://example.com",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Example Website"
    assert response.json()["url"] == "https://example.com"
    assert response.json()["is_active"] is True


def test_list_websites(client):
    client.post(
        "/api/v1/websites",
        json={
            "name": "Example Website",
            "url": "https://example.com",
        },
    )

    response = client.get("/api/v1/websites")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Example Website"


def test_get_website(client):
    created = client.post(
        "/api/v1/websites",
        json={
            "name": "Example Website",
            "url": "https://example.com",
        },
    )

    website_id = created.json()["id"]

    response = client.get(f"/api/v1/websites/{website_id}")

    assert response.status_code == 200
    assert response.json()["id"] == website_id


def test_get_missing_website(client):
    response = client.get("/api/v1/websites/999")

    assert response.status_code == 404


def test_update_website(client):
    created = client.post(
        "/api/v1/websites",
        json={
            "name": "Example Website",
            "url": "https://example.com",
        },
    )

    website_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/websites/{website_id}",
        json={
            "name": "Updated Website",
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Website"
    assert response.json()["is_active"] is False


def test_delete_website(client):
    created = client.post(
        "/api/v1/websites",
        json={
            "name": "Example Website",
            "url": "https://example.com",
        },
    )

    website_id = created.json()["id"]

    response = client.delete(f"/api/v1/websites/{website_id}")

    assert response.status_code == 204

    get_response = client.get(f"/api/v1/websites/{website_id}")

    assert get_response.status_code == 404


def test_duplicate_website_url_is_rejected(client):
    payload = {
        "name": "Example Website",
        "url": "https://example.com",
    }

    first = client.post("/api/v1/websites", json=payload)
    second = client.post(
        "/api/v1/websites",
        json={
            "name": "Another Website",
            "url": "https://example.com",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_localhost_url_is_rejected(client):
    response = client.post(
        "/api/v1/websites",
        json={
            "name": "Local Website",
            "url": "http://localhost:8000",
        },
    )

    assert response.status_code == 422


def test_invalid_url_scheme_is_rejected(client):
    response = client.post(
        "/api/v1/websites",
        json={
            "name": "Invalid Website",
            "url": "ftp://example.com",
        },
    )

    assert response.status_code == 422
