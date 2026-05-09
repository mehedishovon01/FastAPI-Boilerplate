"""Seed the database with default roles and permissions on startup."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.apps.rbac import service
from src.apps.rbac.models import Role
from src.apps.rbac.schemas import PermissionCreate, RoleCreate

logger = logging.getLogger(__name__)

DEFAULT_PERMISSIONS: list[tuple[str, str]] = [
    ("read_user", "Read user details"),
    ("create_user", "Create users"),
    ("update_user", "Update users"),
    ("delete_user", "Delete users"),
    ("read_rbac", "Read roles and permissions"),
    ("manage_rbac", "Create/update/delete roles and permissions"),
]

DEFAULT_ROLES: dict[str, list[str]] = {
    "admin": [name for name, _ in DEFAULT_PERMISSIONS],
    "user": ["read_user"],
}


def bootstrap_default_rbac(db: Session) -> None:
    """Idempotently create the standard set of roles and permissions."""
    perm_lookup = {}
    for name, description in DEFAULT_PERMISSIONS:
        existing = service.get_permission_by_name(db, name)
        if existing is None:
            existing = service.create_permission(
                db, PermissionCreate(name=name, description=description)
            )
            logger.info("Seeded permission '%s'", name)
        perm_lookup[name] = existing

    for role_name, perm_names in DEFAULT_ROLES.items():
        role = service.get_role_by_name(db, role_name)
        if role is None:
            permission_ids = [perm_lookup[p].id for p in perm_names]
            service.create_role(
                db,
                RoleCreate(
                    name=role_name,
                    description=f"Default '{role_name}' role.",
                    permission_ids=permission_ids,
                ),
            )
            logger.info("Seeded role '%s'", role_name)
        else:
            _sync_permissions(db, role, perm_names, perm_lookup)


def _sync_permissions(
    db: Session,
    role: Role,
    perm_names: list[str],
    perm_lookup: dict,
) -> None:
    """Make sure the existing role has at least the default permissions."""
    current = {p.name for p in role.permissions}
    missing = set(perm_names) - current
    if missing:
        for name in missing:
            role.permissions.append(perm_lookup[name])
        db.commit()
