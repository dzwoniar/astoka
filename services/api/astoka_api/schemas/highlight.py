"""Highlight schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from astoka_api.db.models.highlight import HighlightStatus


class HighlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_material_id: UUID
    start_s: float
    end_s: float
    audio_corrected: bool
    viral_score: int
    confidence: float | None
    typology: str | None
    hook_sentence: str | None
    virality_reason: str | None
    suggested_title: str | None
    llm_provider: str
    feature_scores: dict[str, Any]
    status: HighlightStatus
    created_at: datetime
    updated_at: datetime


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_material_id: UUID
    language: str
    model_id: str
    alignment_method: str
    full_text: str
    segments_json: list[dict[str, Any]]
    avg_confidence: float | None
    created_at: datetime
