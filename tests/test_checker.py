
from unittest.mock import patch

import httpx

from app.monitoring.checker import check_website


def test_successful_website_check():
    with patch("app.monitoring.checker.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        client.get.return_value = httpx.Response(200)

        result = check_website("https://example.com")

    assert result.status_code == 200
    assert result.is_healthy is True
    assert result.response_time_ms is not None
    assert result.error is None


def test_server_error_is_unhealthy():
    with patch("app.monitoring.checker.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        client.get.return_value = httpx.Response(503)

        result = check_website("https://example.com")

    assert result.status_code == 503
    assert result.is_healthy is False


def test_connection_failure():
    with patch("app.monitoring.checker.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        client.get.side_effect = httpx.ConnectError(
            "Connection failed"
        )

        result = check_website("https://example.com")

    assert result.status_code is None
    assert result.is_healthy is False
    assert result.error == "ConnectError"
