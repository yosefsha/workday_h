"""Per-source run status, replacing the hardcoded per-feed columns.

Sources are registered in app/wiring.py, so a schema that names them needs a
migration every time one is added. A row per source per run does not.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_source_status",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ingest_run_id",
            sa.Integer(),
            sa.ForeignKey("ingest_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # Null for a candidate source, and for one that failed before it could
        # match anything.
        sa.Column("matched", sa.Integer()),
        sa.Column("detail", sa.String(length=1024)),
    )
    op.create_index(
        "ix_ingest_source_status_ingest_run_id", "ingest_source_status", ["ingest_run_id"]
    )

    op.drop_column("ingest_run", "resume_feed_ok")
    op.drop_column("ingest_run", "linkedin_feed_ok")


def downgrade() -> None:
    false = sa.text("false")
    op.add_column(
        "ingest_run",
        sa.Column("linkedin_feed_ok", sa.Boolean(), nullable=False, server_default=false),
    )
    op.add_column(
        "ingest_run",
        sa.Column("resume_feed_ok", sa.Boolean(), nullable=False, server_default=false),
    )
    op.drop_index("ix_ingest_source_status_ingest_run_id", table_name="ingest_source_status")
    op.drop_table("ingest_source_status")
