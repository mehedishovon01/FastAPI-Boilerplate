"""User CRUD operations."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.apps.rbac import service as rbac_service
from src.apps.users import schemas
from src.apps.users.models import User
from src.core.database import remove, save
from src.core.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from src.core.security import hash_password, verify_password


def list_users(db: Session, *, offset: int, limit: int) -> list[User]:
    return list(db.scalars(select(User).offset(offset).limit(limit)))


def count_users(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(User)) or 0)


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def authenticate(db: Session, *, login: str, password: str) -> User:
    """Look up by username *or* email, then verify the password."""
    user = get_user_by_username(db, login) or get_user_by_email(db, login)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Incorrect username/email or password.")
    if not user.is_active:
        raise AuthenticationError("User account is inactive.")
    return user


def create_user(
    db: Session,
    data: schemas.UserCreate,
    *,
    is_superuser: bool = False,
    default_role: str | None = "user",
) -> User:
    if get_user_by_email(db, data.email):
        raise AlreadyExistsError("Email already registered.")
    if get_user_by_username(db, data.username):
        raise AlreadyExistsError("Username already taken.")

    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_superuser=is_superuser,
    )
    if default_role:
        role = rbac_service.get_role_by_name(db, default_role)
        if role is not None:
            user.roles.append(role)

    return save(db, user)


def update_user(db: Session, user: User, data: schemas.UserUpdate) -> User:
    """Apply a PATCH payload to ``user``.

    ``model_dump(exclude_unset=True)`` returns *only the fields the
    client actually sent*, so omitted fields are left alone and an
    explicit ``null`` correctly clears a nullable column.
    """
    updates = data.model_dump(exclude_unset=True)

    if "email" in updates and updates["email"] != user.email:
        if get_user_by_email(db, updates["email"]):
            raise AlreadyExistsError("Email already in use.")

    for field, value in updates.items():
        setattr(user, field, value)

    return save(db, user)


def admin_update_user(db: Session, user: User, data: schemas.UserAdminUpdate) -> User:
    """Same PATCH semantics as :func:`update_user`, plus role assignment."""
    updates = data.model_dump(exclude_unset=True)

    if "email" in updates and updates["email"] != user.email:
        if get_user_by_email(db, updates["email"]):
            raise AlreadyExistsError("Email already in use.")

    # ``role_ids`` needs special handling: resolve IDs → Role objects.
    role_ids = updates.pop("role_ids", None)

    for field, value in updates.items():
        setattr(user, field, value)

    if role_ids is not None:
        user.roles = [rbac_service.get_role(db, rid) for rid in role_ids]

    return save(db, user)


def change_password(db: Session, user: User, data: schemas.PasswordChange) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise AuthenticationError("Current password is incorrect.")
    user.hashed_password = hash_password(data.new_password)
    save(db, user)


def set_password(db: Session, user: User, new_password: str) -> None:
    user.hashed_password = hash_password(new_password)
    save(db, user)


def delete_user(db: Session, user_id: int) -> None:
    remove(db, get_user(db, user_id))
