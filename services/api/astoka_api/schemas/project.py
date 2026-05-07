"""Project request/response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client: str | None = Field(default=None, max_length=100)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    client: str | None = Field(default=None, max_length=100)
    settings: dict[str, Any] | None = None


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    is_archived: bool
    archived_at: datetime | None
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    # Counts populated from relationships in service layer.
    source_materials_count: int = 0
    clips_count: int = 0


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
