"""Source material + ingest schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from astoka_api.db.models.source_material import SourceType


class UploadInitRequest(BaseModel):
    """Body for POST /projects/{id}/uploads/init."""

    filename: str = Field(min_length=1, max_length=512)
    content_type: str | None = None
    bytes_size: int | None = Field(default=None, ge=0)


class UploadInitResponse(BaseModel):
    source_material_id: UUID
    storage_key: str
    presigned_put_url: str


class UploadCompleteRequest(BaseModel):
    """Body for POST /projects/{id}/uploads/complete."""

    source_material_id: UUID
    content_hash: str | None = Field(default=None, max_length=64)


class YouTubeIngestRequest(BaseModel):
    """Body for POST /projects/{id}/youtube."""

    url: HttpUrl


class SourceMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_type: SourceType
    original_filename: str | None
    youtube_url: str | None
    storage_key: str | None
    proxy_storage_key: str | None
    thumbnail_storage_key: str | None
    duration_s: float | None
    width: int | None
    height: int | None
    fps: float | None
    bytes_size: int | None
    detected_language: str | None
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
