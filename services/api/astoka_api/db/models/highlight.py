"""Highlight — single propose clip from heuristic+LLM scoring.

Schema is RESEARCH §4 — typology + hook_sentence + virality_reason + confidence.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astoka_api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from astoka_api.db.models.source_material import SourceMaterial


class HighlightStatus(enum.StrEnum):
    PENDING = "pending"  # newly generated, awaiting user review
    ACCEPTED = "accepted"  # user accepted, will be rendered later
    REJECTED = "rejected"  # user rejected, hidden from main view but kept in archive
    HIDDEN = "hidden"  # user hid (soft state, distinct from explicit reject)


class Highlight(Base, TimestampMixin):
    __tablename__ = "highlights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Time window in source material seconds (post audio-correction, RESEARCH §3).
    start_s: Mapped[float] = mapped_column(Float, nullable=False)
    end_s: Mapped[float] = mapped_column(Float, nullable=False)
    audio_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Score 0..100. Either from LLM rerank or pure heuristic (when fallback active).
    viral_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # Confidence 0..1 from LLM (PRD HIGH-05, RESEARCH §4).
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # RESEARCH §4 typology — one of: opinion_bomb | hook_moment | story_peak |
    # practical_value | revelation | comedy_punch.
    typology: Mapped[str | None] = mapped_column(String(32), nullable=True)

    hook_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    virality_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 'ollama_llama3.3:8b' | 'heuristic_fallback' | 'openai_gpt-4o-mini' (HIGH-08)
    llm_provider: Mapped[str] = mapped_column(String(64), nullable=False)

    # LLM-suggested edits (filler removal hints, pause trims) — used in Sprint 2.
    edit_suggestions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Per-feature scoring breakdown (audio energy, scene density, face presence)
    # — useful for debugging + Sprint 7 calibration.
    feature_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    status: Mapped[HighlightStatus] = mapped_column(
        Enum(HighlightStatus, name="highlight_status"),
        nullable=False,
        default=HighlightStatus.PENDING,
        index=True,
    )

    source_material: Mapped[SourceMaterial] = relationship(
        "SourceMaterial", back_populates="highlights"
    )

    def __repr__(self) -> str:
        return f"<Highlight {self.id} score={self.viral_score} status={self.status.value}>"
