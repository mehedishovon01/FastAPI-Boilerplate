"""User-management endpoints.

* ``/users/me`` — endpoints for the currently logged-in user.
* ``/users``    — admin-only endpoints for managing other users.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from src.utils.pagination import Page
from src.apps.users import schemas, service
from src.core.dependencies import (
    CurrentUser,
    DbSession,
    Pagination,
    require_permission,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ---------- Self-service ----------

@router.get(
    "/me",
    response_model=schemas.UserRead,
    summary="Get the currently authenticated user",
)
def read_me(current_user: CurrentUser):
    return current_user


@router.patch(
    "/me",
    response_model=schemas.UserRead,
    summary="Update the currently authenticated user",
)
def update_me(payload: schemas.UserSelfUpdate, db: DbSession, current_user: CurrentUser):
    # ``UserSelfUpdate`` deliberately omits ``is_active``/``is_superuser``/
    # ``role_ids`` — users cannot grant themselves powers or deactivate
    # their own account through this endpoint.
    return service.update_user(db, current_user, payload)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current user's password",
)
def change_my_password(
    payload: schemas.PasswordChange, db: DbSession, current_user: CurrentUser
):
    service.change_password(db, current_user, payload)


# ---------- Admin ----------

@router.get(
    "",
    response_model=Page[schemas.UserRead],
    dependencies=[Depends(require_permission("read_user"))],
    summary="List users (admin)",
)
def list_users(db: DbSession, pagination: Pagination):
    items = service.list_users(db, offset=pagination.offset, limit=pagination.limit)
    total = service.count_users(db)
    return Page.build(
        items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
    )


@router.get(
    "/{user_id}",
    response_model=schemas.UserRead,
    dependencies=[Depends(require_permission("read_user"))],
    summary="Get a user by id (admin)",
)
def get_user(user_id: int, db: DbSession):
    return service.get_user(db, user_id)


@router.patch(
    "/{user_id}",
    response_model=schemas.UserRead,
    dependencies=[Depends(require_permission("update_user"))],
    summary="Admin-update a user (roles, superuser, etc.)",
)
def admin_update_user(user_id: int, payload: schemas.UserAdminUpdate, db: DbSession):
    user = service.get_user(db, user_id)
    return service.admin_update_user(db, user, payload)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("delete_user"))],
    summary="Delete a user (admin)",
)
def delete_user(user_id: int, db: DbSession):
    service.delete_user(db, user_id)
