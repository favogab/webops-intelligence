
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Website, MonitoringResult
from app.monitoring.checker import CheckResult
from app.monitoring.repository import (
    save_monitoring_result,
    get_website_monitoring_history,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def website(db):
    record = Website(
        name="Example Website",
        url="https://example.com",
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def make_result(
    status_code=200,
    category="success",
    healthy=True,
):
    return CheckResult(
        url="https://example.com",
        status_code=status_code,
        status_category=category,
        response_time_ms=125.5,
        checked_at=datetime.now(timezone.utc),
        is_healthy=healthy,
        content_type="text/html",
    )


def test_save_monitoring_result(db, website):
    result = make_result()

    saved = save_monitoring_result(
        db,
        website.id,
        result,
    )

    assert saved.id is not None
    assert saved.website_id == website.id
    assert saved.status_code == 200
    assert saved.status_category == "success"
    assert saved.is_healthy is True


def test_save_failed_monitoring_result(db, website):
    result = make_result(
        status_code=None,
        category="timeout",
        healthy=False,
    )

    result.error = "ReadTimeout"

    saved = save_monitoring_result(
        db,
        website.id,
        result,
    )

    assert saved.status_code is None
    assert saved.status_category == "timeout"
    assert saved.is_healthy is False
    assert saved.error == "ReadTimeout"


def test_retrieve_website_monitoring_history(db, website):
    save_monitoring_result(
        db,
        website.id,
        make_result(),
    )

    save_monitoring_result(
        db,
        website.id,
        make_result(503, "server_error", False),
    )

    history = get_website_monitoring_history(
        db,
        website.id,
    )

    assert len(history) == 2
    assert all(item.website_id == website.id for item in history)


def test_monitoring_history_respects_limit(db, website):
    for _ in range(3):
        save_monitoring_result(
            db,
            website.id,
            make_result(),
        )

    history = get_website_monitoring_history(
        db,
        website.id,
        limit=2,
    )

    assert len(history) == 2


def test_monitoring_history_rejects_invalid_limit(db, website):
    with pytest.raises(ValueError):
        get_website_monitoring_history(
            db,
            website.id,
            limit=0,
        )


def test_monitoring_result_belongs_to_website(db, website):
    saved = save_monitoring_result(
        db,
        website.id,
        make_result(),
    )

    db.refresh(website)

    assert saved.website_id == website.id
    assert len(website.monitoring_results) == 1
    assert website.monitoring_results[0].id == saved.id


def test_invalid_website_reference_is_rejected(db):
    result = make_result()

    with pytest.raises(Exception):
        save_monitoring_result(
            db,
            website_id=999,
            result=result,
        )

    db.rollback()

    assert db.query(MonitoringResult).count() == 0
