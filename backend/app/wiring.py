"""Where the concrete pieces are assembled.

The domain and the services take their collaborators as arguments; this module
is the only place that decides what those collaborators actually are, so both
entry points get an identically-configured stack.

**Adding a data source happens here.** Write a class satisfying CandidateSource
or EnrichmentSource in app/sources/, then add it to `build_enrichments()`.
Nothing in the ingest pipeline, the store or the renderers changes.
"""

from __future__ import annotations

from app.config import settings
from app.ingest.service import IngestService
from app.sources.feed_client import FeedClient
from app.sources.linkedin_source import LinkedInFeedSource
from app.sources.protocols import CandidateSource, EnrichmentSource
from app.sources.resume_source import ResumeFeedSource
from app.store.engine import engine
from app.store.repository import SnapshotRepository


def build_repository() -> SnapshotRepository:
    return SnapshotRepository(engine)


def build_feed_client() -> FeedClient:
    return FeedClient(
        connect_timeout=settings.feed_connect_timeout_seconds,
        read_timeout=settings.feed_read_timeout_seconds,
        retries=settings.feed_retries,
    )


def build_candidate_source() -> CandidateSource:
    """The source that produces candidates. Exactly one, by definition."""
    return ResumeFeedSource(client=build_feed_client(), url=settings.resume_feed_url)


def build_enrichments() -> list[EnrichmentSource]:
    """The registry. Sources are applied in this order.

    Order matters when two sources contribute the same field: the later one
    wins. Today there is one source and the question does not arise.
    """
    return [
        LinkedInFeedSource(client=build_feed_client(), url=settings.linkedin_feed_url),
    ]


def build_ingest_service() -> IngestService:
    return IngestService(
        candidate_source=build_candidate_source(),
        enrichments=build_enrichments(),
        repository=build_repository(),
    )
