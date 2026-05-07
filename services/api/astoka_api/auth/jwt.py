"""JWT encode/decode with HS256 — PRD AUTH-04 (24h TTL)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from astoka_api.config import get_settings


def create_access_token(subject: str, *, ttl_hours: int | None = None) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(
        hours=ttl_hours if ttl_hours is not None else settings.jwt_ttl_hours
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expires,
        "iat": datetime.now(UTC),
    }
    token: str = jwt.encode(
        payload, settings.api_secret_key, algorithm=settings.jwt_algorithm
    )
    return token


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.api_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
    return payload
