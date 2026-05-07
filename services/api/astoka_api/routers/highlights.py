"""Highlights + transcripts endpoints (Phase C/D)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from astoka_api.auth.deps import CurrentUser
from astoka_api.db import get_session
from astoka_api.db.models import (
    Highlight,
    HighlightStatus,
    Project,
    SourceMaterial,
    Transcript,
)
from astoka_api.schemas.highlight import HighlightResponse, TranscriptResponse

router = APIRouter(tags=["highlights"])


async def _ensure_project_owner(
    db: AsyncSession, user_id: UUID, project_id: UUID
) -> Project:
    res = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = res.scalar_one_or_none()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


# === Transcripts ===


@router.get(
    "/source-materials/{source_material_id}/transcript",
    response_model=TranscriptResponse,
)
async def get_transcript(
    source_material_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Transcript:
    # Verify ownership through project chain.
    res = await db.execute(
        select(Transcript, Project)
        .join(SourceMaterial, Transcript.source_material_id == SourceMaterial.id)
        .join(Project, SourceMaterial.project_id == Project.id)
        .where(
            Transcript.source_material_id == source_material_id,
            Project.owner_id == user.id,
        )
        .order_by(Transcript.created_at.desc())
        .limit(1)
    )
    row = res.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    return row[0]


# === Highlights ===


@router.get(
    "/projects/{project_id}/highlights", response_model=list[HighlightResponse]
)
async def list_highlights_for_project(
    project_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
    include_archived: bool = False,
) -> list[HighlightResponse]:
    await _ensure_project_owner(db, user.id, project_id)

    stmt = (
        select(Highlight)
        .join(SourceMaterial, Highlight.source_material_id == SourceMaterial.id)
        .where(SourceMaterial.project_id == project_id)
        .order_by(Highlight.viral_score.desc())
    )
    if not include_archived:
        stmt = stmt.where(
            Highlight.status.in_([HighlightStatus.PENDING, HighlightStatus.ACCEPTED])
        )

    res = await db.execute(stmt)
    return [HighlightResponse.model_validate(h) for h in res.scalars().all()]


async def _set_highlight_status(
    db: AsyncSession, *, user_id: UUID, highlight_id: UUID, new_status: HighlightStatus
) -> Highlight:
    res = await db.execute(
        select(Highlight, Project)
        .join(SourceMaterial, Highlight.source_material_id == SourceMaterial.id)
        .join(Project, SourceMaterial.project_id == Project.id)
        .where(Highlight.id == highlight_id, Project.owner_id == user_id)
    )
    row = res.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Highlight not found")
    highlight: Highlight = row[0]
    highlight.status = new_status
    await db.flush()
    return highlight


@router.post("/highlights/{highlight_id}/accept", response_model=HighlightResponse)
async def accept_highlight(
    highlight_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Highlight:
    return await _set_highlight_status(
        db, user_id=user.id, highlight_id=highlight_id, new_status=HighlightStatus.ACCEPTED
    )


@router.post("/highlights/{highlight_id}/reject", response_model=HighlightResponse)
async def reject_highlight(
    highlight_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Highlight:
    return await _set_highlight_status(
        db, user_id=user.id, highlight_id=highlight_id, new_status=HighlightStatus.REJECTED
    )


@router.post("/highlights/{highlight_id}/hide", response_model=HighlightResponse)
async def hide_highlight(
    highlight_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Highlight:
    return await _set_highlight_status(
        db, user_id=user.id, highlight_id=highlight_id, new_status=HighlightStatus.HIDDEN
    )
