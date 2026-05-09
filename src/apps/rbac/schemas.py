from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["delete_user"])
    description: str | None = Field(None, max_length=255)


class PermissionCreate(PermissionBase):
    pass


class PermissionRead(PermissionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class RoleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, examples=["editor"])
    description: str | None = Field(None, max_length=255)


class RoleCreate(RoleBase):
    permission_ids: list[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    description: str | None = Field(None, max_length=255)
    permission_ids: list[int] | None = None


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionRead] = []
