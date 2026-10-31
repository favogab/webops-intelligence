
from app.monitoring.checker import CheckResult, check_website
from app.monitoring.history import MonitoringHistory


class MonitoringService:
    def __init__(self, history: MonitoringHistory):
        self.history = history

    def monitor(self, url: str) -> CheckResult:
        result = check_website(url)
        self.history.save_result(result)

        return result
