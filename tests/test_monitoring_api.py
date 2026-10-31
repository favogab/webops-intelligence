
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import Website, MonitoringResult
from app.monitoring.checker import CheckResult


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


@pytest.fixture
def website(client):
    response = client.post(
        "/api/v1/websites",
        json={
            "name": "Example Website",
            "url": "https://example.com",
        },
    )

    return response.json()


def make_result():
    return CheckResult(
        url="https://example.com",
        status_code=200,
        status_category="success",
        response_time_ms=120.5,
        checked_at=datetime.now(timezone.utc),
        is_healthy=True,
        content_type="text/html",
    )


def test_trigger_website_check(client, website):
    expected_result = make_result()

    with patch(
        "app.monitoring.service.check_website",
        return_value=expected_result,
    ) as checker:
        response = client.post(
            f"/api/v1/websites/{website['id']}/checks"
        )

    checker.assert_called_once_with("https://example.com")

    assert response.status_code == 201
    assert response.json()["website_id"] == website["id"]
    assert response.json()["status_code"] == 200
    assert response.json()["is_healthy"] is True


def test_trigger_check_for_missing_website(client):
    response = client.post("/api/v1/websites/999/checks")

    assert response.status_code == 404


def test_trigger_check_for_inactive_website(client, website):
    client.patch(
        f"/api/v1/websites/{website['id']}",
        json={"is_active": False},
    )

    with patch("app.monitoring.service.check_website") as checker:
        response = client.post(
            f"/api/v1/websites/{website['id']}/checks"
        )

    checker.assert_not_called()

    assert response.status_code == 409


def test_get_monitoring_history(client, website):
    expected_result = make_result()

    with patch(
        "app.monitoring.service.check_website",
        return_value=expected_result,
    ):
        client.post(
            f"/api/v1/websites/{website['id']}/checks"
        )

    response = client.get(
        f"/api/v1/websites/{website['id']}/monitoring-results"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status_code"] == 200


def test_monitoring_history_respects_limit(client, website):
    expected_result = make_result()

    with patch(
        "app.monitoring.service.check_website",
        return_value=expected_result,
    ):
        for _ in range(3):
            client.post(
                f"/api/v1/websites/{website['id']}/checks"
            )

    response = client.get(
        f"/api/v1/websites/{website['id']}/monitoring-results?limit=2"
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_history_for_missing_website(client):
    response = client.get(
        "/api/v1/websites/999/monitoring-results"
    )

    assert response.status_code == 404


def test_monitoring_history_rejects_invalid_limit(client, website):
    response = client.get(
        f"/api/v1/websites/{website['id']}/monitoring-results?limit=0"
    )

    assert response.status_code == 422
