"""FastAPI lifespan: startup / shutdown hooks.

We use the modern ``lifespan`` context manager (the old
``@app.on_event("startup")`` API is deprecated).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import settings
from src.core.database import Base, SessionLocal, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up (env=%s)...", settings.ENVIRONMENT)

    # Local imports keep this file import-light and avoid circular deps.
    # Importing the model modules is what registers their tables on Base.metadata.
    from src.apps.rbac import models as _rbac_models  # noqa: F401
    from src.apps.users import models as _user_models  # noqa: F401
    from src.apps.rbac.bootstrap import bootstrap_default_rbac
    from src.apps.users.bootstrap import bootstrap_first_superuser

    # Convenience for local dev: auto-create tables when DEBUG is on,
    # so newcomers don't have to run alembic before their first request.
    # In production you should always use `alembic upgrade head`.
    if settings.DEBUG:
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        bootstrap_default_rbac(db)
        bootstrap_first_superuser(db)

    yield

    logger.info("Shutting down...")
