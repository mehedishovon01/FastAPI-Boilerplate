"""SQLAlchemy 2.0 engine, session factory, and declarative Base.

We use the *synchronous* SQLAlchemy API for simplicity. FastAPI happily
runs sync DB calls in a thread pool, and the modern 2.0 API + typed
``Mapped[...]`` columns gives a great developer experience without the
extra cognitive load of async sessions.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import TypeVar

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.core.config import settings


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    """Project-wide declarative base.

    Adds ``created_at`` / ``updated_at`` columns to every model so we
    don't have to repeat them everywhere.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Reusable persistence helpers ----------
#
# Almost every service ends in some variation of:
#
#     db.add(obj)
#     db.commit()
#     db.refresh(obj)
#
# These helpers express that intent in one line so service code stays
# focused on *what* it's doing instead of the boilerplate of *how* to
# persist it.

ModelT = TypeVar("ModelT", bound="Base")


def save(db: Session, obj: ModelT) -> ModelT:
    """Persist ``obj`` (insert OR update) and return the refreshed instance.

    ``db.add()`` is a no-op for objects already attached to the session,
    so this works for both newly created and modified entities.
    """
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def save_all(db: Session, objs: list[ModelT]) -> list[ModelT]:
    """Bulk version of :func:`save` — one commit for the whole batch."""
    db.add_all(objs)
    db.commit()
    for obj in objs:
        db.refresh(obj)
    return objs


def remove(db: Session, obj: ModelT) -> None:
    """Delete ``obj`` and commit."""
    db.delete(obj)
    db.commit()
