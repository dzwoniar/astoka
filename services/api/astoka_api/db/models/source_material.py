"""SourceMaterial — uploaded file or YouTube download. Owns transcripts + highlights."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astoka_api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from astoka_api.db.models.highlight import Highlight
    from astoka_api.db.models.job import Job
    from astoka_api.db.models.project import Project
    from astoka_api.db.models.transcript import Transcript


class SourceType(enum.StrEnum):
    UPLOAD = "upload"
    YOUTUBE = "youtube"


class SourceMaterial(Base, TimestampMixin):
    __tablename__ = "source_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"), nullable=False
    )

    # === Identity / origin ===
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # === Storage ===
    # MinIO object key for the original (uploaded or downloaded). Null until ingest done.
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True, unique=True)
    proxy_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # SHA-256 of original bytes — drives ASR/transcript dedup (PRD ASR-07, INGEST-cache).
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # === Probed metadata (filled by ffprobe) ===
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    bytes_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    audio_streams: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Catch-all for ffprobe extras + yt-dlp metadata (uploader, title, view count etc.)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    project: Mapped[Project] = relationship("Project", back_populates="source_materials")
    transcripts: Mapped[list[Transcript]] = relationship(
        "Transcript", back_populates="source_material", cascade="all, delete-orphan"
    )
    highlights: Mapped[list[Highlight]] = relationship(
        "Highlight", back_populates="source_material", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[Job]] = relationship(
        "Job", back_populates="source_material", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SourceMaterial {self.id} {self.source_type.value}>"
