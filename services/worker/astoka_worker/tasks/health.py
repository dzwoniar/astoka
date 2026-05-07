"""Smoke task — confirms broker round-trip works."""

from astoka_worker.celery_app import celery_app


@celery_app.task(name="astoka.health.ping")
def ping() -> str:
    return "pong"
