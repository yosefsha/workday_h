"""Reading and writing ingest snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Connection, Engine, insert, select

from app.domain.candidate import Candidate, Employment, PersonName
from app.sources.protocols import SourceStatus
from app.store.tables import (
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    candidate,
    employment,
    ingest_run,
    ingest_source_status,
)


def _insert_statuses(
    connection: Connection, run_id: int, statuses: Sequence[SourceStatus]
) -> None:
    if not statuses:
        return
    connection.execute(
        insert(ingest_source_status),
        [
            {
                "ingest_run_id": run_id,
                "source_name": status.name,
                "ok": status.ok,
                "matched": status.matched,
                "detail": status.detail,
            }
            for status in statuses
        ],
    )


class SnapshotRepository:
    """The only thing in the application that talks SQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_snapshot(
        self,
        candidates: list[Candidate],
        *,
        started_at: datetime,
        statuses: Sequence[SourceStatus],
    ) -> int:
        """Write a successful run and everything it produced, atomically.

        One transaction: a run that fails halfway leaves no rows behind and no
        half-written snapshot for a reader to find.
        """
        with self._engine.begin() as connection:
            run_id = connection.execute(
                insert(ingest_run)
                .values(
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    status=STATUS_SUCCEEDED,
                )
                .returning(ingest_run.c.id)
            ).scalar_one()

            _insert_statuses(connection, run_id, statuses)

            for person in candidates:
                candidate_id = connection.execute(
                    insert(candidate)
                    .values(
                        ingest_run_id=run_id,
                        given_name=person.name.given_name,
                        family_name=person.name.family_name,
                        formatted_name=person.name.formatted_name,
                        email=person.email,
                        phone=person.phone,
                        linkedin_url=person.linkedin_url,
                    )
                    .returning(candidate.c.id)
                ).scalar_one()

                rows = [
                    {
                        "candidate_id": candidate_id,
                        "ordinal": ordinal,
                        "role": job.role,
                        "start_date": job.start_date,
                        "end_date": job.end_date,
                        "location": job.location,
                        "is_current": job.is_current,
                    }
                    for ordinal, job in enumerate(person.employments)
                ]
                if rows:
                    connection.execute(insert(employment), rows)

        return run_id

    def record_failed_run(self, *, started_at: datetime, statuses: Sequence[SourceStatus]) -> None:
        """Leave a trace of a run that could not complete.

        Without this, an outage is indistinguishable from nobody having tried.
        The per-source rows say which source was the one that stopped it.
        """
        with self._engine.begin() as connection:
            run_id = connection.execute(
                insert(ingest_run)
                .values(
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    status=STATUS_FAILED,
                )
                .returning(ingest_run.c.id)
            ).scalar_one()

            _insert_statuses(connection, run_id, statuses)

    def latest_source_statuses(self) -> list[SourceStatus]:
        """What each source did during the most recent successful run."""
        run_id = self.latest_successful_run_id()
        if run_id is None:
            return []

        with self._engine.connect() as connection:
            rows = connection.execute(
                select(ingest_source_status)
                .where(ingest_source_status.c.ingest_run_id == run_id)
                .order_by(ingest_source_status.c.id)
            ).all()

        return [
            SourceStatus(name=row.source_name, ok=row.ok, matched=row.matched, detail=row.detail)
            for row in rows
        ]

    def latest_successful_run_id(self) -> int | None:
        with self._engine.connect() as connection:
            return connection.execute(
                select(ingest_run.c.id)
                .where(ingest_run.c.status == STATUS_SUCCEEDED)
                .order_by(ingest_run.c.started_at.desc(), ingest_run.c.id.desc())
                .limit(1)
            ).scalar_one_or_none()

    def latest_candidates(self) -> list[Candidate]:
        """Every candidate from the most recent successful run.

        Returns an empty list when no run has succeeded yet — the caller
        decides whether that means "ingest first" or "genuinely nobody".
        """
        run_id = self.latest_successful_run_id()
        if run_id is None:
            return []

        with self._engine.connect() as connection:
            candidate_rows = connection.execute(
                select(candidate)
                .where(candidate.c.ingest_run_id == run_id)
                .order_by(candidate.c.id)
            ).all()

            employment_rows = connection.execute(
                select(employment)
                .join(candidate, employment.c.candidate_id == candidate.c.id)
                .where(candidate.c.ingest_run_id == run_id)
                .order_by(employment.c.candidate_id, employment.c.ordinal)
            ).all()

        jobs: dict[int, list[Employment]] = {}
        for row in employment_rows:
            jobs.setdefault(row.candidate_id, []).append(
                Employment(
                    role=row.role,
                    start_date=row.start_date,
                    end_date=row.end_date,
                    location=row.location,
                    is_current=row.is_current,
                )
            )

        return [
            Candidate(
                name=PersonName(
                    given_name=row.given_name,
                    family_name=row.family_name,
                    formatted_name=row.formatted_name,
                ),
                email=row.email,
                phone=row.phone,
                linkedin_url=row.linkedin_url,
                employments=tuple(jobs.get(row.id, [])),
            )
            for row in candidate_rows
        ]
