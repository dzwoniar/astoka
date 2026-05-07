"""Source material + ingest endpoints.

Routes:
  GET    /projects/{pid}/source-materials             list
  GET    /projects/{pid}/source-materials/{smid}      detail
  POST   /projects/{pid}/uploads/init                 presigned PUT URL
  POST   /projects/{pid}/uploads/complete             confirm + kick off pipeline
  POST   /projects/{pid}/youtube                      ingest YouTube URL
  GET    /projects/{pid}/jobs                         all jobs for project
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from astoka_api.auth.deps import CurrentUser
from astoka_api.db import get_session
from astoka_api.schemas.job import JobResponse
from astoka_api.schemas.source_material import (
    SourceMaterialResponse,
    UploadCompleteRequest,
    UploadInitRequest,
    UploadInitResponse,
    YouTubeIngestRequest,
)
from astoka_api.services import (
    job_service,
    project_service,
    source_material_service,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["ingest"])


async def _ensure_project(
    db: AsyncSession, user_id: UUID, project_id: UUID
) -> None:
    project = await project_service.get_project(
        db, owner_id=user_id, project_id=project_id
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.get("/source-materials", response_model=list[SourceMaterialResponse])
async def list_source_materials(
    project_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[SourceMaterialResponse]:
    await _ensure_project(db, user.id, project_id)
    items = await source_material_service.list_for_project(db, project_id=project_id)
    return [SourceMaterialResponse.model_validate(sm) for sm in items]


@router.get(
    "/source-materials/{source_material_id}", response_model=SourceMaterialResponse
)
async def get_source_material(
    project_id: UUID,
    source_material_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SourceMaterialResponse:
    await _ensure_project(db, user.id, project_id)
    sm = await source_material_service.get_for_project(
        db, project_id=project_id, source_material_id=source_material_id
    )
    if sm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source material not found")
    return SourceMaterialResponse.model_validate(sm)


@router.post(
    "/uploads/init",
    response_model=UploadInitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_init(
    project_id: UUID,
    body: UploadInitRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UploadInitResponse:
    project = await project_service.get_project(
        db, owner_id=user.id, project_id=project_id
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    # We need the actual ORM model for relationship access; project_service returns DTO.
    from sqlalchemy import select

    from astoka_api.db.models import Project as ProjectModel

    res = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project_model = res.scalar_one()

    sm, presigned = await source_material_service.create_upload_draft(
        db, project=project_model, filename=body.filename
    )
    return UploadInitResponse(
        source_material_id=sm.id,
        storage_key=sm.storage_key or "",
        presigned_put_url=presigned,
    )


@router.post("/uploads/complete", response_model=SourceMaterialResponse)
async def upload_complete(
    project_id: UUID,
    body: UploadCompleteRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SourceMaterialResponse:
    await _ensure_project(db, user.id, project_id)
    sm = await source_material_service.complete_upload(
        db,
        source_material_id=body.source_material_id,
        project_id=project_id,
        content_hash=body.content_hash,
    )
    if sm is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Upload not found in storage or wrong project",
        )
    return SourceMaterialResponse.model_validate(sm)


@router.post(
    "/youtube",
    response_model=SourceMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_youtube(
    project_id: UUID,
    body: YouTubeIngestRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SourceMaterialResponse:
    from sqlalchemy import select

    from astoka_api.db.models import Project as ProjectModel

    res = await db.execute(
        select(ProjectModel).where(
            ProjectModel.id == project_id, ProjectModel.owner_id == user.id
        )
    )
    project_model = res.scalar_one_or_none()
    if project_model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    sm = await source_material_service.create_youtube_job(
        db, project=project_model, youtube_url=str(body.url)
    )
    return SourceMaterialResponse.model_validate(sm)


@router.get("/jobs", response_model=list[JobResponse])
async def list_project_jobs(
    project_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[JobResponse]:
    await _ensure_project(db, user.id, project_id)
    jobs = await job_service.list_jobs_for_project(db, project_id=project_id)
    return [JobResponse.model_validate(j) for j in jobs]
