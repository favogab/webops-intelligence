
from datetime import datetime, timezone
from time import perf_counter

import httpx
from pydantic import BaseModel


class CheckResult(BaseModel):
    url: str
    status_code: int | None
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

        response_time_ms = round(
            (perf_counter() - start) * 1000,
            2,
        )

        return CheckResult(
            url=url,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            checked_at=checked_at,
            is_healthy=200 <= response.status_code < 400,
        )

    except httpx.RequestError as exc:
        return CheckResult(
            url=url,
            status_code=None,
            response_time_ms=round(
                (perf_counter() - start) * 1000,
                2,
            ),
            checked_at=checked_at,
            is_healthy=False,
            error=type(exc).__name__,
        )
