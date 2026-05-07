"""Project CRUD service — owns DB queries for projects."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from astoka_api.db.models import Clip, Project, SourceMaterial
from astoka_api.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

SortField = Literal["updated_at", "created_at", "name", "client"]
ArchiveFilter = Literal["all", "active", "archived"]


def _project_to_response(project: Project, sm_count: int, clips_count: int) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        client=project.client,
        is_archived=project.is_archived,
        archived_at=project.archived_at,
        settings=project.settings,
        created_at=project.created_at,
        updated_at=project.updated_at,
        source_materials_count=sm_count,
        clips_count=clips_count,
    )


async def list_projects(
    db: AsyncSession,
    *,
    owner_id: UUID,
    sort_by: SortField = "updated_at",
    sort_desc: bool = True,
    archive_filter: ArchiveFilter = "active",
) -> tuple[list[ProjectResponse], int]:
    """Return projects + total count for current user, with sort + archive filter.

    Counts of source_materials and clips are computed via subqueries so callers
    don't need to load relationships eagerly.
    """
    sm_count_subq = (
        select(func.count(SourceMaterial.id))
        .where(SourceMaterial.project_id == Project.id)
        .scalar_subquery()
    )
    clips_count_subq = (
        select(func.count(Clip.id))
        .where(Clip.project_id == Project.id)
        .scalar_subquery()
    )

    stmt = select(Project, sm_count_subq, clips_count_subq).where(
        Project.owner_id == owner_id
    )

    if archive_filter == "active":
        stmt = stmt.where(Project.is_archived.is_(False))
    elif archive_filter == "archived":
        stmt = stmt.where(Project.is_archived.is_(True))

    sort_column = {
        "updated_at": Project.updated_at,
        "created_at": Project.created_at,
        "name": Project.name,
        "client": Project.client,
    }[sort_by]
    stmt = stmt.order_by(sort_column.desc() if sort_desc else sort_column.asc())

    result = await db.execute(stmt)
    rows = result.all()

    items = [_project_to_response(p, sm, cl) for p, sm, cl in rows]
    return items, len(items)


async def create_project(
    db: AsyncSession, *, owner_id: UUID, body: ProjectCreate
) -> ProjectResponse:
    project = Project(
        owner_id=owner_id,
        name=body.name,
        client=body.client,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return _project_to_response(project, 0, 0)


async def get_project(
    db: AsyncSession, *, owner_id: UUID, project_id: UUID
) -> ProjectResponse | None:
    stmt = (
        select(Project)
        .where(Project.id == project_id, Project.owner_id == owner_id)
        .options(
            selectinload(Project.source_materials),
            selectinload(Project.clips),
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        return None
    return _project_to_response(
        project,
        len(project.source_materials),
        len(project.clips),
    )


async def update_project(
    db: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
    body: ProjectUpdate,
) -> ProjectResponse | None:
    stmt = select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        return None

    if body.name is not None:
        project.name = body.name
    if body.client is not None:
        project.client = body.client
    if body.settings is not None:
        project.settings = body.settings

    await db.flush()
    await db.refresh(project)
    sm_count, clips_count = await _counts(db, project_id)
    return _project_to_response(project, sm_count, clips_count)


async def archive_project(
    db: AsyncSession, *, owner_id: UUID, project_id: UUID
) -> ProjectResponse | None:
    """Soft-delete: set is_archived + archived_at. PRD PROJ-06 (30-day retention)."""
    stmt = select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        return None

    project.is_archived = True
    project.archived_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(project)
    sm_count, clips_count = await _counts(db, project_id)
    return _project_to_response(project, sm_count, clips_count)


async def restore_project(
    db: AsyncSession, *, owner_id: UUID, project_id: UUID
) -> ProjectResponse | None:
    stmt = select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        return None

    project.is_archived = False
    project.archived_at = None
    await db.flush()
    await db.refresh(project)
    sm_count, clips_count = await _counts(db, project_id)
    return _project_to_response(project, sm_count, clips_count)


async def delete_project_hard(
    db: AsyncSession, *, owner_id: UUID, project_id: UUID
) -> bool:
    """Hard delete with confirmation — PRD PROJ-07. CASCADE handles dependents."""
    stmt = select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        return False
    await db.delete(project)
    return True


async def _counts(db: AsyncSession, project_id: UUID) -> tuple[int, int]:
    sm_stmt = select(func.count(SourceMaterial.id)).where(
        SourceMaterial.project_id == project_id
    )
    cl_stmt = select(func.count(Clip.id)).where(Clip.project_id == project_id)
    sm_count = (await db.execute(sm_stmt)).scalar_one()
    cl_count = (await db.execute(cl_stmt)).scalar_one()
    return int(sm_count), int(cl_count)
