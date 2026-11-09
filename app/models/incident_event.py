from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(primary_key=True)

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )

    monitoring_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitoring_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    actor: Mapped[str | None] = mapped_column(
        String(150),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    incident: Mapped["Incident"] = relationship(
        back_populates="events",
    )

    monitoring_result: Mapped["MonitoringResult | None"] = relationship()

    __table_args__ = (
        Index("ix_incident_events_incident_created", "incident_id", "created_at"),
    )