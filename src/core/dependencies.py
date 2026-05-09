"""Reusable FastAPI dependencies.

Auth & RBAC are implemented as plain dependencies (instead of the
broken middleware in the old code). They are easy to compose:

    @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    def admin_only(...): ...

    @router.delete("/users/{id}",
                   dependencies=[Depends(require_permission("delete_user"))])
    def delete_user(...): ...
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.apps.users.models import User
from src.core.config import settings
from src.core.database import get_db
from src.core.exceptions import (
    InvalidTokenError,
    NotFoundError,
    PermissionDeniedError,
)
from src.core.security import TokenType, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# Type aliases — make endpoint signatures very short & readable
DbSession = Annotated[Session, Depends(get_db)]
AccessToken = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(token: AccessToken, db: DbSession) -> User:
    """Resolve the user behind the bearer token, or raise 401."""
    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise InvalidTokenError("Token missing subject.")

    user = db.get(User, int(user_id))
    if user is None:
        raise NotFoundError("User no longer exists.")
    if not user.is_active:
        raise PermissionDeniedError("Inactive user.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise PermissionDeniedError("Superuser privileges required.")
    return current_user


def require_role(*role_names: str) -> Callable[[User], User]:
    """Dependency factory: pass if user has *any* of the given roles."""

    required = set(role_names)

    def _dep(current_user: CurrentUser) -> User:
        user_roles = {role.name for role in current_user.roles}
        if current_user.is_superuser or user_roles & required:
            return current_user
        raise PermissionDeniedError(
            f"Requires one of roles: {', '.join(sorted(required))}."
        )

    return _dep


def require_permission(*permission_names: str) -> Callable[[User], User]:
    """Dependency factory: pass if user has *all* of the given permissions."""

    required = set(permission_names)

    def _dep(current_user: CurrentUser) -> User:
        if current_user.is_superuser:
            return current_user
        user_perms = {
            perm.name for role in current_user.roles for perm in role.permissions
        }
        missing = required - user_perms
        if missing:
            raise PermissionDeniedError(
                f"Missing permissions: {', '.join(sorted(missing))}."
            )
        return current_user

    return _dep


# ---------- Pagination ----------

class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number, 1-indexed."),
        per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)."),
    ) -> None:
        self.page = page
        self.per_page = per_page
        self.offset = (page - 1) * per_page
        self.limit = per_page


Pagination = Annotated[PaginationParams, Depends()]
