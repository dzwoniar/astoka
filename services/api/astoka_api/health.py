"""Healthcheck — verifies API + critical dependencies (Postgres, Redis, MinIO, Ollama).

Each dependency check is best-effort; failures degrade the overall status to "degraded"
without raising — this lets Docker Compose distinguish "starting" from "stopped".
"""

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from astoka_api import __version__
from astoka_api.config import get_settings

router = APIRouter(tags=["health"])


class DependencyStatus(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    dependencies: list[DependencyStatus]


async def _check_postgres() -> DependencyStatus:
    settings = get_settings()
    try:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return DependencyStatus(name="postgres", ok=True)
    except Exception as exc:
        return DependencyStatus(name="postgres", ok=False, detail=str(exc)[:200])


async def _check_redis() -> DependencyStatus:
    settings = get_settings()
    try:
        import redis.asyncio as redis_async

        client: Any = redis_async.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        return DependencyStatus(name="redis", ok=True)
    except Exception as exc:
        return DependencyStatus(name="redis", ok=False, detail=str(exc)[:200])


async def _check_minio() -> DependencyStatus:
    settings = get_settings()
    url = f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}/minio/health/live"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        return DependencyStatus(name="minio", ok=True)
    except Exception as exc:
        return DependencyStatus(name="minio", ok=False, detail=str(exc)[:200])


async def _check_ollama() -> DependencyStatus:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            resp.raise_for_status()
        return DependencyStatus(name="ollama", ok=True)
    except Exception as exc:
        return DependencyStatus(name="ollama", ok=False, detail=str(exc)[:200])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    deps = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_minio(),
        _check_ollama(),
        return_exceptions=False,
    )
    overall_ok = all(d.ok for d in deps)
    return HealthResponse(
        status="ok" if overall_ok else "degraded",
        version=__version__,
        dependencies=list(deps),
    )


@router.get("/health/live")
async def health_live() -> dict[str, Any]:
    """Liveness probe — does NOT check deps. Used by container healthcheck."""
    return {"status": "ok"}
