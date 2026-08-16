"""The contract every data source implements.

Two protocols, because sources do two genuinely different jobs. A
CandidateSource *produces* candidates — without one there is no report. An
EnrichmentSource *adds* to candidates that already exist, and by default its
absence degrades the report rather than failing it.

Adding a source is writing one class and registering it in app/wiring.py.
Nothing in the ingest pipeline names a specific feed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.domain.candidate import Candidate


class SourceUnavailableError(RuntimeError):
    """A source could not be read.

    The contract-level failure. HTTP feeds raise the FeedUnavailableError
    subclass; a source backed by a file, a database or a vendor SDK raises this
    directly, and the ingest pipeline handles all of them identically.
    """


@dataclass(frozen=True)
class SourceStatus:
    """What one source did during one run.

    `ok` and `matched` answer different questions. A source that returned
    cleanly and matched nobody is not the same event as a source that was
    unreachable, and a NULL in the output means something different in each
    case.

    Lives here rather than with the ingest service so the store can persist it
    without the store and the pipeline importing each other.
    """

    name: str
    ok: bool
    matched: int | None = None
    detail: str | None = None


@dataclass(frozen=True)
class EnrichmentOutcome:
    """The result of applying one enrichment to the whole candidate set.

    `matched` is how many candidates the enrichment actually had data for, and
    it is reported separately from success: a source that returns cleanly and
    matches nobody is not the same event as a source that was unreachable.
    """

    candidates: list[Candidate]
    matched: int


@runtime_checkable
class Enrichment(Protocol):
    """Loaded data from an EnrichmentSource, ready to apply."""

    def apply(self, candidates: list[Candidate]) -> EnrichmentOutcome:
        """Return the candidates with this source's contribution attached.

        Takes the whole set rather than one candidate at a time so an
        implementation is free to do a single bulk lookup instead of N.
        """
        ...


@runtime_checkable
class CandidateSource(Protocol):
    """Produces the candidates a report is about."""

    @property
    def name(self) -> str:
        """Stable identifier, recorded against every ingest run."""
        ...

    def load(self) -> list[Candidate]:
        """Fetch and parse. Raises SourceUnavailableError if it cannot."""
        ...


@runtime_checkable
class EnrichmentSource(Protocol):
    """Adds data to candidates another source produced."""

    @property
    def name(self) -> str:
        ...

    @property
    def required(self) -> bool:
        """Whether this source's failure fails the whole ingest.

        False for a genuinely supplemental source. Expressed as a property of
        the source rather than as a branch in the pipeline, so making a source
        mandatory is a change to that source and nothing else.
        """
        ...

    def load(self) -> Enrichment:
        ...
