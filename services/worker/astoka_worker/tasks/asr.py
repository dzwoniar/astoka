"""ASR worker task: faster-whisper transcription with word_timestamps.

Lazy model download — first run pulls the configured WHISPER_MODEL (~1.5 GB
for `medium`, ~3 GB for `large-v3`). Default is `medium` since it's the best
quality/speed tradeoff for Polish per Janek's testing on Akademia recordings.

GPU/CPU auto-fallback via try/except: CUDA → fp16; on failure → CPU int8.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import UUID

from astoka_api.db.models import SourceMaterial, Transcript
from astoka_worker.celery_app import celery_app
from astoka_worker.tasks._helpers import (
    mark_failed,
    mark_running,
    mark_succeeded,
    update_progress,
)
from astoka_worker.util.db import db_session
from astoka_worker.util.events import publish_event
from astoka_worker.util.storage import download_file

# Default Whisper model. Janek can override via WHISPER_MODEL env (or per-project
# setting in a future sprint). `medium` chosen as the quality/speed sweet spot
# for Polish on RTX 4090 (PRD MET-06 target WER ≤10%); requires GPU for usable
# throughput. Override examples:
#   WHISPER_MODEL=Systran/faster-whisper-large-v3        — best quality, slower
#   WHISPER_MODEL=Systran/faster-distil-whisper-large-v3 — faster, slightly worse
DEFAULT_WHISPER_MODEL = os.environ.get(
    "WHISPER_MODEL", "Systran/faster-whisper-medium"
)

# Singleton — first call loads, subsequent calls reuse.
_MODEL_CACHE: dict[str, object] = {}


def _load_model(model_id: str):
    """Returns faster_whisper.WhisperModel. Tries CUDA fp16 first, then CPU int8."""
    if model_id in _MODEL_CACHE:
        return _MODEL_CACHE[model_id]

    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(model_id, device="cuda", compute_type="float16")
    except Exception:
        # Either no CUDA or CUDA libs not available in container — fall back.
        model = WhisperModel(model_id, device="cpu", compute_type="int8")

    _MODEL_CACHE[model_id] = model
    return model


@celery_app.task(name="astoka.asr", bind=True, max_retries=1)
def transcribe(self, source_material_id: str) -> str:
    """Transcribe audio from source_material → persist Transcript → chain to highlights."""
    from astoka_api.db.models import Job, JobStatus, JobType

    sm_uuid = UUID(source_material_id)

    # Create or pick up an ASR job (one per source_material).
    with db_session() as session:
        sm = session.get(SourceMaterial, sm_uuid)
        if sm is None:
            raise RuntimeError(f"SourceMaterial {sm_uuid} not found")

        # Cache check: if a transcript already exists for this hash, skip.
        if sm.content_hash:
            from sqlalchemy import select

            existing = (
                session.execute(
                    select(Transcript)
                    .join(SourceMaterial, Transcript.source_material_id == SourceMaterial.id)
                    .where(SourceMaterial.content_hash == sm.content_hash)
                    .where(Transcript.source_material_id != sm.id)
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if existing is not None:
                # Clone the existing transcript record under this source_material.
                clone = Transcript(
                    source_material_id=sm.id,
                    language=existing.language,
                    model_id=existing.model_id,
                    alignment_method=existing.alignment_method,
                    full_text=existing.full_text,
                    segments_json=list(existing.segments_json),
                    avg_confidence=existing.avg_confidence,
                )
                session.add(clone)
                session.flush()
                publish_event(
                    sm.project_id,
                    {
                        "event": "transcript_ready",
                        "project_id": str(sm.project_id),
                        "source_material_id": str(sm.id),
                        "from_cache": True,
                    },
                )
                _kick_off_highlights(str(sm.id))
                return str(sm.id)

        job = Job(
            source_material_id=sm_uuid,
            job_type=JobType.ASR,
            status=JobStatus.PENDING,
            celery_task_id=self.request.id,
        )
        session.add(job)
        session.flush()
        job_id = str(job.id)

    # Mark running outside the previous tx so SSE event fires immediately.
    with db_session() as session:
        job, sm = mark_running(session, job_id, message="Pobieram audio...")

        if not sm.storage_key:
            mark_failed(session, job, sm, error="No storage_key")
            raise RuntimeError("no storage_key")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_in = str(Path(tmpdir) / "input")
            try:
                update_progress(session, job, sm, progress=0.05, message="Pobieram materiał...")
                download_file(sm.storage_key, local_in)

                update_progress(
                    session,
                    job,
                    sm,
                    progress=0.10,
                    message="Ładuję model ASR (pierwszy run pobiera ~1.5 GB)...",
                )
                model = _load_model(DEFAULT_WHISPER_MODEL)

                update_progress(
                    session, job, sm, progress=0.15, message="Transkrybuję..."
                )

                segments_iter, info = model.transcribe(
                    local_in,
                    language="pl",
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=False,
                )

                segments_list: list[dict[str, object]] = []
                full_text_parts: list[str] = []
                total_duration = info.duration or sm.duration_s or 0.0

                for seg in segments_iter:
                    words = []
                    if seg.words:
                        for w in seg.words:
                            words.append(
                                {
                                    "text": w.word.strip(),
                                    "start": float(w.start),
                                    "end": float(w.end),
                                    "confidence": float(w.probability or 0.0),
                                }
                            )
                    segments_list.append(
                        {
                            "text": seg.text.strip(),
                            "start": float(seg.start),
                            "end": float(seg.end),
                            "words": words,
                        }
                    )
                    full_text_parts.append(seg.text.strip())

                    # Update progress based on segment end vs total duration.
                    if total_duration > 0:
                        pct = 0.15 + 0.75 * (seg.end / total_duration)
                        if int(seg.end) % 5 == 0:  # every ~5s of audio
                            update_progress(
                                session,
                                job,
                                sm,
                                progress=min(0.9, pct),
                                message=f"Transkrybuję... {seg.end:.0f}s / {total_duration:.0f}s",
                            )

                # Compute average confidence across all words.
                all_confs: list[float] = []
                for s in segments_list:
                    seg_words = s.get("words")
                    if isinstance(seg_words, list):
                        for w in seg_words:
                            if isinstance(w, dict):
                                conf = w.get("confidence")
                                if isinstance(conf, int | float):
                                    all_confs.append(float(conf))
                avg_conf = (
                    float(sum(all_confs) / len(all_confs)) if all_confs else None
                )

                update_progress(
                    session, job, sm, progress=0.95, message="Zapisuję transkrypcję..."
                )

                transcript = Transcript(
                    source_material_id=sm.id,
                    language=info.language or "pl",
                    model_id=DEFAULT_WHISPER_MODEL,
                    alignment_method="faster_whisper_word_timestamps",
                    full_text=" ".join(full_text_parts),
                    segments_json=segments_list,
                    avg_confidence=avg_conf,
                )
                session.add(transcript)
                session.flush()

                if not sm.detected_language:
                    sm.detected_language = info.language

                mark_succeeded(
                    session,
                    job,
                    sm,
                    result={
                        "transcript_id": str(transcript.id),
                        "segments_count": len(segments_list),
                        "avg_confidence": avg_conf,
                    },
                )

                publish_event(
                    sm.project_id,
                    {
                        "event": "transcript_ready",
                        "project_id": str(sm.project_id),
                        "source_material_id": str(sm.id),
                        "from_cache": False,
                    },
                )

                _kick_off_highlights(str(sm.id))
                return str(sm.id)

            except Exception as exc:
                mark_failed(session, job, sm, error=f"{type(exc).__name__}: {exc}")
                raise


def _kick_off_highlights(source_material_id: str) -> None:
    try:
        from astoka_worker.tasks.highlights import detect_highlights

        detect_highlights.delay(source_material_id)
    except (ImportError, AttributeError):
        # Phase D not landed yet — that's OK, transcript still useful.
        pass
