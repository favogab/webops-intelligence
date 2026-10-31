
from datetime import datetime, timezone
from unittest.mock import patch

from app.monitoring.checker import CheckResult
from app.monitoring.history import MonitoringHistory
from app.monitoring.service import MonitoringService


def make_result():
    return CheckResult(
        url="https://example.com",
        status_code=200,
        status_category="success",
        response_time_ms=120.5,
        checked_at=datetime.now(timezone.utc),
        is_healthy=True,
        content_type="text/html",
    )


def test_monitor_checks_and_saves_result(tmp_path):
    history = MonitoringHistory(tmp_path / "test.db")
    service = MonitoringService(history)
    expected_result = make_result()

    with patch(
        "app.monitoring.service.check_website",
        return_value=expected_result,
    ) as checker:
        result = service.monitor("https://example.com")

    checker.assert_called_once_with("https://example.com")

    records = history.get_recent()

    assert result == expected_result
    assert len(records) == 1
    assert records[0].url == "https://example.com"
    assert records[0].status_category == "success"


def test_monitor_saves_unhealthy_result(tmp_path):
    history = MonitoringHistory(tmp_path / "test.db")
    service = MonitoringService(history)

    failed_result = CheckResult(
        url="https://example.com",
        status_code=503,
        status_category="server_error",
        response_time_ms=250.0,
        checked_at=datetime.now(timezone.utc),
        is_healthy=False,
    )

    with patch(
        "app.monitoring.service.check_website",
        return_value=failed_result,
    ):
        result = service.monitor("https://example.com")

    records = history.get_recent()

    assert result.is_healthy is False
    assert len(records) == 1
    assert records[0].status_category == "server_error"
    assert records[0].is_healthy is False


def test_monitor_returns_result_when_history_is_empty(tmp_path):
    history = MonitoringHistory(tmp_path / "test.db")
    service = MonitoringService(history)
    expected_result = make_result()

    with patch(
        "app.monitoring.service.check_website",
        return_value=expected_result,
    ):
        result = service.monitor("https://example.com")

    assert isinstance(result, CheckResult)
    assert result.status_code == 200
