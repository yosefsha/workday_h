"""The persisted schema.

Each ingest is a snapshot: candidates belong to the run that produced them and
are never updated in place, so a partial run cannot half-overwrite good data
and the history of what the feeds said is kept.

Dates are stored as DATE rather than as the `Jan/01/2008` wire string. The wire
format is a rendering concern, `Sep/5/2016` and `Sep/05/2016` must land on the
same row, and gap questions stay queries rather than a full re-parse.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    text,
)

metadata = MetaData()

STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

ingest_run = Table(
    "ingest_run",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", String(16), nullable=False),
)

# One row per source per run. A table rather than a column per source, because
# sources are registered in app/wiring.py and a schema that names them would
# need a migration every time one is added.
#
# This is how you tell "the source ran and matched nobody" from "the source
# was unreachable" — a distinction a NULL linkedin_url cannot carry on its own.
ingest_source_status = Table(
    "ingest_source_status",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "ingest_run_id",
        ForeignKey("ingest_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("source_name", String(64), nullable=False),
    Column("ok", Boolean, nullable=False, server_default=text("false")),
    # Null for a source that produces candidates rather than enriching them,
    # and for one that failed before it could match anything.
    Column("matched", Integer),
    Column("detail", String(1024)),
)

candidate = Table(
    "candidate",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "ingest_run_id",
        ForeignKey("ingest_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("given_name", String(255)),
    Column("family_name", String(255)),
    Column("formatted_name", String(512)),
    Column("email", String(320)),
    Column("phone", String(64)),
    Column("linkedin_url", String(1024)),
)

employment = Table(
    "employment",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "candidate_id",
        ForeignKey("candidate.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    # Feed order, kept only so a snapshot round-trips faithfully. Reporting
    # order is derived by sorting on dates, never from this column.
    Column("ordinal", Integer, nullable=False),
    Column("role", String(512)),
    Column("start_date", Date),
    Column("end_date", Date),
    Column("location", String(512)),
    Column("is_current", Boolean, nullable=False, server_default=text("false")),
)
