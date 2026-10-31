
from datetime import datetime, timezone

import pytest

from app.monitoring.checker import CheckResult
from app.monitoring.history import MonitoringHistory


@pytest.fixture
def history(tmp_path):
    db_path = tmp_path / "test_history.db"
    return MonitoringHistory(db_path)


def make_result(
    status_code=200,
    category="success",
    healthy=True,
):
    return CheckResult(
        url="https://example.com",
        status_code=status_code,
        status_category=category,
        response_time_ms=125.5,
        checked_at=datetime.now(timezone.utc),
        is_healthy=healthy,
        content_type="text/html",
    )


def test_save_and_retrieve_result(history):
    result = make_result()

    history.save_result(result)
    records = history.get_recent()

    assert len(records) == 1
    assert records[0].url == result.url
    assert records[0].status_code == 200
    assert records[0].status_category == "success"
    assert records[0].is_healthy is True


def test_multiple_results_are_retrieved_newest_first(history):
    first = make_result(200, "success", True)
    second = make_result(503, "server_error", False)

    history.save_result(first)
    history.save_result(second)

    records = history.get_recent()

    assert len(records) == 2
    assert records[0].status_code == 503
    assert records[1].status_code == 200


def test_history_respects_limit(history):
    for _ in range(3):
        history.save_result(make_result())

    records = history.get_recent(limit=2)

    assert len(records) == 2


def test_history_preserves_failure_evidence(history):
    result = CheckResult(
        url="https://example.com",
        status_code=None,
        status_category="timeout",
        response_time_ms=10000.0,
        checked_at=datetime.now(timezone.utc),
        is_healthy=False,
        error="ReadTimeout",
    )

    history.save_result(result)
    records = history.get_recent()

    assert records[0].status_category == "timeout"
    assert records[0].error == "ReadTimeout"
    assert records[0].is_healthy is False


def test_invalid_history_limit_is_rejected(history):
    with pytest.raises(ValueError):
        history.get_recent(limit=0)
