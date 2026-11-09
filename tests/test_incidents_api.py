
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import Incident, IncidentEvent, Website


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
