
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Website, MonitoringResult


def test_website_can_have_multiple_monitoring_results():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        website = Website(
            name="Example",
            url="https://example.com",
        )

        website.monitoring_results.append(
            MonitoringResult(
                status_code=200,
                status_category="success",
                response_time_ms=120.5,
                is_healthy=True,
                checked_at=datetime.now(timezone.utc),
            )
        )

        website.monitoring_results.append(
            MonitoringResult(
                status_code=503,
                status_category="server_error",
                response_time_ms=250.0,
                is_healthy=False,
                checked_at=datetime.now(timezone.utc),
            )
        )

        session.add(website)
        session.commit()

        session.refresh(website)

        assert len(website.monitoring_results) == 2
        assert website.monitoring_results[0].status_code == 200
        assert website.monitoring_results[1].status_code == 503
