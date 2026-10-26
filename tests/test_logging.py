
import json
import logging

from app.core.logging import JSONFormatter


def test_json_formatter_returns_valid_json():
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="webops.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Test monitoring event",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    data = json.loads(output)

    assert data["level"] == "INFO"
    assert data["logger"] == "webops.test"
    assert data["message"] == "Test monitoring event"
    assert "timestamp" in data


def test_json_formatter_handles_errors():
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="webops.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Monitoring failed",
        args=(),
        exc_info=None,
    )

    data = json.loads(formatter.format(record))

    assert data["level"] == "ERROR"
    assert data["message"] == "Monitoring failed"
