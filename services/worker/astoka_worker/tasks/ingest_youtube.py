"""yt-dlp download task. Saves to MinIO, then chains to probe."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from astoka_api.services import storage_service as api_storage
from astoka_worker.celery_app import celery_app
from astoka_worker.tasks._helpers import (
    mark_failed,
    mark_running,
    mark_succeeded,
    update_progress,
)
from astoka_worker.util.db import db_session
from astoka_worker.util.events import publish_event
from astoka_worker.util.storage import upload_file


@celery_app.task(name="astoka.ingest.youtube", bind=True, max_retries=2)
def download_youtube(self, source_material_id: str, job_id: str) -> str:
    """Download a YouTube URL via yt-dlp → MinIO → trigger probe job."""
    import yt_dlp  # imported here to keep tests cheap

    with db_session() as session:
        job, sm = mark_running(session, job_id, message="Pobieram z YouTube...")

        if not sm.youtube_url:
            mark_failed(session, job, sm, error="No youtube_url")
            raise RuntimeError("no youtube_url")

        # Capture IDs needed by progress_hook BEFORE leaving the SQLAlchemy
        # session scope. The hook intentionally never touches the DB — see
        # the docstring inside `progress_hook` below.
        project_id_str = str(sm.project_id)
        sm_id_str = str(sm.id)
        job_id_str = str(job.id)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = str(Path(tmpdir) / "%(id)s.%(ext)s")

            last_pct: dict[str, float] = {"v": 0.0}

            def progress_hook(d: dict[str, Any]) -> None:
                """Best-effort progress reporting from yt-dlp.

                CRITICAL: do NOT open a DB session inside this callback.
                The hook fires inline on yt-dlp's download path. Earlier code
                opened a fresh `db_session()` per progress event, which under
                Celery's prefork pool deadlocked at ~6.5% — psycopg2 connections
                inherited across fork() were poisoned, and the inner flush()
                blocked the download thread forever.

                Instead: publish a JSON event to Redis only (sync redis client,
                fresh connection per call, swallows errors). The SSE listener
                in the API reads from the same channel and updates the UI live.
                Job.progress in the DB stays at 0.05 until mark_succeeded /
                mark_failed at the end — acceptable for MVP, SSE feed is real.
                """
                if d.get("status") != "downloading":
                    return
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                if total <= 0:
                    return
                pct = downloaded / total
                # Throttle Redis publishes to ~5% steps.
                if pct - last_pct["v"] < 0.05:
                    return
                last_pct["v"] = pct
                scaled = 0.05 + pct * 0.8  # 0.05..0.85 of the overall job
                publish_event(
                    project_id_str,
                    {
                        "event": "job_update",
                        "project_id": project_id_str,
                        "source_material_id": sm_id_str,
                        "job_id": job_id_str,
                        "job_type": "youtube_download",
                        "status": "running",
                        "progress": scaled,
                        "progress_message": f"Pobieram z YouTube... {pct:.0%}",
                        "error_message": None,
                    },
                )

            ydl_opts = {
                "outtmpl": output_template,
                # Single pre-muxed stream so yt-dlp doesn't spawn ffmpeg to
                # merge bestvideo+bestaudio. The merge subprocess inherits
                # Celery's stdio FDs and hangs on write() in prefork pool.
                # Trade-off: capped at whatever pre-muxed quality YouTube
                # serves (usually 720p H.264 + AAC, fine for MVP).
                "format": "best[height<=1080][ext=mp4]/best[height<=1080]/best",
                "noplaylist": True,
                "quiet": True,
                "progress_hooks": [progress_hook],
                "writethumbnail": True,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(sm.youtube_url, download=True)
                    file_path = ydl.prepare_filename(info)
                    if not Path(file_path).exists():
                        # yt-dlp might post-process: scan for produced file.
                        candidates = list(Path(tmpdir).glob(f"*.{info.get('ext', 'mp4')}"))
                        if candidates:
                            file_path = str(candidates[0])

                update_progress(session, job, sm, progress=0.9, message="Wysyłam do MinIO...")
                ext = Path(file_path).suffix
                fake_filename = f"{info.get('id', 'youtube')}{ext}"
                storage_key = api_storage.storage_key_for_source(str(sm.id), fake_filename)
                upload_file(file_path, storage_key)
                sm.storage_key = storage_key
                sm.original_filename = fake_filename

                # Stash yt-dlp metadata.
                extra = dict(sm.extra_metadata)
                extra["yt_dlp"] = {
                    "title": info.get("title"),
                    "uploader": info.get("uploader"),
                    "upload_date": info.get("upload_date"),
                    "duration": info.get("duration"),
                    "view_count": info.get("view_count"),
                    "id": info.get("id"),
                }
                sm.extra_metadata = extra

                # Optional thumbnail upload.
                thumb_files = list(Path(tmpdir).glob("*.jpg")) + list(
                    Path(tmpdir).glob("*.webp")
                )
                if thumb_files:
                    thumb_key = api_storage.storage_key_for_thumbnail(str(sm.id))
                    upload_file(str(thumb_files[0]), thumb_key)
                    sm.thumbnail_storage_key = thumb_key

                session.flush()

                mark_succeeded(
                    session,
                    job,
                    sm,
                    result={
                        "title": info.get("title"),
                        "duration": info.get("duration"),
                        "id": info.get("id"),
                    },
                )

                # Chain to probe — see source_material_service._enqueue_probe for
                # the same commit-before-delay pattern. The probe worker runs in a
                # separate process; if we only flush, the new probe_job row isn't
                # yet visible on its connection when the Redis task message arrives.

                from astoka_api.db.models import Job, JobStatus, JobType
                from astoka_worker.tasks.probe import probe_metadata

                probe_job = Job(
                    source_material_id=sm.id,
                    job_type=JobType.PROBE,
                    status=JobStatus.PENDING,
                )
                session.add(probe_job)
                session.commit()  # row durable + visible to probe worker
                celery_result = probe_metadata.delay(str(sm.id), str(probe_job.id))
                probe_job.celery_task_id = celery_result.id
                session.commit()

                return str(sm.id)

            except yt_dlp.utils.DownloadError as exc:
                # Map the most common yt-dlp errors to user-friendly Polish messages.
                msg = str(exc).lower()
                if "private" in msg:
                    user_msg = "Wideo prywatne. Wgraj plik lokalnie zamiast linku."
                elif "members-only" in msg or "members only" in msg:
                    user_msg = "Wideo dla członków kanału. Wgraj plik lokalnie."
                elif "geo-restrict" in msg or "not available in your country" in msg:
                    user_msg = "Wideo zablokowane w tej lokalizacji."
                elif "sign in to confirm" in msg or "bot" in msg:
                    user_msg = (
                        "YouTube wymaga weryfikacji bot. Spróbuj za parę minut "
                        "lub wgraj plik lokalnie."
                    )
                elif "video unavailable" in msg or "removed" in msg:
                    user_msg = "Wideo niedostępne lub usunięte."
                elif "age" in msg and "restrict" in msg:
                    user_msg = "Wideo z ograniczeniem wiekowym wymaga zalogowania."
                else:
                    user_msg = f"yt-dlp: {exc}"
                mark_failed(session, job, sm, error=user_msg)
                raise
            except Exception as exc:
                mark_failed(session, job, sm, error=f"{type(exc).__name__}: {exc}")
                raise
