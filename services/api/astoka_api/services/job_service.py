"""Job state machine + SSE event broadcasting via Redis pub/sub."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis_async
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from astoka_api.config import get_settings
from astoka_api.db.models import Job, JobStatus, JobType


def project_events_channel(project_id: UUID) -> str:
    return f"events:project:{project_id}"


async def publish_event(project_id: UUID, payload: dict[str, Any]) -> None:
    """Push event to Redis pub/sub channel for this project's SSE stream."""
    settings = get_settings()
    client: Any = redis_async.from_url(settings.redis_url)
    try:
        channel = project_events_channel(project_id)
        await client.publish(channel, json.dumps(payload))
    finally:
        await client.aclose()


async def create_job(
    db: AsyncSession,
    *,
    source_material_id: UUID,
    job_type: JobType,
    celery_task_id: str | None = None,
) -> Job:
    job = Job(
        source_material_id=source_material_id,
        job_type=job_type,
        status=JobStatus.PENDING,
        celery_task_id=celery_task_id,
    )
    db.add(job)
    await db.flush()
    return job


async def update_job_status(
    db: AsyncSession,
    *,
    job_id: UUID,
    status: JobStatus | None = None,
    progress: float | None = None,
    progress_message: str | None = None,
    error_message: str | None = None,
    result: dict[str, Any] | None = None,
) -> Job | None:
    res = await db.execute(select(Job).where(Job.id == job_id))
    job = res.scalar_one_or_none()
    if job is None:
        return None

    if status is not None:
        prev = job.status
        job.status = status
        if status == JobStatus.RUNNING and prev != JobStatus.RUNNING:
            job.started_at = datetime.now(UTC)
        if status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.finished_at = datetime.now(UTC)
    if progress is not None:
        job.progress = max(0.0, min(1.0, progress))
    if progress_message is not None:
        job.progress_message = progress_message
    if error_message is not None:
        job.error_message = error_message
    if result is not None:
        job.result = result

    await db.flush()
    return job


async def list_jobs_for_project(
    db: AsyncSession, *, project_id: UUID
) -> list[Job]:
    """All jobs across all source materials in a project."""
    from astoka_api.db.models import SourceMaterial

    stmt = (
        select(Job)
        .join(SourceMaterial, Job.source_material_id == SourceMaterial.id)
        .where(SourceMaterial.project_id == project_id)
        .order_by(Job.created_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
