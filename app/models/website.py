
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    consecutive_successes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
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

    monitoring_results: Mapped[list["MonitoringResult"]] = relationship(
        back_populates="website",
        cascade="all, delete-orphan",
    )

    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="website",
        cascade="all, delete-orphan",
    )
