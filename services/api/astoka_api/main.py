"""FastAPI app entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from astoka_api import __version__
from astoka_api.config import get_settings
from astoka_api.health import router as health_router
from astoka_api.routers.auth import router as auth_router
from astoka_api.routers.events import router as events_router
from astoka_api.routers.highlights import router as highlights_router
from astoka_api.routers.projects import router as projects_router
from astoka_api.routers.source_materials import router as source_materials_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Sprint 1+ wires DB pool, Redis client, MinIO client here.
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(source_materials_router)
    app.include_router(highlights_router)
    app.include_router(events_router)
    return app


app = create_app()
