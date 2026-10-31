
from sqlalchemy.orm import Session

from app.models import Website
from app.monitoring.checker import CheckResult, check_website
from app.monitoring.history import MonitoringHistory
from app.monitoring.repository import save_monitoring_result


class MonitoringService:
    def __init__(self, history: MonitoringHistory):
        self.history = history

    def monitor(self, url: str) -> CheckResult:
        result = check_website(url)
        self.history.save_result(result)

        return result


class DatabaseMonitoringService:
    def __init__(self, db: Session):
        self.db = db

    def monitor_website(self, website_id: int):
        website = self.db.get(Website, website_id)

        if website is None:
            raise LookupError("Website not found")

        if not website.is_active:
            raise ValueError("Website is inactive")

        result = check_website(website.url)

        return save_monitoring_result(
            db=self.db,
            website_id=website.id,
            result=result,
        )
