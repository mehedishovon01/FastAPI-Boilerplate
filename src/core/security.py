"""Password hashing (bcrypt) and JWT helpers (PyJWT).

We use ``bcrypt`` directly (no passlib) because passlib has not been
maintained for several years and breaks with bcrypt >= 4.1. The bcrypt
package itself exposes a small, stable API.

JWTs are issued with two flavors:

* ``access``  — short-lived, sent on every request.
* ``refresh`` — long-lived, exchanged for a new access token.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

import bcrypt
import jwt

from src.core.config import settings


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


# ---------- Password ----------

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# ---------- JWT ----------

def _create_token(
    subject: str | int,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type.value,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_password_reset_token(subject: str | int) -> str:
    return _create_token(
        subject,
        TokenType.PASSWORD_RESET,
        timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode & verify a JWT. Raises ``jwt.PyJWTError`` on failure."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if expected_type is not None and payload.get("type") != expected_type.value:
        raise jwt.InvalidTokenError(f"Expected token type '{expected_type.value}'")
    return payload


def access_token_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
