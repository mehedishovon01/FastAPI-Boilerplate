# FastAPI Boilerplate

A clean, modular, production-shaped FastAPI starter — JWT auth, RBAC,
SQLAlchemy 2.0, Alembic, and a passing test suite — built so that the
*shape* of the project teaches you good FastAPI patterns by example.

## Documentation map

This file is the project overview. Everything else lives in:

| Doc                                   | What's in it                                                                            |
|---------------------------------------|------------------------------------------------------------------------------------------|
| **[Architecture](./Architecture.md)** | Request lifecycle, project layout, configuration, security, dependencies, app factory & lifespan, recipes for adding features, production checklist. |
| **[Models](./Models.md)**             | Database setup, the shared `Base`, persistence helpers, every ORM model, ER diagram, migrations workflow. |
| **[Schemas & APIs](./Schemas-and-APIs.md)** | Every Pydantic schema, the full HTTP API reference, default seed data, PATCH/PUT/pagination design recipes. |

If you only have 30 minutes, read them in that order.

## What's included

- **Auth** — register, login (OAuth2 password flow with username **or** email), JWT access + refresh tokens, password reset by email.
- **Users** — `/users/me` self-service endpoints + admin user management (with role assignment).
- **RBAC** — roles & permissions, plus a `require_permission(...)` dependency that's trivial to compose on any route. Superusers automatically pass every check.
- **SQLAlchemy 2.0** — modern `Mapped[...]` declarative models. Shared `Base` adds `created_at` / `updated_at` to every table.
- **Alembic** — migrations wired up, including SQLite batch mode. Reads `DATABASE_URL` from settings.
- **Pydantic v2** — validated settings (the app fails fast on bad config), `ConfigDict(from_attributes=True)` schemas, type-safe end-to-end.
- **Tests** — `pytest` + `httpx.TestClient`, fresh in-memory SQLite per test, lifespan-aware seeding. **16 passing tests** covering health, auth, RBAC, and PATCH semantics.

## Tech stack

| Layer            | Choice                                               |
|------------------|------------------------------------------------------|
| Web framework    | FastAPI 0.115+                                       |
| Validation       | Pydantic 2 + pydantic-settings                       |
| ORM              | SQLAlchemy 2.0 (sync)                                |
| Migrations       | Alembic                                              |
| Auth             | PyJWT + bcrypt (no passlib, no python-jose)          |
| Tests            | pytest, httpx, fastapi.testclient                    |
| Default DB       | SQLite (PostgreSQL via `DATABASE_URL` env var)       |

## At-a-glance project shape

```
src/
├── main.py                 # ASGI entry point
├── api/v1/router.py        # Aggregates every app router
├── apps/                   # ← features live here, one folder each
│   ├── auth/               #     register, login, refresh, password reset
│   ├── users/              #     /users/me + admin user CRUD
│   └── rbac/               #     role/permission CRUD + dependencies
├── core/                   # config, database, security, lifespan, exceptions, ...
├── services/               # cross-cutting integrations with side effects (SMTP, ...)
├── utils/                  # pure helpers (Page[T] envelope, ...)
└── tests/
```

Each app has the same five files: `models.py`, `schemas.py`,
`service.py`, `router.py`, optional `bootstrap.py`. Adding a new
feature is "copy the folder, write your code". See
[Architecture → Adding a new app](./Architecture.md#adding-a-new-app-eg-posts).

## Why this rewrite exists

The original boilerplate had real bugs. This rewrite fixes them all
and ships a passing test suite that pins the new behaviour.

| Old problem                                                                                              | Fix                                                                           |
|----------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| Two competing `User` models (`src/models/user.py` + `src/apps/auth/models.py`) on the same table.        | One canonical `User` in `apps/users/models.py`; old files removed.            |
| Three competing auth routers (`routers/auth.py`, `apps/auth/routers.py`, `apps/auth/views.py`).          | One router per app, mounted via `api/v1/router.py`.                           |
| `core/app.py` referenced `schemas.PermissionCreate` without importing it.                                | Bootstrap moved to dedicated `apps/<x>/bootstrap.py` files.                   |
| Deprecated `@app.on_event("startup")`.                                                                   | Replaced with the `lifespan` async context manager.                           |
| RBAC middleware accessed `request.state.current_user` which was never set, and mixed two middleware styles. | RBAC implemented as composable `Depends(require_permission(...))`. Middleware deleted. |
| `pydantic<2` and `pydantic-settings>=2` declared together — a hard conflict.                             | Pydantic v2 throughout, with proper `ConfigDict(from_attributes=True)`.        |
| `passlib` + `python-jose` (both unmaintained, the latter has known CVEs).                                | `bcrypt` and `PyJWT` directly.                                                |
| Duplicated `[alembic]` and `[loggers]` sections in `alembic.ini`; folder named `alembic.` (with a stray period). | Clean `alembic.ini`, proper `alembic/` folder, `env.py` reads `DATABASE_URL` from settings. |
| `views.py` referenced `datetime.utcnow()` without importing `datetime`, and instantiated `AuthView()` at module level despite needing constructor args. | Plain function-based router, no fragile DI hacks.                             |
| Empty `tests/test_auth.py`.                                                                              | 16 tests covering health, auth, RBAC, and PATCH semantics — all passing.      |
| PATCH endpoints used `if data.x is not None:` — clients could never clear nullable fields.               | Switched to `model_dump(exclude_unset=True)`. Clients can now clear via `null`. |

That's the boilerplate. Read the code top-down starting at
`src/main.py` → `src/core/app.py` → `src/api/v1/router.py` → an app of
your choice, and you'll have the whole thing in your head in 30 minutes.
