
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import Incident, IncidentEvent


@pytest.fixture
def api():
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

    with TestClient(app) as client:
        yield client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def incident_record(api):
    client, SessionLocal = api

    website_response = client.post(
        "/api/v1/websites",
        json={
            "name": "Test Website",
            "url": "https://example.com",
        },
    )

    assert website_response.status_code == 201

    website_id = website_response.json()["id"]

    with SessionLocal() as db:
        incident = Incident(
            website_id=website_id,
            title="Availability incident: Test Website",
            description="Three consecutive monitoring failures detected.",
            status="open",
        )

        db.add(incident)
        db.commit()
        db.refresh(incident)

        incident_id = incident.id

    return incident_id, website_id


def test_get_incident(api, incident_record):
    client, _ = api
    incident_id, website_id = incident_record

    response = client.get(
        f"/api/v1/incidents/{incident_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == incident_id
    assert response.json()["website_id"] == website_id
    assert response.json()["status"] == "open"
    assert response.json()["acknowledged"] is False


def test_get_missing_incident(api):
    client, _ = api

    response = client.get("/api/v1/incidents/999")

    assert response.status_code == 404


def test_get_events_for_missing_incident(api):
    client, _ = api

    response = client.get("/api/v1/incidents/999/events")

    assert response.status_code == 404


def test_get_incident_events_in_chronological_order(
    api,
    incident_record,
):
    client, SessionLocal = api
    incident_id, _ = incident_record

    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        db.add_all(
            [
                IncidentEvent(
                    incident_id=incident_id,
                    event_type="incident_opened",
                    description="Incident opened.",
                    actor="system",
                    created_at=now,
                ),
                IncidentEvent(
                    incident_id=incident_id,
                    event_type="recovery_started",
                    description="Recovery started.",
                    actor="system",
                    created_at=now + timedelta(minutes=2),
                ),
                IncidentEvent(
                    incident_id=incident_id,
                    event_type="monitoring_success",
                    description="Successful check recorded.",
                    actor="system",
                    created_at=now + timedelta(minutes=1),
                ),
            ]
        )
        db.commit()

    response = client.get(
        f"/api/v1/incidents/{incident_id}/events"
    )

    assert response.status_code == 200

    events = response.json()

    assert len(events) == 3
    assert [event["event_type"] for event in events] == [
        "incident_opened",
        "monitoring_success",
        "recovery_started",
    ]


def test_acknowledge_active_incident(api, incident_record):
    client, _ = api
    incident_id, _ = incident_record

    response = client.post(
        f"/api/v1/incidents/{incident_id}/acknowledge",
        json={"acknowledged_by": "Favogab"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["acknowledged"] is True
    assert data["acknowledged_by"] == "Favogab"
    assert data["acknowledged_at"] is not None
    assert data["status"] == "open"


def test_acknowledgement_creates_audit_event(
    api,
    incident_record,
):
    client, SessionLocal = api
    incident_id, _ = incident_record

    response = client.post(
        f"/api/v1/incidents/{incident_id}/acknowledge",
        json={"acknowledged_by": "Favogab"},
    )

    assert response.status_code == 200

    with SessionLocal() as db:
        events = db.scalars(
            select(IncidentEvent).where(
                IncidentEvent.incident_id == incident_id,
                IncidentEvent.event_type == "incident_acknowledged",
            )
        ).all()

    assert len(events) == 1
    assert events[0].actor == "Favogab"


def test_acknowledging_twice_does_not_create_duplicate_events(
    api,
    incident_record,
):
    client, SessionLocal = api
    incident_id, _ = incident_record

    payload = {"acknowledged_by": "Favogab"}

    first = client.post(
        f"/api/v1/incidents/{incident_id}/acknowledge",
        json=payload,
    )

    second = client.post(
        f"/api/v1/incidents/{incident_id}/acknowledge",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    with SessionLocal() as db:
        events = db.scalars(
            select(IncidentEvent).where(
                IncidentEvent.incident_id == incident_id,
                IncidentEvent.event_type == "incident_acknowledged",
            )
        ).all()

    assert len(events) == 1


def test_resolved_incident_cannot_be_acknowledged(
    api,
    incident_record,
):
    client, SessionLocal = api
    incident_id, _ = incident_record

    with SessionLocal() as db:
        incident = db.get(Incident, incident_id)
        incident.status = "resolved"
        incident.resolved_at = datetime.now(timezone.utc)
        db.commit()

    response = client.post(
        f"/api/v1/incidents/{incident_id}/acknowledge",
        json={"acknowledged_by": "Favogab"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only active incidents can be acknowledged"
    )


def test_acknowledgement_rejects_blank_operator_name(
    api,
    incident_record,
):
    client, _ = api
    incident_id, _ = incident_record

    response = client.post(
        f"/api/v1/incidents/{incident_id}/acknowledge",
        json={"acknowledged_by": "   "},
    )

    assert response.status_code == 422


def create_test_incident(
    client,
    SessionLocal,
    incident_status="open",
    opened_at=None,
    website_id=None,
):
    # Create a separate website unless one was supplied.
    if website_id is None:
        unique_token = datetime.now(timezone.utc).timestamp()

        website_response = client.post(
            "/api/v1/websites",
            json={
                "name": f"Test Website {unique_token}",
                "url": f"https://example-{unique_token}.com",
            },
        )

        assert website_response.status_code == 201

        website_id = website_response.json()["id"]

    timestamp = opened_at or datetime.now(timezone.utc)

    with SessionLocal() as db:
        incident = Incident(
            website_id=website_id,
            title=f"Test incident: {incident_status}",
            description="Test incident for listing API.",
            status=incident_status,
            opened_at=timestamp,
            updated_at=timestamp,
        )

        db.add(incident)
        db.commit()
        db.refresh(incident)

        return incident.id


def test_list_incidents(api, incident_record):
    client, _ = api

    response = client.get("/api/v1/incidents")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "open"
    assert data["limit"] == 20
    assert data["offset"] == 0


def test_filter_incidents_by_status(api, incident_record):
    client, SessionLocal = api
    _, website_id = incident_record

    create_test_incident(
        client,
        SessionLocal,
        incident_status="resolved",
        website_id=website_id,
    )

    response = client.get("/api/v1/incidents?status=resolved")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert all(
        item["status"] == "resolved"
        for item in data["items"]
    )


def test_filter_incidents_by_website(api, incident_record):
    client, SessionLocal = api
    _, website_id = incident_record

    second_website = client.post(
        "/api/v1/websites",
        json={
            "name": "Second Website",
            "url": "https://example.org",
        },
    )

    assert second_website.status_code == 201

    second_website_id = second_website.json()["id"]

    create_test_incident(
        client,
        SessionLocal,
        website_id=second_website_id,
    )

    response = client.get(
        f"/api/v1/incidents?website_id={website_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert all(
        item["website_id"] == website_id
        for item in data["items"]
    )


def test_incident_pagination(api, incident_record):
    client, SessionLocal = api

    for _ in range(3):
        create_test_incident(client, SessionLocal)

    response = client.get(
        "/api/v1/incidents?limit=2&offset=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 1


def test_incidents_are_ordered_newest_first(api, incident_record):
    client, SessionLocal = api

    now = datetime.now(timezone.utc)

    create_test_incident(
        client,
        SessionLocal,
        opened_at=now - timedelta(minutes=10),
    )

    newest_id = create_test_incident(
        client,
        SessionLocal,
        opened_at=now + timedelta(minutes=10),
    )

    response = client.get("/api/v1/incidents")

    assert response.status_code == 200

    items = response.json()["items"]

    assert items[0]["id"] == newest_id


def test_combine_incident_filters(api, incident_record):
    client, SessionLocal = api
    _, website_id = incident_record

    # This resolved incident belongs to the website being filtered.
    create_test_incident(
        client,
        SessionLocal,
        incident_status="resolved",
        website_id=website_id,
    )

    # This active incident belongs to another website.
    create_test_incident(
        client,
        SessionLocal,
        incident_status="recovering",
    )

    response = client.get(
        f"/api/v1/incidents?status=resolved&website_id={website_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["status"] == "resolved"
    assert data["items"][0]["website_id"] == website_id


def test_invalid_incident_status_is_rejected(api):
    client, _ = api

    response = client.get(
        "/api/v1/incidents?status=invalid"
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "offset=-1",
    ],
)
def test_invalid_incident_pagination_is_rejected(api, query):
    client, _ = api

    response = client.get(
        f"/api/v1/incidents?{query}"
    )

    assert response.status_code == 422
