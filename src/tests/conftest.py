"""pytest fixtures: a fresh in-memory database for every test.

We monkey-patch the application's engine + ``SessionLocal`` *before*
the FastAPI app is built so that the startup lifespan (which seeds
default RBAC and the first superuser) runs against the same in-memory
SQLite database that the tests query.
"""
from __future__ import annotations

import os

# Required env vars must be set before any application module is imported.
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("FIRST_SUPERUSER_EMAIL", "admin@example.com")
os.environ.setdefault("FIRST_SUPERUSER_USERNAME", "admin")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "AdminPass123!")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core import database as db_module
from src.core.app import create_app
from src.core.database import Base, get_db


@pytest.fixture()
def client(monkeypatch):
    # Build a fresh in-memory SQLite engine for this test
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Make sure model classes are registered on Base.metadata
    from src.apps.rbac import models as _rbac  # noqa: F401
    from src.apps.users import models as _users  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Patch the module-level engine + SessionLocal so the lifespan
    # bootstrap runs against this test database.
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSession)
    # The lifespan imports SessionLocal directly into its own module,
    # so we must patch it there too.
    from src.core import lifespan as lifespan_module
    monkeypatch.setattr(lifespan_module, "SessionLocal", TestingSession, raising=False)
    monkeypatch.setattr(lifespan_module, "engine", engine, raising=False)

    app = create_app()

    def _get_db_override():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
