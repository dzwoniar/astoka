"""Projects router — CRUD + sort + filter + soft-delete + restore + hard-delete.

Maps to PRD PROJ-01..08. All routes require auth (owner-scoped).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from astoka_api.auth.deps import CurrentUser
from astoka_api.db import get_session
from astoka_api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from astoka_api.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
    sort_by: Annotated[
        project_service.SortField, Query(description="Field to sort by")
    ] = "updated_at",
    sort_desc: Annotated[bool, Query(description="Descending order (default true)")] = True,
    archive_filter: Annotated[
        project_service.ArchiveFilter, Query(description="all | active | archived")
    ] = "active",
) -> ProjectListResponse:
    items, total = await project_service.list_projects(
        db,
        owner_id=user.id,
        sort_by=sort_by,
        sort_desc=sort_desc,
        archive_filter=archive_filter,
    )
    return ProjectListResponse(items=items, total=total)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    return await project_service.create_project(db, owner_id=user.id, body=body)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    project = await project_service.get_project(db, owner_id=user.id, project_id=project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    project = await project_service.update_project(
        db, owner_id=user.id, project_id=project_id, body=body
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{project_id}", response_model=ProjectResponse)
async def archive_project(
    project_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    """Soft-delete: archive (PRD PROJ-06)."""
    project = await project_service.archive_project(
        db, owner_id=user.id, project_id=project_id
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    project = await project_service.restore_project(
        db, owner_id=user.id, project_id=project_id
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{project_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_project(
    project_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """PRD PROJ-07 — permanent delete. Confirmation enforced client-side."""
    deleted = await project_service.delete_project_hard(
        db, owner_id=user.id, project_id=project_id
    )
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
