
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Website, MonitoringResult
from app.monitoring.checker import CheckResult
from app.monitoring.service import DatabaseMonitoringService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    with TestingSessionLocal() as session:
        yield session

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def website(db_session):
    record = Website(
        name="Test Website",
        url="https://example.com",
        is_active=True,
    )

    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    return record


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


def test_monitor_website_saves_result(db_session, website):
    expected_result = make_result()
    service = DatabaseMonitoringService(db_session)

    with patch(
        "app.monitoring.service.check_website",
        return_value=expected_result,
    ) as checker:
        record = service.monitor_website(website.id)

    checker.assert_called_once_with(website.url)

    assert isinstance(record, MonitoringResult)
    assert record.website_id == website.id
    assert record.status_code == 200
    assert record.status_category == "success"
    assert record.is_healthy is True

    saved_records = (
        db_session.query(MonitoringResult)
        .filter_by(website_id=website.id)
        .all()
    )

    assert len(saved_records) == 1


def test_monitor_website_saves_unhealthy_result(db_session, website):
    failed_result = CheckResult(
        url=website.url,
        status_code=503,
        status_category="server_error",
        response_time_ms=250.0,
        checked_at=datetime.now(timezone.utc),
        is_healthy=False,
    )

    service = DatabaseMonitoringService(db_session)

    with patch(
        "app.monitoring.service.check_website",
        return_value=failed_result,
    ):
        record = service.monitor_website(website.id)

    assert record.is_healthy is False
    assert record.status_code == 503
    assert record.status_category == "server_error"


def test_monitor_website_rejects_unknown_website(db_session):
    service = DatabaseMonitoringService(db_session)

    with pytest.raises(LookupError, match="Website not found"):
        service.monitor_website(999)


def test_monitor_website_rejects_inactive_website(db_session, website):
    website.is_active = False
    db_session.commit()

    service = DatabaseMonitoringService(db_session)

    with patch("app.monitoring.service.check_website") as checker:
        with pytest.raises(ValueError, match="Website is inactive"):
            service.monitor_website(website.id)

    checker.assert_not_called()
