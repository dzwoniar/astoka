"""Sync DB session for Celery tasks (Celery doesn't play well with asyncio).

Workers use a separate sync engine; API uses async. Schema is shared via
astoka_api package.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from astoka_worker.config import get_worker_settings


@lru_cache(maxsize=1)
def get_sync_engine() -> Engine:
    settings = get_worker_settings()
    # Convert async DSN (asyncpg) to sync (psycopg2). Both share the same Postgres.
    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(sync_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def sync_session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_sync_engine(), expire_on_commit=False)


@contextmanager
def db_session() -> Iterator[Session]:
    """Context manager: auto-commit if no exception, rollback otherwise."""
    factory = sync_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
