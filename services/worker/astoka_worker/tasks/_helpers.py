"""Shared helpers for worker tasks: job state updates + event publishing.

Each task task starts by marking its Job RUNNING + emitting an SSE event,
ends by setting SUCCEEDED/FAILED + emitting again. This module captures
that boilerplate.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from astoka_api.db.models import Job, JobStatus, SourceMaterial
from astoka_worker.util.events import publish_event


def _job_event_payload(
    job: Job, sm: SourceMaterial, *, override_progress: float | None = None
) -> dict[str, Any]:
    return {
        "event": "job_update",
        "project_id": str(sm.project_id),
        "source_material_id": str(sm.id),
        "job_id": str(job.id),
        "job_type": str(job.job_type),
        "status": str(job.status),
        "progress": override_progress if override_progress is not None else job.progress,
        "progress_message": job.progress_message,
        "error_message": job.error_message,
    }


def mark_running(
    session: Session, job_id: str, message: str | None = None
) -> tuple[Job, SourceMaterial]:
    job = session.get(Job, UUID(job_id))
    assert job is not None, f"Job {job_id} not found"
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC)
    job.progress = 0.0
    job.progress_message = message
    sm = session.get(SourceMaterial, job.source_material_id)
    assert sm is not None
    session.flush()
    publish_event(sm.project_id, _job_event_payload(job, sm))
    return job, sm


def update_progress(
    session: Session,
    job: Job,
    sm: SourceMaterial,
    *,
    progress: float,
    message: str | None = None,
) -> None:
    job.progress = max(0.0, min(1.0, progress))
    if message is not None:
        job.progress_message = message
    session.flush()
    publish_event(sm.project_id, _job_event_payload(job, sm))


def mark_succeeded(
    session: Session,
    job: Job,
    sm: SourceMaterial,
    *,
    result: dict[str, Any] | None = None,
) -> None:
    job.status = JobStatus.SUCCEEDED
    job.progress = 1.0
    job.finished_at = datetime.now(UTC)
    if result is not None:
        job.result = result
    session.flush()
    publish_event(sm.project_id, _job_event_payload(job, sm))


def mark_failed(
    session: Session,
    job: Job,
    sm: SourceMaterial,
    *,
    error: str,
) -> None:
    job.status = JobStatus.FAILED
    job.error_message = error[:2000]
    job.finished_at = datetime.now(UTC)
    session.flush()
    publish_event(sm.project_id, _job_event_payload(job, sm))
