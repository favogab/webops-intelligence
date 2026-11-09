
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Website
from app.monitoring.service import DatabaseMonitoringService

logger = logging.getLogger("webops.monitoring.scheduler")

_scheduler: BackgroundScheduler | None = None


def run_monitoring_cycle() -> None:
    """Check every active website and persist its monitoring result."""

    try:
        with SessionLocal() as db:
            website_ids = db.scalars(
                select(Website.id).where(Website.is_active.is_(True))
            ).all()

    except Exception:
        logger.exception("Unable to retrieve active websites for monitoring")
        return

    if not website_ids:
        logger.info("Monitoring cycle skipped: no active websites found")
        return

    logger.info(
        "Starting monitoring cycle for %s active website(s)",
        len(website_ids),
    )

    for website_id in website_ids:
        try:
            with SessionLocal() as db:
                service = DatabaseMonitoringService(db)
                result = service.monitor_website(website_id)

                logger.info(
                    "Website check completed: website_id=%s status=%s healthy=%s",
                    website_id,
                    result.status_category,
                    result.is_healthy,
                )

        except Exception:
            logger.exception(
                "Monitoring failed for website_id=%s",
                website_id,
            )

    logger.info("Monitoring cycle completed")


def start_scheduler() -> None:
    """Start recurring website monitoring."""

    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.info("Monitoring scheduler is already running")
        return

    settings = get_settings()

    _scheduler = BackgroundScheduler(timezone="UTC")

    _scheduler.add_job(
        run_monitoring_cycle,
        trigger="interval",
        seconds=settings.monitoring_interval_seconds,
        id="website_monitoring",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )

    _scheduler.start()

    logger.info(
        "Monitoring scheduler started: interval=%s seconds",
        settings.monitoring_interval_seconds,
    )


def shutdown_scheduler() -> None:
    """Stop the monitoring scheduler cleanly."""

    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Monitoring scheduler stopped")

    _scheduler = None