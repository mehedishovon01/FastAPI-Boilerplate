"""Authentication service: token issuance and password reset."""
from __future__ import annotations

import logging

import jwt
from sqlalchemy.orm import Session

from src.apps.auth import schemas
from src.apps.users import service as users_service
from src.apps.users.models import User
from src.core.exceptions import InvalidTokenError, NotFoundError
from src.core.security import (
    TokenType,
    access_token_expires_at,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
)
from src.services.email import send_email

logger = logging.getLogger(__name__)


def issue_token_pair(user: User) -> schemas.TokenPair:
    return schemas.TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_at=access_token_expires_at(),
    )


def refresh_access_token(db: Session, refresh_token: str) -> schemas.AccessTokenOnly:
    try:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError("User no longer eligible for tokens.")

    return schemas.AccessTokenOnly(
        access_token=create_access_token(user.id),
        expires_at=access_token_expires_at(),
    )


def request_password_reset(db: Session, email: str) -> None:
    """Always returns successfully to avoid leaking which emails are registered."""
    user = users_service.get_user_by_email(db, email)
    if user is None:
        logger.info("Password-reset requested for unknown email %s", email)
        return

    token = create_password_reset_token(user.id)
    send_email(
        to=user.email,
        subject="Reset your password",
        body=(
            "You (or someone using your email) requested a password reset.\n"
            f"Use this token to set a new password: {token}\n"
            "If you did not request this, you can safely ignore this email."
        ),
    )


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    try:
        payload = decode_token(token, expected_type=TokenType.PASSWORD_RESET)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise NotFoundError("User not found.")
    users_service.set_password(db, user, new_password)
