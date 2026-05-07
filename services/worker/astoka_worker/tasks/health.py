"""Smoke task — confirms broker round-trip works."""

from astoka_worker.celery_app import celery_app


@celery_app.task(name="astoka.health.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"
