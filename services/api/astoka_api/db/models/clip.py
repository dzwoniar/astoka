"""Clip — accepted highlight that will be (eventually) rendered to MP4.

In Sprint 1 (Demo Backbone) clips exist as records but render pipeline is NOT wired
— that's Sprint 5 (Render). Schema fields below are pre-populated to avoid migration
churn when render lands.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astoka_api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from astoka_api.db.models.edit_operation import EditOperation
    from astoka_api.db.models.project import Project


class Clip(Base, TimestampMixin):
    __tablename__ = "clips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Optional link to highlight from which this clip was promoted (NULL for prompt-mode clips).
    highlight_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("highlights.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Time window in source seconds.
    start_s: Mapped[float] = mapped_column(Float, nullable=False)
    end_s: Mapped[float] = mapped_column(Float, nullable=False)

    # === Render config (used Sprint 5+) ===
    aspect_ratio: Mapped[str] = mapped_column(String(8), nullable=False, default="9:16")
    reframe_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    captions_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    captions_overrides: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # === Render output (filled by Sprint 5 render task) ===
    render_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    render_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    render_bytes_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 'pending' | 'rendering' | 'rendered' | 'failed'
    render_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    project: Mapped[Project] = relationship("Project", back_populates="clips")
    edit_operations: Mapped[list[EditOperation]] = relationship(
        "EditOperation", back_populates="clip", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Clip {self.id} {self.aspect_ratio}>"
