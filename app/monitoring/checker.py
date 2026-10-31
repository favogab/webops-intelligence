
from datetime import datetime, timezone
from time import perf_counter

import httpx
from pydantic import BaseModel


class CheckResult(BaseModel):
    url: str
    status_code: int | None
    status_category: str
    response_time_ms: float | None
    checked_at: datetime
    is_healthy: bool
    error: str | None = None


def check_website(url: str) -> CheckResult:
    checked_at = datetime.now(timezone.utc)
    start = perf_counter()

    try:
        with httpx.Client(
            timeout=10.0,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = client.get(url)

        elapsed = round((perf_counter() - start) * 1000, 2)
        status = response.status_code

        if 200 <= status < 300:
            category = "success"
        elif 300 <= status < 400:
            category = "redirect"
        elif 400 <= status < 500:
            category = "client_error"
        else:
            category = "server_error"

        return CheckResult(
            url=url,
            status_code=status,
            status_category=category,
            response_time_ms=elapsed,
            checked_at=checked_at,
            is_healthy=category == "success",
        )

    except httpx.TimeoutException as exc:
        category = "timeout"
        error = type(exc).__name__

    except httpx.ConnectError as exc:
        category = "connection_error"
        error = type(exc).__name__

    except httpx.RequestError as exc:
        category = "request_error"
        error = type(exc).__name__

    return CheckResult(
        url=url,
        status_code=None,
        status_category=category,
        response_time_ms=round(
            (perf_counter() - start) * 1000,
            2,
        ),
        checked_at=checked_at,
        is_healthy=False,
        error=error,
    )
