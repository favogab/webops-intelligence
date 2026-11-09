
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Incident, IncidentEvent


router = APIRouter(
    prefix="/api/v1/incidents",
    tags=["Incidents"],
)


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_id: int
    triggering_result_id: int | None
    title: str
    description: str | None
    status: str
    acknowledged: bool
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    opened_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class IncidentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    monitoring_result_id: int | None
    event_type: str
    description: str
    actor: str | None
    created_at: datetime


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(min_length=1, max_length=150)


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
    incident = db.get(Incident, incident_id)

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return incident


@router.get(
    "/{incident_id}/events",
    response_model=list[IncidentEventRead],
)
def get_incident_events(
    incident_id: int,
    db: Session = Depends(get_db),
):
    incident = db.get(Incident, incident_id)

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    statement = (
        select(IncidentEvent)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.created_at.asc(), IncidentEvent.id.asc())
    )

    return db.scalars(statement).all()


@router.post(
    "/{incident_id}/acknowledge",
    response_model=IncidentRead,
)
def acknowledge_incident(
    incident_id: int,
    payload: AcknowledgeRequest,
    db: Session = Depends(get_db),
):
    incident = db.execute(
        select(Incident)
        .where(Incident.id == incident_id)
        .with_for_update()
    ).scalar_one_or_none()

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    if incident.acknowledged:
        return incident

    if incident.status not in {"open", "recovering"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only active incidents can be acknowledged",
        )

    acknowledged_by = payload.acknowledged_by.strip()

    if not acknowledged_by:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Acknowledged by cannot be blank",
        )

    now = datetime.now().astimezone()

    incident.acknowledged = True
    incident.acknowledged_at = now
    incident.acknowledged_by = acknowledged_by
    incident.updated_at = now

    db.add(
        IncidentEvent(
            incident=incident,
            event_type="incident_acknowledged",
            description=f"Incident acknowledged by {acknowledged_by}.",
            actor=acknowledged_by,
        )
    )

    db.commit()
    db.refresh(incident)

    return incident
