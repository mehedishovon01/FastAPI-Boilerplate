"""HTTP endpoints for managing roles and permissions.

All RBAC management endpoints require the ``manage_rbac`` permission
(or superuser). Read endpoints require ``read_rbac``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.apps.rbac import schemas, service
from src.core.dependencies import DbSession, Pagination, require_permission

router = APIRouter(prefix="/rbac", tags=["RBAC"])


# ---------- Permissions ----------

@router.get(
    "/permissions",
    response_model=list[schemas.PermissionRead],
    dependencies=[Depends(require_permission("read_rbac"))],
    summary="List all permissions",
)
def list_permissions(db: DbSession, pagination: Pagination):
    return service.list_permissions(db, offset=pagination.offset, limit=pagination.limit)


@router.post(
    "/permissions",
    response_model=schemas.PermissionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("manage_rbac"))],
    summary="Create a new permission",
)
def create_permission(payload: schemas.PermissionCreate, db: DbSession):
    return service.create_permission(db, payload)


@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("manage_rbac"))],
    summary="Delete a permission",
)
def delete_permission(permission_id: int, db: DbSession):
    service.delete_permission(db, permission_id)


# ---------- Roles ----------

@router.get(
    "/roles",
    response_model=list[schemas.RoleRead],
    dependencies=[Depends(require_permission("read_rbac"))],
    summary="List all roles",
)
def list_roles(db: DbSession, pagination: Pagination):
    return service.list_roles(db, offset=pagination.offset, limit=pagination.limit)


@router.get(
    "/roles/{role_id}",
    response_model=schemas.RoleRead,
    dependencies=[Depends(require_permission("read_rbac"))],
    summary="Get a single role",
)
def get_role(role_id: int, db: DbSession):
    return service.get_role(db, role_id)


@router.post(
    "/roles",
    response_model=schemas.RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("manage_rbac"))],
    summary="Create a new role",
)
def create_role(payload: schemas.RoleCreate, db: DbSession):
    return service.create_role(db, payload)


@router.patch(
    "/roles/{role_id}",
    response_model=schemas.RoleRead,
    dependencies=[Depends(require_permission("manage_rbac"))],
    summary="Update a role",
)
def update_role(role_id: int, payload: schemas.RoleUpdate, db: DbSession):
    return service.update_role(db, role_id, payload)


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("manage_rbac"))],
    summary="Delete a role",
)
def delete_role(role_id: int, db: DbSession):
    service.delete_role(db, role_id)
