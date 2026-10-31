
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_200():
    response = client.get("/health")

    assert response.status_code == 200


def test_health_endpoint_returns_expected_data():
    response = client.get("/health")

    assert response.json() == {
        "status": "ok",
        "service": "webops-intelligence",
        "environment": "development",
    }


def test_unknown_route_returns_404():
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
