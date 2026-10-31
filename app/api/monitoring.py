
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Website
from app.monitoring.repository import (
    get_website_monitoring_history,
)
from app.monitoring.service import DatabaseMonitoringService


router = APIRouter(
    prefix="/api/v1/websites",
    tags=["Monitoring"],
)


class MonitoringResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_id: int
    status_code: int | None
    status_category: str
    response_time_ms: float | None
    is_healthy: bool
    content_type: str | None
    redirect_location: str | None
    error: str | None
    checked_at: datetime


@router.post(
    "/{website_id}/checks",
    response_model=MonitoringResultRead,
    status_code=status.HTTP_201_CREATED,
)
def trigger_website_check(
    website_id: int,
    db: Session = Depends(get_db),
):
    service = DatabaseMonitoringService(db)

    try:
        return service.monitor_website(website_id)

    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Website is inactive",
        )


@router.get(
    "/{website_id}/monitoring-results",
    response_model=list[MonitoringResultRead],
)
def get_website_history(
    website_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    website = db.get(Website, website_id)

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )

    return get_website_monitoring_history(
        db=db,
        website_id=website_id,
        limit=limit,
    )
