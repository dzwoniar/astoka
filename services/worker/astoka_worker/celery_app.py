"""Celery application — broker/backend = Redis.

Queue topology (NFR-REL-01, RNDR-08):
- `default`     — generic / cleanup tasks
- `asr`         — Whisper transcription (GPU-bound, sequential per device)
- `highlight`   — heuristics + LLM reranking (GPU + Ollama)
- `render`      — FFmpeg/NVENC export (GPU encoder, single engine)

Sprint 0 wires only `default`. Other queues come online with their respective sprints.
"""

from celery import Celery
from celery.signals import worker_process_init

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


@worker_process_init.connect
def _dispose_engine_after_fork(**_: object) -> None:
    """Dispose the SQLAlchemy engine inside each forked child.

    Celery's prefork pool forks worker children from the parent process AFTER
    the SQLAlchemy engine + psycopg2 connection pool have already been created
    (engine creation is memoized via @lru_cache in `util.db.get_sync_engine`).
    Forked children inherit the parent's open sockets and pool state, which
    psycopg2 cannot safely share — first DB write in a child can deadlock or
    silently corrupt the connection. Empirically: YouTube download hung at
    ~6.5% inside `progress_hook` because the inner db_session() called from
    yt-dlp's download thread tried to use one of those inherited connections.

    Standard SQLAlchemy + Celery prefork mitigation: dispose the engine on
    `worker_process_init`. Each child rebuilds its own connection pool lazily
    on first use, with fresh sockets owned by that child.

    See also: docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing
    """
    # Lazy import — keeps this signal handler importable in environments where
    # the DB module's optional deps aren't installed (e.g. unit tests of
    # celery_app construction).
    from astoka_worker.util.db import get_sync_engine

    get_sync_engine().dispose()
