from unittest.mock import patch

import httpx

from app.monitoring.checker import check_website


def mock_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code)


def test_successful_website_check():
    with patch("app.monitoring.checker.httpx.Client") as factory:
        client = factory.return_value.__enter__.return_value
        client.get.return_value = mock_response(200)

        result = check_website("https://example.com")

    assert result.status_code == 200
    assert result.status_category == "success"
    assert result.is_healthy is True


def test_redirect_is_not_verified_as_healthy():
    with patch("app.monitoring.checker.httpx.Client") as factory:
        client = factory.return_value.__enter__.return_value
        client.get.return_value = mock_response(301)

        result = check_website("https://example.com")

    assert result.status_code == 301
    assert result.status_category == "redirect"
    assert result.is_healthy is False


def test_client_error_is_classified():
    with patch("app.monitoring.checker.httpx.Client") as factory:
        client = factory.return_value.__enter__.return_value
        client.get.return_value = mock_response(404)

        result = check_website("https://example.com")

    assert result.status_category == "client_error"
    assert result.is_healthy is False


def test_server_error_is_unhealthy():
    with patch("app.monitoring.checker.httpx.Client") as factory:
        client = factory.return_value.__enter__.return_value
        client.get.return_value = mock_response(503)

        result = check_website("https://example.com")

    assert result.status_category == "server_error"
    assert result.is_healthy is False


def test_connection_failure():
    with patch("app.monitoring.checker.httpx.Client") as factory:
        client = factory.return_value.__enter__.return_value
        client.get.side_effect = httpx.ConnectError("Connection failed")

        result = check_website("https://example.com")

    assert result.status_code is None
    assert result.status_category == "request_error"
    assert result.is_healthy is False
    assert result.error == "ConnectError"