"""Create the first superuser on startup if configured."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.apps.rbac import service as rbac_service
from src.apps.users import service as users_service
from src.apps.users.schemas import UserCreate
from src.core.config import settings

logger = logging.getLogger(__name__)


def bootstrap_first_superuser(db: Session) -> None:
    if not (
        settings.FIRST_SUPERUSER_EMAIL
        and settings.FIRST_SUPERUSER_USERNAME
        and settings.FIRST_SUPERUSER_PASSWORD
    ):
        return

    existing = users_service.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
    if existing is not None:
        return

    user = users_service.create_user(
        db,
        UserCreate(
            email=settings.FIRST_SUPERUSER_EMAIL,
            username=settings.FIRST_SUPERUSER_USERNAME,
            full_name="Initial Superuser",
            password=settings.FIRST_SUPERUSER_PASSWORD,
        ),
        is_superuser=True,
        default_role=None,
    )
    admin_role = rbac_service.get_role_by_name(db, "admin")
    if admin_role is not None and admin_role not in user.roles:
        user.roles.append(admin_role)
        db.commit()
    logger.warning(
        "Created first superuser '%s'. Change the password ASAP!",
        user.username,
    )
