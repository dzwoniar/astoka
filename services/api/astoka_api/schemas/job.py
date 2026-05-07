"""Job + SSE event schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from astoka_api.db.models.job import JobStatus, JobType


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_material_id: UUID
    job_type: JobType
    status: JobStatus
    progress: float
    progress_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    result: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JobUpdateEvent(BaseModel):
    """SSE payload — emitted whenever a job's status/progress changes."""

    event: str = "job_update"
    project_id: UUID
    source_material_id: UUID
    job_id: UUID
    job_type: str
    status: str
    progress: float
    progress_message: str | None = None
    error_message: str | None = None


class SourceMaterialReadyEvent(BaseModel):
    event: str = "source_material_ready"
    project_id: UUID
    source_material_id: UUID
    duration_s: float | None
    proxy_storage_key: str | None


class HighlightsReadyEvent(BaseModel):
    event: str = "highlights_ready"
    project_id: UUID
    source_material_id: UUID
    highlight_count: int = Field(ge=0)
