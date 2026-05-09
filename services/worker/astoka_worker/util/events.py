"""Sync Redis pub/sub publisher for worker → API SSE events."""

import json
from typing import Any
from uuid import UUID

import redis
import structlog

from astoka_worker.config import get_worker_settings

_logger = structlog.get_logger(__name__)


def project_events_channel(project_id: UUID | str) -> str:
    return f"events:project:{project_id}"


def publish_event(project_id: UUID | str, payload: dict[str, Any]) -> None:
    """Best-effort publish — keep the job running if Redis flickers, but LOG
    the failure so we can debug "user reports no progress, but worker says fine"
    scenarios. Bare `except: pass` silenced this for too long."""
    try:
        s = get_worker_settings()
        client = redis.from_url(s.redis_url)
        try:
            client.publish(project_events_channel(project_id), json.dumps(payload, default=str))
        finally:
            client.close()
    except Exception as exc:
        _logger.warning(
            "redis.publish_event failed",
            error=str(exc),
            error_type=type(exc).__name__,
            project_id=str(project_id),
            event=payload.get("event"),
        )
