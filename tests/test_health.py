
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_success():
    response = client.get("/health")

    assert response.status_code == 200


def test_health_returns_expected_data():
    response = client.get("/health")

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "webops-intelligence"
    assert data["environment"] == "development"


def test_unknown_endpoint_returns_not_found():
    response = client.get("/does-not-exist")

    assert response.status_code == 404