"""The one implementation of "go and read the sources".

Both entry points call this: the CLI constructs it in-process, and POST /ingest
constructs the same object. There is no second copy of this logic and no HTTP
hop between the CLI and the work it does.

Nothing here names a specific feed. The service is handed one CandidateSource
and any number of EnrichmentSources and loops over them, so adding a source is
a new class plus one line in app/wiring.py.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.candidate import Candidate
from app.sources.protocols import (
    CandidateSource,
    EnrichmentSource,
    SourceStatus,
    SourceUnavailableError,
)
from app.store.repository import SnapshotRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    run_id: int
    candidate_count: int
    statuses: tuple[SourceStatus, ...]


class IngestService:
    def __init__(
        self,
        *,
        candidate_source: CandidateSource,
        enrichments: Sequence[EnrichmentSource],
        repository: SnapshotRepository,
    ) -> None:
        self._candidate_source = candidate_source
        self._enrichments = tuple(enrichments)
        self._repository = repository

    def run(self) -> IngestResult:
        """Read every source, join them, and persist the result as one snapshot.

        The candidate source is the report — without it there is nothing to
        say, so its failure fails the run. Each enrichment is asked whether its
        own failure is fatal (`required`), and by default it is not: the run
        proceeds, that source's contribution is missing, and the run records
        that it was unreachable so the absence is not mistaken for "matched
        nobody".
        """
        started_at = datetime.now(UTC)
        statuses: list[SourceStatus] = []

        try:
            candidates = self._candidate_source.load()
        except SourceUnavailableError as error:
            statuses.append(
                SourceStatus(name=self._candidate_source.name, ok=False, detail=str(error))
            )
            self._repository.record_failed_run(started_at=started_at, statuses=statuses)
            raise

        statuses.append(SourceStatus(name=self._candidate_source.name, ok=True))

        for source in self._enrichments:
            candidates, status = self._apply(source, candidates)
            statuses.append(status)
            if not status.ok and source.required:
                self._repository.record_failed_run(started_at=started_at, statuses=statuses)
                raise SourceUnavailableError(
                    f"required source {source.name!r} unavailable: {status.detail}"
                )

        run_id = self._repository.save_snapshot(
            candidates, started_at=started_at, statuses=statuses
        )

        logger.info(
            "ingest run %d stored %d candidates from %d sources",
            run_id,
            len(candidates),
            len(statuses),
        )
        return IngestResult(
            run_id=run_id,
            candidate_count=len(candidates),
            statuses=tuple(statuses),
        )

    def _apply(
        self, source: EnrichmentSource, candidates: list[Candidate]
    ) -> tuple[list[Candidate], SourceStatus]:
        """Load one enrichment and apply it, or report why it could not be.

        A failing optional source leaves the candidates untouched and returns a
        failed status. It never raises here — whether that is fatal is the
        caller's decision, based on `source.required`.
        """
        try:
            enrichment = source.load()
        except SourceUnavailableError as error:
            logger.warning("source %r unavailable, contribution omitted: %s", source.name, error)
            return candidates, SourceStatus(name=source.name, ok=False, detail=str(error))

        outcome = enrichment.apply(candidates)
        logger.info(
            "source %r matched %d of %d candidates",
            source.name,
            outcome.matched,
            len(candidates),
        )
        return outcome.candidates, SourceStatus(
            name=source.name, ok=True, matched=outcome.matched
        )
