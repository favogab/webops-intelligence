
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MonitoringResult(Base):
    __tablename__ = "monitoring_results"

    id: Mapped[int] = mapped_column(primary_key=True)

    website_id: Mapped[int] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status_code: Mapped[int | None] = mapped_column(Integer)
    status_category: Mapped[str] = mapped_column(String(50), nullable=False)
    response_time_ms: Mapped[float | None] = mapped_column(Float)
    is_healthy: Mapped[bool] = mapped_column(Boolean, nullable=False)

    content_type: Mapped[str | None] = mapped_column(String(255))
    redirect_location: Mapped[str | None] = mapped_column(String(2048))
    error: Mapped[str | None] = mapped_column(String(255))

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    website: Mapped["Website"] = relationship(
        back_populates="monitoring_results",
    )
