"""Probe task: extract metadata + generate proxy preview.

Chain step 2 (after upload or YouTube download). Reads the original from MinIO,
runs ffprobe, encodes a 480p proxy back to MinIO, updates SourceMaterial columns.

Followed by ASR job in the chain (Phase C).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from astoka_api.services import storage_service as api_storage
from astoka_worker.celery_app import celery_app
from astoka_worker.tasks._helpers import (
    mark_failed,
    mark_running,
    mark_succeeded,
    update_progress,
)
from astoka_worker.util.db import db_session
from astoka_worker.util.ffmpeg import (
    extract_basic_metadata,
    ffprobe_metadata,
    make_proxy_preview,
)
from astoka_worker.util.hashing import sha256_file
from astoka_worker.util.storage import download_file, stat_object, upload_file


@celery_app.task(name="astoka.probe", bind=True, max_retries=2)
def probe_metadata(self, source_material_id: str, job_id: str) -> str:
    """Probe a source_material → fill metadata + create proxy preview.

    Returns the source_material_id so a Celery chain can pass it to the next task.
    """
    with db_session() as session:
        try:
            job, sm = mark_running(session, job_id, message="Pobieram metadane...")
        except AssertionError as e:
            raise RuntimeError(str(e)) from e

        if not sm.storage_key:
            mark_failed(session, job, sm, error="Source material has no storage_key")
            raise RuntimeError("no storage_key")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_in = str(Path(tmpdir) / "input.bin")

            try:
                update_progress(session, job, sm, progress=0.1, message="Pobieram z MinIO...")
                download_file(sm.storage_key, local_in)

                update_progress(session, job, sm, progress=0.3, message="Hash pliku...")
                if not sm.content_hash:
                    sm.content_hash = sha256_file(local_in)
                    session.flush()

                update_progress(session, job, sm, progress=0.5, message="ffprobe metadane...")
                probe = ffprobe_metadata(local_in)
                meta = extract_basic_metadata(probe)
                sm.duration_s = meta["duration_s"]
                sm.width = meta["width"]
                sm.height = meta["height"]
                sm.fps = meta["fps"]
                sm.bytes_size = meta["bytes_size"] or stat_object(sm.storage_key)
                sm.detected_language = meta["detected_language"]
                sm.audio_streams = meta["audio_streams"]
                # Stash full ffprobe output in extra_metadata for debugging.
                extra = dict(sm.extra_metadata)
                extra["ffprobe"] = probe
                sm.extra_metadata = extra
                session.flush()

                update_progress(session, job, sm, progress=0.7, message="Generuję proxy 480p...")
                local_proxy = str(Path(tmpdir) / "proxy.mp4")
                make_proxy_preview(local_in, local_proxy)
                proxy_key = api_storage.storage_key_for_proxy(str(sm.id))
                upload_file(local_proxy, proxy_key)
                sm.proxy_storage_key = proxy_key
                session.flush()

                update_progress(
                    session, job, sm, progress=0.95, message="Kolejkuję ASR..."
                )

                mark_succeeded(
                    session,
                    job,
                    sm,
                    result={
                        "duration_s": sm.duration_s,
                        "proxy_storage_key": proxy_key,
                    },
                )

                # Chain to ASR. Lazy import — ASR module may not be ready in all envs.
                try:
                    from astoka_worker.tasks.asr import transcribe

                    transcribe.delay(str(sm.id))
                except (ImportError, AttributeError):
                    pass

                return str(sm.id)

            except Exception as exc:
                mark_failed(session, job, sm, error=f"{type(exc).__name__}: {exc}")
                raise
