"""CRUD operations for roles and permissions."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.apps.rbac import schemas
from src.apps.rbac.models import Permission, Role
from src.core.database import remove, save
from src.core.exceptions import AlreadyExistsError, NotFoundError


# ---------- Permissions ----------

def list_permissions(db: Session, *, offset: int, limit: int) -> list[Permission]:
    return list(db.scalars(select(Permission).offset(offset).limit(limit)))


def get_permission(db: Session, permission_id: int) -> Permission:
    permission = db.get(Permission, permission_id)
    if permission is None:
        raise NotFoundError("Permission not found.")
    return permission


def get_permission_by_name(db: Session, name: str) -> Permission | None:
    return db.scalar(select(Permission).where(Permission.name == name))


def create_permission(db: Session, data: schemas.PermissionCreate) -> Permission:
    if get_permission_by_name(db, data.name):
        raise AlreadyExistsError(f"Permission '{data.name}' already exists.")
    return save(db, Permission(name=data.name, description=data.description))


def delete_permission(db: Session, permission_id: int) -> None:
    remove(db, get_permission(db, permission_id))


# ---------- Roles ----------

def list_roles(db: Session, *, offset: int, limit: int) -> list[Role]:
    return list(db.scalars(select(Role).offset(offset).limit(limit)))


def get_role(db: Session, role_id: int) -> Role:
    role = db.get(Role, role_id)
    if role is None:
        raise NotFoundError("Role not found.")
    return role


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))


def create_role(db: Session, data: schemas.RoleCreate) -> Role:
    if get_role_by_name(db, data.name):
        raise AlreadyExistsError(f"Role '{data.name}' already exists.")

    role = Role(name=data.name, description=data.description)
    if data.permission_ids:
        role.permissions = _resolve_permissions(db, data.permission_ids)
    return save(db, role)


def update_role(db: Session, role_id: int, data: schemas.RoleUpdate) -> Role:
    """Apply a PATCH payload to a role.

    Uses ``model_dump(exclude_unset=True)`` so that omitted fields are
    untouched and a client can clear ``description`` by sending null.
    """
    role = get_role(db, role_id)
    updates = data.model_dump(exclude_unset=True)

    # ``permission_ids`` is not a column — resolve to Role <-> Permission rows.
    permission_ids = updates.pop("permission_ids", None)

    for field, value in updates.items():
        setattr(role, field, value)

    if permission_ids is not None:
        role.permissions = _resolve_permissions(db, permission_ids)

    return save(db, role)


def delete_role(db: Session, role_id: int) -> None:
    remove(db, get_role(db, role_id))


def _resolve_permissions(db: Session, ids: list[int]) -> list[Permission]:
    permissions = list(db.scalars(select(Permission).where(Permission.id.in_(ids))))
    if len(permissions) != len(set(ids)):
        raise NotFoundError("One or more permissions not found.")
    return permissions
