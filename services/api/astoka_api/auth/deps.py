"""FastAPI dependencies for auth.

`get_current_user` reads JWT from httpOnly cookie `astoka_session`, decodes,
loads user from DB. Raises 401 if missing/invalid/inactive.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from astoka_api.auth.jwt import decode_access_token
from astoka_api.db import get_session
from astoka_api.db.models import User

SESSION_COOKIE_NAME = "astoka_session"


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_session)],
    astoka_session: Annotated[str | None, Cookie()] = None,
) -> User:
    if not astoka_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session cookie",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(astoka_session)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session subject",
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
