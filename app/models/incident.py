
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)

    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    triggering_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitoring_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(30),
        default="open",
        nullable=False,
    )

    acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    website: Mapped["Website"] = relationship(
        back_populates="incidents",
    )

    triggering_result: Mapped["MonitoringResult | None"] = relationship()

    __table_args__ = (
        Index(
            "uq_incidents_one_active_per_website",
            "website_id",
            unique=True,
            postgresql_where=text("status IN ('open', 'recovering')"),
            sqlite_where=text("status IN ('open', 'recovering')"),
        ),
    )
