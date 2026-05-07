"""Auth endpoints: login (sets cookie), logout (clears cookie), me (current user)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from astoka_api.auth.deps import SESSION_COOKIE_NAME, CurrentUser
from astoka_api.auth.jwt import create_access_token
from astoka_api.auth.security import verify_password
from astoka_api.config import get_settings
from astoka_api.db import get_session
from astoka_api.db.models import User
from astoka_api.schemas.auth import LoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    settings = get_settings()
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user.last_login_at = datetime.now(UTC)
    await db.flush()

    token = create_access_token(subject=str(user.id))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.jwt_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        # Secure flag off in dev (localhost http); on in prod via Traefik TLS termination.
        secure=False,
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=UserResponse)
async def me(current: CurrentUser) -> User:
    return current
