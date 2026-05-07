"""initial schema — full MVP (Sprint 1 Demo Backbone)

Schema designed to hold all Sprint 1-7 features without later migration churn.
Some columns are nullable / pre-populated for features that come in later sprints
(reframe_config, captions_style, render_storage_key, user_corrections, etc.).

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # === users ===
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # === projects ===
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_projects_owner_id_users"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client", sa.String(100), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    # === source_materials ===
    source_type_enum = postgresql.ENUM("upload", "youtube", name="source_type")
    source_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "source_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                ondelete="CASCADE",
                name="fk_source_materials_project_id_projects",
            ),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            postgresql.ENUM("upload", "youtube", name="source_type", create_type=False),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(512), nullable=True),
        sa.Column("youtube_url", sa.String(2048), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("proxy_storage_key", sa.String(512), nullable=True),
        sa.Column("thumbnail_storage_key", sa.String(512), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("bytes_size", sa.BigInteger(), nullable=True),
        sa.Column("detected_language", sa.String(8), nullable=True),
        sa.Column("audio_streams", sa.Integer(), nullable=True),
        sa.Column(
            "extra_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_source_materials_project_id", "source_materials", ["project_id"])
    op.create_index(
        "ix_source_materials_content_hash", "source_materials", ["content_hash"]
    )
    op.create_index(
        "uq_source_materials_storage_key", "source_materials", ["storage_key"], unique=True
    )

    # === transcripts ===
    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "source_material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "source_materials.id",
                ondelete="CASCADE",
                name="fk_transcripts_source_material_id_source_materials",
            ),
            nullable=False,
        ),
        sa.Column("language", sa.String(8), nullable=False, server_default="pl"),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column(
            "alignment_method",
            sa.String(64),
            nullable=False,
            server_default="faster_whisper_word_timestamps",
        ),
        sa.Column("full_text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "segments_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "user_corrections",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("avg_confidence", sa.Float(), nullable=True),
    )
    op.create_index("ix_transcripts_source_material_id", "transcripts", ["source_material_id"])

    # === highlights ===
    highlight_status_enum = postgresql.ENUM(
        "pending", "accepted", "rejected", "hidden", name="highlight_status"
    )
    highlight_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "highlights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "source_material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "source_materials.id",
                ondelete="CASCADE",
                name="fk_highlights_source_material_id_source_materials",
            ),
            nullable=False,
        ),
        sa.Column("start_s", sa.Float(), nullable=False),
        sa.Column("end_s", sa.Float(), nullable=False),
        sa.Column("audio_corrected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("viral_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("typology", sa.String(32), nullable=True),
        sa.Column("hook_sentence", sa.Text(), nullable=True),
        sa.Column("virality_reason", sa.Text(), nullable=True),
        sa.Column("suggested_title", sa.String(255), nullable=True),
        sa.Column("llm_provider", sa.String(64), nullable=False),
        sa.Column(
            "edit_suggestions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "feature_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "accepted",
                "rejected",
                "hidden",
                name="highlight_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index("ix_highlights_source_material_id", "highlights", ["source_material_id"])
    op.create_index("ix_highlights_status", "highlights", ["status"])

    # === clips ===
    op.create_table(
        "clips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id", ondelete="CASCADE", name="fk_clips_project_id_projects"
            ),
            nullable=False,
        ),
        sa.Column(
            "highlight_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "highlights.id", ondelete="SET NULL", name="fk_clips_highlight_id_highlights"
            ),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("start_s", sa.Float(), nullable=False),
        sa.Column("end_s", sa.Float(), nullable=False),
        sa.Column("aspect_ratio", sa.String(8), nullable=False, server_default="9:16"),
        sa.Column(
            "reframe_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("captions_style", sa.String(64), nullable=True),
        sa.Column(
            "captions_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("render_storage_key", sa.String(512), nullable=True),
        sa.Column("render_duration_s", sa.Float(), nullable=True),
        sa.Column("render_bytes_size", sa.Integer(), nullable=True),
        sa.Column("render_status", sa.String(32), nullable=False, server_default="pending"),
    )
    op.create_index("ix_clips_project_id", "clips", ["project_id"])
    op.create_index("ix_clips_highlight_id", "clips", ["highlight_id"])

    # === edit_operations ===
    op.create_table(
        "edit_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "clip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "clips.id", ondelete="CASCADE", name="fk_edit_operations_clip_id_clips"
            ),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("op_type", sa.String(64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_undone", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_edit_operations_clip_id", "edit_operations", ["clip_id"])

    # === jobs ===
    job_type_enum = postgresql.ENUM(
        "youtube_download",
        "probe",
        "proxy_preview",
        "asr",
        "highlight",
        "render",
        name="job_type",
    )
    job_type_enum.create(op.get_bind(), checkfirst=True)

    job_status_enum = postgresql.ENUM(
        "pending", "running", "succeeded", "failed", "cancelled", name="job_status"
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "source_material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "source_materials.id",
                ondelete="CASCADE",
                name="fk_jobs_source_material_id_source_materials",
            ),
            nullable=False,
        ),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column(
            "job_type",
            postgresql.ENUM(
                "youtube_download",
                "probe",
                "proxy_preview",
                "asr",
                "highlight",
                "render",
                name="job_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "running",
                "succeeded",
                "failed",
                "cancelled",
                name="job_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("progress_message", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_jobs_source_material_id", "jobs", ["source_material_id"])
    op.create_index("ix_jobs_celery_task_id", "jobs", ["celery_task_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("edit_operations")
    op.drop_table("clips")
    op.drop_table("highlights")
    op.drop_table("transcripts")
    op.drop_table("source_materials")
    op.drop_table("projects")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in ("job_status", "job_type", "highlight_status", "source_type"):
        bind.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
