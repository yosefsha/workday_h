"""The résumé feed as a CandidateSource."""

from __future__ import annotations

from app.domain.candidate import Candidate
from app.sources.feed_client import FeedClient
from app.sources.resume_feed import parse_resume_feed


class ResumeFeedSource:
    """Fetches the résumé feed over HTTP and parses it into candidates.

    A thin adapter: the fetching lives in FeedClient and the parsing in
    resume_feed.parse_resume_feed, both of which stay usable without this
    class. This exists only to satisfy the CandidateSource protocol.
    """

    def __init__(self, *, client: FeedClient, url: str, name: str = "resume_feed") -> None:
        self._client = client
        self._url = url
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def load(self) -> list[Candidate]:
        return parse_resume_feed(self._client.fetch_text(self._url))
