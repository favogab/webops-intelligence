
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Incident, MonitoringResult, Website
from app.monitoring.incident_detector import IncidentDetectionService


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def website(db):
    record = Website(
        name="Test Website",
        url="https://example.com",
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def make_result(db, website, category):
    status_codes = {
        "success": 200,
        "server_error": 503,
        "client_error": 404,
    }

    result = MonitoringResult(
        website_id=website.id,
        status_code=status_codes.get(category),
        status_category=category,
        response_time_ms=100.0,
        is_healthy=category == "success",
        checked_at=datetime.now(timezone.utc),
    )

    db.add(result)
    db.flush()

    return result


def process_check(db, website, category):
    result = make_result(db, website, category)
    incident = IncidentDetectionService(db).process(result)
    db.flush()
    return incident


def get_incidents(db, website):
    return list(
        db.scalars(
            select(Incident).where(
                Incident.website_id == website.id
            )
        ).all()
    )


def test_incident_opens_after_three_consecutive_failures(db, website):
    detector = IncidentDetectionService(db)

    for _ in range(2):
        result = make_result(db, website, "server_error")
        assert detector.process(result) is None

    result = make_result(db, website, "server_error")
    incident = detector.process(result)

    assert incident is not None
    assert incident.status == "open"
    assert incident.triggering_result_id == result.id
    assert website.consecutive_failures == 3

    assert len(get_incidents(db, website)) == 1


def test_success_resets_failure_streak(db, website):
    process_check(db, website, "server_error")
    process_check(db, website, "server_error")
    process_check(db, website, "success")

    assert website.consecutive_failures == 0
    assert website.consecutive_successes == 0
    assert get_incidents(db, website) == []

    process_check(db, website, "server_error")
    process_check(db, website, "server_error")

    assert website.consecutive_failures == 2
    assert get_incidents(db, website) == []


def test_incident_enters_recovering_after_first_success(db, website):
    for _ in range(3):
        process_check(db, website, "server_error")

    incident = get_incidents(db, website)[0]

    process_check(db, website, "success")

    assert incident.status == "recovering"
    assert website.consecutive_successes == 1
    assert incident.resolved_at is None


def test_incident_resolves_after_two_successful_checks(db, website):
    for _ in range(3):
        process_check(db, website, "server_error")

    incident = get_incidents(db, website)[0]

    process_check(db, website, "success")
    process_check(db, website, "success")

    assert incident.status == "resolved"
    assert incident.resolved_at is not None
    assert website.consecutive_failures == 0
    assert website.consecutive_successes == 0

    assert len(get_incidents(db, website)) == 1


def test_failure_during_recovery_reopens_incident(db, website):
    for _ in range(3):
        process_check(db, website, "server_error")

    incident = get_incidents(db, website)[0]

    process_check(db, website, "success")
    assert incident.status == "recovering"

    process_check(db, website, "timeout")

    assert incident.status == "open"
    assert incident.resolved_at is None
    assert website.consecutive_failures == 1
    assert website.consecutive_successes == 0


def test_client_error_does_not_count_as_outage(db, website):
    process_check(db, website, "server_error")
    process_check(db, website, "server_error")
    process_check(db, website, "client_error")

    assert website.consecutive_failures == 0
    assert get_incidents(db, website) == []


def test_non_qualifying_check_resets_failure_streak(db, website):
    process_check(db, website, "server_error")
    process_check(db, website, "server_error")
    process_check(db, website, "redirect")

    assert website.consecutive_failures == 0
    assert get_incidents(db, website) == []


def test_new_failure_streak_can_open_another_incident_after_resolution(
    db,
    website,
):
    for _ in range(3):
        process_check(db, website, "server_error")

    first_incident = get_incidents(db, website)[0]

    process_check(db, website, "success")
    process_check(db, website, "success")

    assert first_incident.status == "resolved"

    for _ in range(3):
        process_check(db, website, "server_error")

    incidents = get_incidents(db, website)

    assert len(incidents) == 2
    assert incidents[0].status == "resolved"
    assert incidents[1].status == "open"