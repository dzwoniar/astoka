"""Transcript — ASR output for one source material.

Schema in `segments_json` matches PRD ASR-03:
  segments: [{ text, start, end, words: [{text, start, end, confidence}] }]
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astoka_api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from astoka_api.db.models.source_material import SourceMaterial


class Transcript(Base, TimestampMixin):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    language: Mapped[str] = mapped_column(String(8), nullable=False, default="pl")
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Whether timestamps came from faster-whisper word_timestamps (Sprint 1)
    # or from WhisperX wav2vec2 alignment (future Sprint 4 captions upgrade).
    alignment_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="faster_whisper_word_timestamps"
    )

    # Compact searchable plain text (joined segments) — for grep/search later.
    full_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Full structured transcript (PRD ASR-03 schema).
    segments_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # User edits to text (Sprint 2 EDIT-XX). Empty in Sprint 1.
    user_corrections: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Best-effort confidence average across all words (0..1).
    avg_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    source_material: Mapped[SourceMaterial] = relationship(
        "SourceMaterial", back_populates="transcripts"
    )

    def __repr__(self) -> str:
        return f"<Transcript {self.id} model={self.model_id}>"
