"""Seed admin user — run once after first migration.

Usage (from inside api container or via `make seed`):
    python -m astoka_api.cli.seed

Idempotent — re-running won't create duplicates.

For Sprint 1 demo backbone we hardcode admin/admin (PRD AUTH-01, AUTH-02 minimal scope).
Full multi-user admin-managed accounts come in Sprint 6.
"""

import asyncio

from sqlalchemy import select

from astoka_api.auth.security import hash_password
from astoka_api.db import async_session_factory
from astoka_api.db.models import User

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"


async def seed_admin() -> None:
    factory = async_session_factory()
    async with factory() as session:
        result = await session.execute(select(User).where(User.username == DEFAULT_USERNAME))
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"User '{DEFAULT_USERNAME}' already exists (id={existing.id}). Skipping.")
            return

        user = User(
            username=DEFAULT_USERNAME,
            password_hash=hash_password(DEFAULT_PASSWORD),
            is_admin=True,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Seeded admin user: username={DEFAULT_USERNAME} password={DEFAULT_PASSWORD}")


def main() -> None:
    asyncio.run(seed_admin())


if __name__ == "__main__":
    main()
