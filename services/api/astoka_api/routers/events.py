"""Server-Sent Events for live pipeline status.

GET /projects/{project_id}/events  → SSE stream of job updates.

Subscribes to Redis pub/sub channel `events:project:{project_id}`. Worker tasks
publish events there via job_service.publish_event(). Browser EventSource
consumes them.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import redis.asyncio as redis_async
from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from astoka_api.auth.deps import CurrentUser
from astoka_api.config import get_settings
from astoka_api.db import async_session_factory
from astoka_api.db.models import Project
from astoka_api.services.job_service import project_events_channel

router = APIRouter(prefix="/projects/{project_id}", tags=["events"])


async def _user_owns_project(user_id: UUID, project_id: UUID) -> bool:
    factory = async_session_factory()
    async with factory() as session:
        res = await session.execute(
            select(Project).where(
                Project.id == project_id, Project.owner_id == user_id
            )
        )
        return res.scalar_one_or_none() is not None


def _format_sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


async def _event_stream(
    request: Request, project_id: UUID
) -> AsyncIterator[str]:
    settings = get_settings()
    client: Any = redis_async.from_url(settings.redis_url)
    channel = project_events_channel(project_id)
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)

        # Initial open ping so EventSource knows we're alive.
        yield _format_sse("ping", {"project_id": str(project_id)})

        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=15.0,
                )
            except TimeoutError:
                # Heartbeat keeps the connection alive through proxies.
                yield ": heartbeat\n\n"
                continue
            if msg is None or msg.get("type") != "message":
                continue
            try:
                data = json.loads(msg["data"])
                event_name = data.get("event", "message")
                yield _format_sse(event_name, data)
            except (json.JSONDecodeError, TypeError):
                continue
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        finally:
            await client.aclose()


@router.get("/events")
async def project_events(
    project_id: UUID,
    user: CurrentUser,
    request: Request,
) -> StreamingResponse:
    if not await _user_owns_project(user.id, project_id):
        from fastapi import HTTPException

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    return StreamingResponse(
        _event_stream(request, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering
        },
    )
