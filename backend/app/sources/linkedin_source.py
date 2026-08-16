"""The LinkedIn feed as an EnrichmentSource."""

from __future__ import annotations

from app.sources.feed_client import FeedClient
from app.sources.linkedin_feed import LinkedInDirectory, parse_linkedin_feed


class LinkedInFeedSource:
    """Fetches the LinkedIn CSV and returns it as an applicable enrichment.

    Not required: it contributes an optional profile URL and nothing else, so a
    failure here leaves every candidate without a profile rather than taking
    the report down. See CONTEXT.md on the LinkedIn Feed being supplemental.
    """

    def __init__(self, *, client: FeedClient, url: str, name: str = "linkedin_feed") -> None:
        self._client = client
        self._url = url
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def required(self) -> bool:
        return False

    def load(self) -> LinkedInDirectory:
        return parse_linkedin_feed(self._client.fetch_text(self._url))
