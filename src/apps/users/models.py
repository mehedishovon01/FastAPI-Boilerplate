"""User model."""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.apps.rbac.models import Role, user_roles
from src.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"
