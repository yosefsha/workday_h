"""Fetching an upstream feed over HTTP."""

from __future__ import annotations

import logging

import httpx

from app.sources.protocols import SourceUnavailableError

logger = logging.getLogger(__name__)


class FeedUnavailableError(SourceUnavailableError):
    """An upstream HTTP feed could not be read.

    A subclass so the ingest pipeline can catch the protocol-level
    SourceUnavailableError without knowing that this particular source speaks
    HTTP, while callers that do care can still catch this.
    """


class FeedClient:
    """Reads a feed's body, with an explicit timeout and a bounded retry.

    Both feeds are small static documents, so one retry covers a dropped
    connection without turning an outage into a retry storm.
    """

    def __init__(self, *, connect_timeout: float, read_timeout: float, retries: int) -> None:
        self._timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=connect_timeout,
        )
        self._retries = max(retries, 0)

    def fetch_text(self, url: str) -> str:
        attempts = self._retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = httpx.get(url, timeout=self._timeout, follow_redirects=True)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as error:
                last_error = error
                logger.warning(
                    "feed fetch failed (attempt %d/%d): %s: %s", attempt, attempts, url, error
                )

        raise FeedUnavailableError(f"could not read feed at {url}: {last_error}") from last_error
