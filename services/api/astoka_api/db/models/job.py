"""Job — tracks a single async pipeline step (download, probe, asr, highlight, render).

State machine drives the SSE event stream (Phase B.4). One source material has many jobs;
job sequences form a Celery chain (orchestrator).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astoka_api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from astoka_api.db.models.source_material import SourceMaterial


class JobType(str, enum.Enum):
    YOUTUBE_DOWNLOAD = "youtube_download"
    PROBE = "probe"
    PROXY_PREVIEW = "proxy_preview"
    ASR = "asr"
    HIGHLIGHT = "highlight"
    RENDER = "render"  # Sprint 5+


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Celery task ID (for Flower / cancellation).
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    job_type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )

    # 0.0..1.0 — drives UI progress bar.
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Free-form short message: "Pobieram model... 60%", "Transkrybuję chunk 3/5".
    progress_message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-job result/output payload (e.g. transcript_id, highlight_count).
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    source_material: Mapped[SourceMaterial] = relationship(
        "SourceMaterial", back_populates="jobs"
    )

    def __repr__(self) -> str:
        return f"<Job {self.job_type.value} {self.status.value} {self.progress:.0%}>"
