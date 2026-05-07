"""Sync Redis pub/sub publisher for worker → API SSE events."""

import json
from typing import Any
from uuid import UUID

import redis

from astoka_worker.config import get_worker_settings


def project_events_channel(project_id: UUID | str) -> str:
    return f"events:project:{project_id}"


def publish_event(project_id: UUID | str, payload: dict[str, Any]) -> None:
    """Best-effort publish — swallow errors so a job doesn't fail because Redis
    flickered."""
    try:
        s = get_worker_settings()
        client = redis.from_url(s.redis_url)
        try:
            client.publish(project_events_channel(project_id), json.dumps(payload, default=str))
        finally:
            client.close()
    except Exception:
        pass
