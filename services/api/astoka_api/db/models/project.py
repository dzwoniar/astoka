"""Project — top-level entity. Container for source materials, transcripts, clips, highlights."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astoka_api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from astoka_api.db.models.clip import Clip
    from astoka_api.db.models.source_material import SourceMaterial
    from astoka_api.db.models.user import User


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Per-project preferences (caption_style default, llm_provider, weights_overrides etc.)
    # Future-proof slot — Sprints 4 (highlight LLM toggle), 6 (caption styles), 8 (prompt mode).
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    owner: Mapped[User] = relationship("User", back_populates="projects")
    source_materials: Mapped[list[SourceMaterial]] = relationship(
        "SourceMaterial",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    clips: Mapped[list[Clip]] = relationship(
        "Clip",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project {self.name}>"
