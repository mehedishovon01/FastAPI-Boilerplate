"""Authentication endpoints: register, login, refresh, password reset."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from src.apps.auth import schemas, service
from src.apps.users import schemas as user_schemas
from src.apps.users import service as users_service
from src.core.dependencies import DbSession

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=user_schemas.UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
def register(payload: user_schemas.UserCreate, db: DbSession):
    return users_service.create_user(db, payload)


@router.post(
    "/login",
    response_model=schemas.TokenPair,
    summary="OAuth2 password flow login (username or email)",
)
def login(
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = users_service.authenticate(
        db, login=form_data.username, password=form_data.password
    )
    return service.issue_token_pair(user)


@router.post(
    "/refresh",
    response_model=schemas.AccessTokenOnly,
    summary="Exchange a refresh token for a new access token",
)
def refresh(payload: schemas.RefreshRequest, db: DbSession):
    return service.refresh_access_token(db, payload.refresh_token)


@router.post(
    "/password-reset/request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password-reset email",
)
def password_reset_request(payload: schemas.PasswordResetRequest, db: DbSession):
    service.request_password_reset(db, payload.email)
    return {"detail": "If the email exists, a reset link has been sent."}


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirm a password reset with the emailed token",
)
def password_reset_confirm(payload: schemas.PasswordResetConfirm, db: DbSession):
    service.confirm_password_reset(db, payload.token, payload.new_password)
