"""migrate all datetime columns to TIMESTAMPTZ

Why: 0001_initial originally created all timestamp columns as TIMESTAMP WITHOUT
TIME ZONE. Application code uses `datetime.now(UTC)` (tz-aware) when setting
manually-managed timestamps (last_login_at, archived_at, started_at, finished_at),
which collides with asyncpg's strict tz-aware vs naive check:

    can't subtract offset-naive and offset-aware datetimes

Fix: convert all 20 datetime columns to TIMESTAMP WITH TIME ZONE. Existing rows
keep their wall-clock values (`AT TIME ZONE 'UTC'` interprets naive as UTC).
Both 0001 (fresh installs) and this 0002 (existing DBs) end at the same schema.

Revision ID: 0002_timestamptz
Revises: 0001_initial
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_timestamptz"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Every datetime column in the schema. Listed explicitly so a deliberate diff in
# the future (drop/rename) shows up here too — no auto-discovery magic.
_TZ_COLUMNS: list[tuple[str, str]] = [
    # users
    ("users", "created_at"),
    ("users", "updated_at"),
    ("users", "last_login_at"),
    # projects
    ("projects", "created_at"),
    ("projects", "updated_at"),
    ("projects", "archived_at"),
    # source_materials
    ("source_materials", "created_at"),
    ("source_materials", "updated_at"),
    # transcripts
    ("transcripts", "created_at"),
    ("transcripts", "updated_at"),
    # highlights
    ("highlights", "created_at"),
    ("highlights", "updated_at"),
    # clips
    ("clips", "created_at"),
    ("clips", "updated_at"),
    # edit_operations
    ("edit_operations", "created_at"),
    ("edit_operations", "updated_at"),
    # jobs
    ("jobs", "created_at"),
    ("jobs", "updated_at"),
    ("jobs", "started_at"),
    ("jobs", "finished_at"),
]


def upgrade() -> None:
    for table, column in _TZ_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column in _TZ_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
