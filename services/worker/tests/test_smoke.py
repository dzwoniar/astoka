"""Smoke test — celery_app constructs without runtime errors."""

from astoka_worker.celery_app import celery_app


def test_celery_app_constructs() -> None:
    assert celery_app.main == "astoka"
    assert celery_app.conf.task_default_queue == "default"


def test_ping_task_registered() -> None:
    from astoka_worker.tasks.health import ping  # noqa: F401

    assert "astoka.health.ping" in celery_app.tasks
