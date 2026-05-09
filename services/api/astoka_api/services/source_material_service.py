"""Source material lifecycle: create draft, complete upload, kick off pipeline."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from astoka_api.db.models import (
    Job,
    JobType,
    Project,
    SourceMaterial,
    SourceType,
)
from astoka_api.services import job_service, storage_service


async def create_upload_draft(
    db: AsyncSession,
    *,
    project: Project,
    filename: str,
) -> tuple[SourceMaterial, str]:
    """Create draft + return (source_material, presigned PUT URL).

    Caller (web) PUTs the file to the URL, then calls /uploads/complete to
    register hash + kick off pipeline. We pre-allocate the storage_key here.
    """
    sm = SourceMaterial(
        project_id=project.id,
        source_type=SourceType.UPLOAD,
        original_filename=filename,
    )
    db.add(sm)
    await db.flush()

    sm.storage_key = storage_service.storage_key_for_source(str(sm.id), filename)
    await db.flush()

    presigned = storage_service.presign_upload_url(sm.storage_key)
    return sm, presigned


async def complete_upload(
    db: AsyncSession,
    *,
    source_material_id: UUID,
    project_id: UUID,
    content_hash: str | None,
) -> SourceMaterial | None:
    """Mark upload complete + kick off probe job.

    Verifies upload actually arrived in MinIO. Returns None if not found or wrong project.
    """
    res = await db.execute(
        select(SourceMaterial).where(
            SourceMaterial.id == source_material_id,
            SourceMaterial.project_id == project_id,
        )
    )
    sm = res.scalar_one_or_none()
    if sm is None:
        return None

    if not sm.storage_key or not storage_service.object_exists(sm.storage_key):
        return None

    if content_hash:
        sm.content_hash = content_hash

    # Worker imports lazy to avoid CI/test coupling.
    await _enqueue_probe(db, sm)
    return sm


async def create_youtube_job(
    db: AsyncSession,
    *,
    project: Project,
    youtube_url: str,
) -> SourceMaterial:
    """Register source material from YouTube URL + kick off download job."""
    sm = SourceMaterial(
        project_id=project.id,
        source_type=SourceType.YOUTUBE,
        youtube_url=youtube_url,
    )
    db.add(sm)
    await db.flush()

    await _enqueue_youtube_download(db, sm)
    return sm


async def _enqueue_probe(db: AsyncSession, sm: SourceMaterial) -> Job:
    """Add probe job + signal worker via Celery.

    CRITICAL: we COMMIT before calling .delay() — the worker runs in a separate
    process/connection and will SELECT the Job row by id. If we only flush, the
    row is visible to this session but not yet to the worker, and the task starts
    instantly (Redis broker is fast). The commit guarantees the row is durable
    and visible to all connections before the task message reaches the worker.
    """
    job = await job_service.create_job(
        db,
        source_material_id=sm.id,
        job_type=JobType.PROBE,
    )
    await db.commit()  # job + sm now durable & visible to worker DB connection
    # Lazy import to avoid pulling celery in tests.
    try:
        from astoka_worker.tasks.probe import probe_metadata

        result = probe_metadata.delay(str(sm.id), str(job.id))
        job.celery_task_id = result.id
        await db.commit()
    except ImportError:
        # Worker not installed in this env (e.g. tests) — leave job pending.
        pass
    return job


async def _enqueue_youtube_download(db: AsyncSession, sm: SourceMaterial) -> Job:
    """Same commit-before-delay pattern as _enqueue_probe — see its docstring."""
    job = await job_service.create_job(
        db,
        source_material_id=sm.id,
        job_type=JobType.YOUTUBE_DOWNLOAD,
    )
    await db.commit()  # see _enqueue_probe note
    try:
        from astoka_worker.tasks.ingest_youtube import download_youtube

        result = download_youtube.delay(str(sm.id), str(job.id))
        job.celery_task_id = result.id
        await db.commit()
    except ImportError:
        pass
    return job


async def list_for_project(
    db: AsyncSession, *, project_id: UUID
) -> list[SourceMaterial]:
    res = await db.execute(
        select(SourceMaterial)
        .where(SourceMaterial.project_id == project_id)
        .order_by(SourceMaterial.created_at.desc())
    )
    return list(res.scalars().all())


async def get_for_project(
    db: AsyncSession, *, project_id: UUID, source_material_id: UUID
) -> SourceMaterial | None:
    res = await db.execute(
        select(SourceMaterial).where(
            SourceMaterial.id == source_material_id,
            SourceMaterial.project_id == project_id,
        )
    )
    return res.scalar_one_or_none()


async def to_response_dict(sm: SourceMaterial) -> dict[str, Any]:
    """Serialize for API output (avoids loading relationships)."""
    return {
        "id": sm.id,
        "project_id": sm.project_id,
        "source_type": sm.source_type,
        "original_filename": sm.original_filename,
        "youtube_url": sm.youtube_url,
        "storage_key": sm.storage_key,
        "proxy_storage_key": sm.proxy_storage_key,
        "thumbnail_storage_key": sm.thumbnail_storage_key,
        "duration_s": sm.duration_s,
        "width": sm.width,
        "height": sm.height,
        "fps": sm.fps,
        "bytes_size": sm.bytes_size,
        "detected_language": sm.detected_language,
        "extra_metadata": sm.extra_metadata,
        "created_at": sm.created_at,
        "updated_at": sm.updated_at,
    }
