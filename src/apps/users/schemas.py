from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.apps.rbac.schemas import RoleRead


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str | None = Field(None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


# PATCH input DTOs.
#
# Every field is Optional so that a client can send only what it wants
# to change. The service layer uses ``model_dump(exclude_unset=True)``
# to tell "field omitted" apart from "field set to null" — so a client
# can clear a nullable column with ``{"full_name": null}``.
#
# Inheritance encodes "who is allowed to change what":
#
#     UserSelfUpdate  ── only what a user may change about themself
#         └── UserUpdate            (+ admin-only: is_active)
#                 └── UserAdminUpdate (+ is_superuser, role_ids)


class UserSelfUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=255)


class UserUpdate(UserSelfUpdate):
    is_active: bool | None = None


class UserAdminUpdate(UserUpdate):
    is_superuser: bool | None = None
    role_ids: list[int] | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: list[RoleRead] = []
