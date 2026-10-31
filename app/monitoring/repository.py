
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MonitoringResult
from app.monitoring.checker import CheckResult


def save_monitoring_result(
    db: Session,
    website_id: int,
    result: CheckResult,
) -> MonitoringResult:
    record = MonitoringResult(
        website_id=website_id,
        status_code=result.status_code,
        status_category=result.status_category,
        response_time_ms=result.response_time_ms,
        is_healthy=result.is_healthy,
        content_type=result.content_type,
        redirect_location=result.redirect_location,
        error=result.error,
        checked_at=result.checked_at,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def get_website_monitoring_history(
    db: Session,
    website_id: int,
    limit: int = 100,
) -> list[MonitoringResult]:
    if limit < 1:
        raise ValueError("Limit must be at least 1")

    statement = (
        select(MonitoringResult)
        .where(MonitoringResult.website_id == website_id)
        .order_by(MonitoringResult.checked_at.desc())
        .limit(limit)
    )

    return list(db.scalars(statement).all())
