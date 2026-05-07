"""Celery application — broker/backend = Redis.

Queue topology (NFR-REL-01, RNDR-08):
- `default`     — generic / cleanup tasks
- `asr`         — Whisper transcription (GPU-bound, sequential per device)
- `highlight`   — heuristics + LLM reranking (GPU + Ollama)
- `render`      — FFmpeg/NVENC export (GPU encoder, single engine)

Sprint 0 wires only `default`. Other queues come online with their respective sprints.
"""

from celery import Celery

from astoka_worker.config import get_worker_settings

settings = get_worker_settings()

celery_app = Celery(
    "astoka",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "astoka_worker.tasks.health",
        "astoka_worker.tasks.probe",
        "astoka_worker.tasks.ingest_youtube",
        "astoka_worker.tasks.asr",
        "astoka_worker.tasks.highlights",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # GPU jobs — don't grab work we can't do.
    # Retry policy — NFR-REL-01: max 3 retries, exponential backoff.
    task_default_retry_delay=30,
    task_max_retries=3,
    task_default_queue="default",
    # Sprint 5+ uncomments queue routing here.
    # task_routes={
    #     "astoka_worker.tasks.asr.*":       {"queue": "asr"},
    #     "astoka_worker.tasks.highlights.*":{"queue": "highlight"},
    #     "astoka_worker.tasks.render.*":    {"queue": "render"},
    # },
)
