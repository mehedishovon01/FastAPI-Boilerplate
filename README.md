# FastAPI Boilerplate

A clean, modular, production-ready FastAPI starter with JWT auth, RBAC,
SQLAlchemy 2.0, Alembic migrations, and a test suite.

> See **[BOILERPLATE.md](./BOILERPLATE.md)** for the full architecture
> walkthrough — every model, schema, endpoint, dependency, and design
> decision is documented there.

## Features

- **Auth** — Register, login (OAuth2 password flow), JWT access + refresh tokens, password reset by email.
- **Users** — `/me` self-service endpoints + admin user management.
- **RBAC** — Roles & permissions with a `require_permission(...)` dependency that's trivial to compose on any route.
- **SQLAlchemy 2.0** — Modern `Mapped[...]` declarative models with a shared `Base` that adds `created_at` / `updated_at`.
- **Alembic** — Migrations wired up, including SQLite batch mode.
- **Pydantic v2** — Validated settings, `from_attributes` schemas, type-safe end-to-end.
- **Tests** — `pytest` + `httpx.TestClient`, in-memory SQLite, lifespan-aware seeding.

## Tech Stack

| Layer            | Choice                                               |
|------------------|------------------------------------------------------|
| Web framework    | FastAPI 0.115+                                       |
| Validation       | Pydantic 2 + pydantic-settings                       |
| ORM              | SQLAlchemy 2.0 (sync)                                |
| Migrations       | Alembic                                              |
| Auth             | PyJWT + bcrypt (no passlib, no python-jose)          |
| Tests            | pytest, httpx, fastapi.testclient                    |
| Default DB       | SQLite (PostgreSQL via `DATABASE_URL` env var)       |

## Quick Start

```bash
git clone https://github.com/mehedishovon01/FastAPI-Boilerplate.git
cd FastAPI-Boilerplate

python -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set a SECRET_KEY of 32+ characters

uvicorn src.main:app --reload
```

Open the docs:

- Swagger UI &mdash; <http://localhost:8000/docs>
- ReDoc       &mdash; <http://localhost:8000/redoc>

## Database Migrations

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

> In `DEBUG=true` mode the lifespan auto-creates tables on startup so
> beginners can skip Alembic on day one. In production always rely on
> migrations.

## Running the Tests

```bash
pytest -v
```

A fresh in-memory SQLite database is created per test, the lifespan
runs against it, and a `TestClient` is yielded with the DB dependency
already overridden.

## Project Layout

```
fastapi-boilerplate/
├── alembic/                # Alembic env + migration scripts
├── src/
│   ├── api/v1/router.py    # Aggregates every app router
│   ├── apps/
│   │   ├── auth/           # Login, register, refresh, password reset
│   │   ├── users/          # User entity + /me + admin user mgmt
│   │   └── rbac/           # Role / Permission / RBAC dependencies
│   ├── core/
│   │   ├── app.py          # FastAPI factory
│   │   ├── config.py       # Pydantic settings
│   │   ├── database.py     # Engine, SessionLocal, Base
│   │   ├── dependencies.py # get_current_user, require_permission, ...
│   │   ├── exceptions.py   # Custom exceptions + handlers
│   │   ├── lifespan.py     # Startup/shutdown
│   │   ├── logging.py      # Logging config
│   │   └── security.py     # JWT + password hashing
│   ├── services/           # Cross-cutting infrastructure (have I/O)
│   │   └── email.py        # SMTP wrapper
│   ├── utils/              # Pure helpers (no I/O, no DB)
│   │   └── pagination.py   # Page[T] response envelope
│   ├── tests/              # pytest suite
│   └── main.py             # ASGI entry point
├── alembic.ini
├── requirements.txt
├── README.md
└── BOILERPLATE.md          # Detailed architecture & API docs
```

## License

MIT — see [LICENSE](./LICENSE).
