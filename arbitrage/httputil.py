"""Shared HTTP retry/backoff policy for all outbound API clients.

One policy everywhere: retry with exponential backoff on rate-limit (429) and
transient server errors (5xx); everything else raises immediately. Callers that
need to treat a specific status specially (e.g. eBay returning 403 for an
unapproved API) catch ``httpx.HTTPStatusError`` and inspect the response.
"""
from __future__ import annotations

import time
from collections.abc import Callable

import httpx
import structlog

log = structlog.get_logger(__name__)

RETRY_STATUSES = (429, 500, 502, 503, 504)
DEFAULT_ATTEMPTS = 4
DEFAULT_BASE_DELAY = 2.0


def get_with_backoff(
    client: httpx.Client,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """GET with exponential backoff on 429/5xx. Raises on other errors and
    when attempts are exhausted (never returns a failed response silently)."""
    delay = base_delay
    last: httpx.HTTPError | None = None
    for _ in range(attempts):
        resp = client.get(url, headers=headers)
        if resp.status_code in RETRY_STATUSES:
            log.warning(
                "http.retrying", url=str(resp.request.url), status=resp.status_code,
                sleep=delay,
            )
            sleep(delay)
            delay *= 2
            last = httpx.HTTPStatusError(
                f"retryable status {resp.status_code}",
                request=resp.request,
                response=resp,
            )
            continue
        resp.raise_for_status()
        return resp
    raise last or httpx.HTTPError(f"request failed after {attempts} attempts: {url}")
