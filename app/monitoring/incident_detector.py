
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Incident, MonitoringResult, Website


FAILURE_THRESHOLD = 3
RECOVERY_THRESHOLD = 2

QUALIFYING_FAILURES = {
    "server_error",
    "connection_error",
    "timeout",
}


class IncidentDetectionService:
    def __init__(self, db: Session):
        self.db = db

    def process(self, result: MonitoringResult) -> Incident | None:
        website = self.db.execute(
            select(Website)
            .where(Website.id == result.website_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()

        active_incident = self.db.execute(
            select(Incident)
            .where(
                Incident.website_id == website.id,
                Incident.status.in_(["open", "recovering"]),
            )
            .with_for_update()
        ).scalar_one_or_none()

        category = result.status_category

        if category in QUALIFYING_FAILURES:
            website.consecutive_failures += 1
            website.consecutive_successes = 0

            if active_incident is not None:
                active_incident.status = "open"
                active_incident.updated_at = datetime.now(timezone.utc)
                active_incident.resolved_at = None
                return active_incident

            if website.consecutive_failures >= FAILURE_THRESHOLD:
                incident = Incident(
                    website_id=website.id,
                    triggering_result_id=result.id,
                    title=f"Availability incident: {website.name}",
                    description=(
                        f"{FAILURE_THRESHOLD} consecutive qualifying "
                        "monitoring failures detected."
                    ),
                    status="open",
                )
                self.db.add(incident)
                return incident

            return None

        if category == "success":
            website.consecutive_failures = 0
            website.consecutive_successes += 1

            if active_incident is None:
                website.consecutive_successes = 0
                return None

            if active_incident.status == "open":
                active_incident.status = "recovering"

            if website.consecutive_successes >= RECOVERY_THRESHOLD:
                active_incident.status = "resolved"
                active_incident.resolved_at = result.checked_at
                active_incident.updated_at = result.checked_at
                website.consecutive_successes = 0

            return active_incident

        website.consecutive_failures = 0
        website.consecutive_successes = 0
        return active_incident