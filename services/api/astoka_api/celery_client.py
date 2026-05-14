"""Celery client for API → worker task dispatch.

The API container MUST NOT import worker code directly. Worker tasks live in a
separate Python package (`astoka_worker`) installed only in the worker container.
If API tries `from astoka_worker.tasks.probe import probe_metadata`, it raises
ImportError, and any `except ImportError: pass` will silently drop the message.

Instead: use task names (strings) as the contract between services. Celery's
`send_task` sends a message to the broker by name; the worker, which has the
task registered under that name, picks it up.

Task names are defined once here as TaskNames constants — single source of truth
shared by API (this file) and worker (which registers tasks with the same names
via `@celery_app.task(name=TaskNames.PROBE)`).
"""

from functools import lru_cache
from typing import Any

from celery import Celery

from astoka_api.config import get_settings


class TaskNames:
    """Stable task names — contract between API (dispatch) and worker (register).

    Do NOT rename without coordinating with worker code. Adding a new task:
    1. Add constant here
    2. Worker's @celery_app.task(name=TaskNames.X) uses the same string
    3. Call `send_task(TaskNames.X, args=[...])` from API
    """

    PROBE = "astoka.probe"
    INGEST_YOUTUBE = "astoka.ingest.youtube"
    ASR = "astoka.asr"
    HIGHLIGHTS = "astoka.highlights"
    RENDER = "astoka.render"  # Sprint 5


@lru_cache(maxsize=1)
def _client() -> Celery:
    """Lightweight Celery app for sending messages — no task registry, no worker.

    CRITICAL: must mirror the worker's broker/queue config (see
    `services/worker/astoka_worker/celery_app.py`). If queue/serializer/content
    settings drift between the two sides, messages reach Redis but live in the
    wrong queue and the worker silently never consumes them.

    Specifically `task_default_queue="default"` matches the worker side.
    Without it, Celery defaults to queue name `"celery"` here while the worker
    listens on `"default"` — every task gets stuck on the broker forever.
    """
    settings = get_settings()
    app = Celery(
        "astoka-api",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )
    app.conf.update(
        task_default_queue="default",
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
    return app


def send_task(
    name: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    """Dispatch a task to the worker. Returns the Celery task ID.

    Raises whatever the broker raises (typically `kombu.exceptions.OperationalError`)
    when Redis is down — caller should let it propagate to a 500/503 instead of
    silently dropping the request.
    """
    result = _client().send_task(name, args=args or [], kwargs=kwargs or {})
    return str(result.id)
