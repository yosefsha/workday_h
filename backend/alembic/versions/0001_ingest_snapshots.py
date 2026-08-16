"""Ingest snapshots: runs, candidates and their employments.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "resume_feed_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "linkedin_feed_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    # Reads always ask for the newest successful run.
    op.create_index(
        "ix_ingest_run_status_started_at", "ingest_run", ["status", "started_at"]
    )

    op.create_table(
        "candidate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ingest_run_id",
            sa.Integer(),
            sa.ForeignKey("ingest_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("given_name", sa.String(length=255)),
        sa.Column("family_name", sa.String(length=255)),
        sa.Column("formatted_name", sa.String(length=512)),
        sa.Column("email", sa.String(length=320)),
        sa.Column("phone", sa.String(length=64)),
        sa.Column("linkedin_url", sa.String(length=1024)),
    )
    op.create_index("ix_candidate_ingest_run_id", "candidate", ["ingest_run_id"])

    op.create_table(
        "employment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidate.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=512)),
        # Nullable: an unparseable date does not discard the employment, it
        # suppresses that candidate's gap reporting. See docs/adr/0002.
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("location", sa.String(length=512)),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_employment_candidate_id", "employment", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_employment_candidate_id", table_name="employment")
    op.drop_table("employment")
    op.drop_index("ix_candidate_ingest_run_id", table_name="candidate")
    op.drop_table("candidate")
    op.drop_index("ix_ingest_run_status_started_at", table_name="ingest_run")
    op.drop_table("ingest_run")
