# Architecture

How the boilerplate is shaped, why it's shaped that way, and how a
request flows from the wire down to the database and back.

> Companion docs: **[Models](./Models.md)** • **[Schemas & APIs](./Schemas-and-APIs.md)** • **[Boilerplate overview](./BOILERPLATE.md)**

---

## 1. Request lifecycle (the mental model)

```
HTTP request
    │
    ▼
Uvicorn (ASGI server)
    │
    ▼
FastAPI app                    ──────  CORS middleware
    │                                 │
    ▼                                 ▼
APIRouter (/api/v1) ──► sub-router (/users) ──► path operation function
                                                 │
                                                 ▼
                          Dependency injection: get_db, get_current_user,
                                                require_permission, ...
                                                 │
                                                 ▼
                          Pydantic input validation (request body / query)
                                                 │
                                                 ▼
                          Service function (pure business logic, takes a Session)
                                                 │
                                                 ▼
                          SQLAlchemy 2.0 (queries the DB)
                                                 │
                                                 ▼
                          Response: ORM object → Pydantic schema → JSON
```

Every endpoint follows this layered shape:

| Layer        | File                                | Responsibility                                                |
|--------------|-------------------------------------|---------------------------------------------------------------|
| Router       | `apps/<x>/router.py`                | URL & HTTP method, response model, deps. *No* business logic. |
| Service      | `apps/<x>/service.py`               | **Domain** logic for this app. Pure functions that take a `Session` and do DB work. |
| Schema       | `apps/<x>/schemas.py`               | Pydantic v2 models for input/output.                          |
| Model        | `apps/<x>/models.py`                | SQLAlchemy 2.0 ORM classes.                                   |
| Bootstrap    | `apps/<x>/bootstrap.py` *(opt.)*    | One-time seed logic that runs in the lifespan.                |

This separation means you can call a service from a CLI, a worker, or a
test **without going through HTTP**.

### Three kinds of "shared code"

People conflate these all the time. Keep them in different folders so
the boundaries stay obvious:

| Kind                       | Lives in              | Side effects? | Owned by        | Example                                |
|----------------------------|-----------------------|---------------|-----------------|----------------------------------------|
| **Domain service**         | `apps/<x>/service.py` | Yes (DB)      | One app         | `users.service.authenticate(db, ...)`  |
| **Infrastructure service** | `src/services/`       | Yes (external) | Nobody / shared | `services.email.send_email(...)`       |
| **Pure utility**           | `src/utils/`          | **No**        | Nobody / shared | `utils.pagination.Page[UserRead]`      |

Quick decision tree when you're about to add new shared code:

1. *Does this talk to the database for one specific entity?* → it's a **domain service**, put it in `apps/<x>/service.py`.
2. *Does this talk to an external system (SMTP, Redis, S3, Stripe, ...)?* → it's an **infrastructure service**, put it in `src/services/`.
3. *Is it just a pure transformation of data with no I/O?* → it's a **utility**, put it in `src/utils/`.

If you find yourself wanting to put I/O code in `utils/`, stop —
that's a service. If you find a domain function being used by two
different apps, that's a sign you have a *third* domain hiding in the
overlap; extract it as a new app, don't promote it to `services/`.

---

## 2. Project layout

```
fastapi-boilerplate/
├── alembic/
│   ├── env.py                  # Reads Settings.DATABASE_URL
│   ├── script.py.mako          # Template for new migrations
│   └── versions/               # Generated migration scripts
├── alembic.ini
├── .env.example
├── requirements.txt
├── README.md
├── docx/                       # Project documentation
│   ├── BOILERPLATE.md          # ← project overview
│   ├── Architecture.md         # ← you are here
│   ├── Models.md
│   └── Schemas-and-APIs.md
└── src/
    ├── main.py                 # ASGI entry point
    ├── api/v1/router.py        # Aggregates every app router
    ├── apps/
    │   ├── auth/
    │   │   ├── router.py
    │   │   ├── service.py
    │   │   └── schemas.py
    │   ├── users/
    │   │   ├── bootstrap.py    # Creates the first superuser
    │   │   ├── models.py
    │   │   ├── router.py
    │   │   ├── schemas.py
    │   │   └── service.py
    │   └── rbac/
    │       ├── bootstrap.py    # Seeds default roles & permissions
    │       ├── models.py
    │       ├── router.py
    │       ├── schemas.py
    │       └── service.py
    ├── core/
    │   ├── app.py              # FastAPI factory: middleware, routers, exception handlers
    │   ├── config.py           # Pydantic Settings
    │   ├── database.py         # Engine, SessionLocal, Base, save(), remove()
    │   ├── dependencies.py     # get_current_user, require_permission, Pagination, ...
    │   ├── exceptions.py       # AppException tree + handlers
    │   ├── lifespan.py         # Startup/shutdown
    │   ├── logging.py          # Logging config
    │   └── security.py         # JWT + bcrypt
    ├── services/               # Cross-cutting infrastructure (have I/O)
    │   └── email.py            # SMTP wrapper
    ├── utils/                  # Pure helpers (no I/O, no DB, no env)
    │   └── pagination.py       # Page[T] response envelope
    └── tests/
        ├── conftest.py         # Fresh in-memory DB per test
        ├── test_auth.py
        ├── test_users.py
        └── test_rbac.py
```

### Why `apps/`?

Each app is a **bounded slice** of the domain. To add a new feature
(say `posts`), you create a new folder `src/apps/posts/` with the same
five files. Nothing else changes except mounting its router in
`src/api/v1/router.py`. This pattern scales from a side project to a
team product without restructuring.

---

## 3. Configuration

All settings live in one place: `src/core/config.py`. They are loaded
from environment variables (or `.env`) and validated by Pydantic at
import time, so the app **fails fast** if anything is missing or
malformed.

### Setting reference

| Setting                                | Type            | Default                       | Notes                                                                 |
|----------------------------------------|-----------------|-------------------------------|-----------------------------------------------------------------------|
| `PROJECT_NAME`                         | `str`           | `"FastAPI Boilerplate"`       | Shown in `/docs`.                                                     |
| `VERSION`                              | `str`           | `"1.0.0"`                     |                                                                       |
| `DESCRIPTION`                          | `str`           | …                             |                                                                       |
| `ENVIRONMENT`                          | `str`           | `"development"`               | One of `development`, `staging`, `production`.                        |
| `DEBUG`                                | `bool`          | `True`                        | Enables verbose logs and dev-only auto table creation.                |
| `API_V1_PREFIX`                        | `str`           | `/api/v1`                     |                                                                       |
| `HOST`                                 | `str`           | `0.0.0.0`                     |                                                                       |
| `PORT`                                 | `int`           | `8000`                        |                                                                       |
| `SECRET_KEY`                           | `str` *(req.)*  | —                             | **Min 32 chars.** Used to sign JWTs.                                  |
| `JWT_ALGORITHM`                        | `str`           | `HS256`                       |                                                                       |
| `ACCESS_TOKEN_EXPIRE_MINUTES`          | `int`           | `30`                          |                                                                       |
| `REFRESH_TOKEN_EXPIRE_DAYS`            | `int`           | `7`                           |                                                                       |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`  | `int`           | `60`                          |                                                                       |
| `BACKEND_CORS_ORIGINS`                 | `list[str]`     | `[]`                          | Comma-separated string in `.env` is auto-parsed into a list.          |
| `DATABASE_URL`                         | `str`           | `sqlite:///./app.db`          | Any SQLAlchemy URL. e.g. `postgresql+psycopg://user:pwd@host/db`.     |
| `FIRST_SUPERUSER_EMAIL`                | `EmailStr?`     | `None`                        | If set, a superuser is created on first startup.                      |
| `FIRST_SUPERUSER_USERNAME`             | `str?`          | `None`                        |                                                                       |
| `FIRST_SUPERUSER_PASSWORD`             | `str?`          | `None`                        |                                                                       |
| `SMTP_HOST` / `SMTP_PORT`              | `str?` / `int`  | `None` / `587`                | When unset, `send_email` logs the message instead of sending.         |
| `SMTP_USER` / `SMTP_PASSWORD`          | `str?` / `str?` | `None` / `None`               |                                                                       |
| `SMTP_TLS`                             | `bool`          | `True`                        |                                                                       |
| `EMAILS_FROM_EMAIL`                    | `EmailStr?`     | `None`                        |                                                                       |
| `EMAILS_FROM_NAME`                     | `str?`          | `None`                        |                                                                       |

### Pattern: the cached accessor

```67:73:src/core/config.py
@lru_cache
def get_settings() -> Settings:
    """Cached accessor so Settings() is only instantiated once per process."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
```

Importing `settings` is cheap and idempotent. Tests that need to swap
settings can call `get_settings.cache_clear()` between runs.

---

## 4. Security

### Passwords

We use the `bcrypt` package directly. The full API is two functions:

```python
def hash_password(password: str) -> str: ...
def verify_password(plain_password: str, hashed_password: str) -> bool: ...
```

Why not `passlib`? It is unmaintained and breaks with `bcrypt >= 4.1`,
which is the only currently maintained `bcrypt` package. Calling
`bcrypt` directly is one extra line of code for a much sturdier setup.

### JWT tokens

There are **three** token kinds, each marked with a `type` claim so you
can't, say, use a refresh token where an access token is required:

| `TokenType.ACCESS`         | Short-lived, sent on every request.                  |
| `TokenType.REFRESH`        | Long-lived, exchanged via `/auth/refresh`.           |
| `TokenType.PASSWORD_RESET` | One-shot, embedded in the password-reset email link. |

Helpers:

```python
create_access_token(subject)          -> str
create_refresh_token(subject)         -> str
create_password_reset_token(subject)  -> str
decode_token(token, expected_type=…)  -> dict   # raises jwt.PyJWTError on failure
access_token_expires_at()             -> datetime
```

The `subject` is always the user's primary key (as a string). Use a
UUID instead of an integer in production if you don't want to leak the
size of your user table.

---

## 5. Dependencies

`src/core/dependencies.py` is the **glue** of the whole app. It exports
both ready-to-use dependencies and *factories* that produce them.

### Plain dependencies

| Name                   | What it gives you                                   |
|------------------------|-----------------------------------------------------|
| `DbSession`            | A SQLAlchemy `Session` for the current request.     |
| `AccessToken`          | The raw bearer token string.                        |
| `CurrentUser`          | The authenticated `User`. Returns 401 if invalid.   |
| `Pagination`           | A `PaginationParams(page, per_page, offset, limit)` |

These are `typing.Annotated` aliases so endpoint signatures stay tiny:

```python
def list_users(db: DbSession, pagination: Pagination): ...
def read_me(current_user: CurrentUser): ...
```

### Factories

```python
require_role("admin")                       # any of these roles
require_permission("delete_user")           # ALL of these permissions
get_current_superuser                       # short-cut for is_superuser
```

Compose them into routes either in the decorator (when you don't need
the user object) or in the signature (when you do):

```python
@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_permission("delete_user"))],   # gate
)
def delete_user(user_id: int, db: DbSession): ...

@router.get("/admin/dashboard")
def dashboard(current: User = Depends(require_role("admin"))):   # gate + value
    ...
```

A `superuser` automatically passes every `require_role` and
`require_permission` check.

### Why dependencies instead of middleware?

The old code had an RBAC middleware that:

- Tried to read `request.state.current_user` (which was never set).
- Mixed Starlette's class-based ASGI signature with `BaseHTTPMiddleware` semantics.

Dependencies are strictly better here because:

- They run **after** path-routing, so they know which permission applies.
- They appear in the OpenAPI docs (you'll see the `Authorize` button).
- They are trivial to test (just call the function).
- They compose: any route can opt into any combination of role/permission checks.

### Pagination is split in two — on purpose

The pagination feature has *two* halves that live in two different files:

| Piece                                   | Lives in              | What it is                                  | Pure? |
|-----------------------------------------|-----------------------|---------------------------------------------|-------|
| `Pagination` (`PaginationParams`)       | `core/dependencies.py`| FastAPI request dependency (uses `Query()`) | No    |
| `Page[T]`                                | `utils/pagination.py` | Pydantic response schema                     | Yes   |

The dependency reads & validates query params from the *request*; the
`Page[T]` envelope shapes the *response*. Same feature, different
responsibilities, different folders. See [Schemas & APIs → Returning
paginated results with metadata](./Schemas-and-APIs.md#returning-paginated-results-with-metadata)
for the usage pattern.

---

## 6. Application factory & lifespan

### Factory — `src/core/app.py`

```python
def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(..., lifespan=lifespan)
    app.add_middleware(CORSMiddleware, ...)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    @app.get("/health", tags=["Health"])
    def health(): return {"status": "ok", "environment": settings.ENVIRONMENT}
    return app
```

### Lifespan — `src/core/lifespan.py`

The lifespan replaces the deprecated `@app.on_event("startup")` API:

1. Imports model modules so they register on `Base.metadata`.
2. **In DEBUG only**, runs `Base.metadata.create_all()` so beginners
   don't have to learn Alembic on day one.
3. Calls `bootstrap_default_rbac` and `bootstrap_first_superuser`.

### Exception handlers

A small hierarchy lets services raise meaningful errors without
knowing about HTTP:

```
AppException (400)
├── NotFoundError          (404)
├── AlreadyExistsError     (409)
├── AuthenticationError    (401)
├── PermissionDeniedError  (403)
└── InvalidTokenError      (401)
```

The handler turns any of these into:

```json
{ "detail": "<exc.detail>" }
```

`SQLAlchemyError` and `RequestValidationError` get their own catch-alls.

---

## 7. Common architectural recipes

### Adding a new app (e.g. `posts`)

1. `mkdir src/apps/posts && touch src/apps/posts/{__init__,models,schemas,service,router}.py`
2. Define your SQLAlchemy model in `models.py` (inheriting from `core.database.Base`).
3. Define `Create`/`Update`/`Read` schemas in `schemas.py`.
4. Write the service functions in `service.py` (each takes a `Session` plus pydantic input).
5. Build the router in `router.py`:

   ```python
   router = APIRouter(prefix="/posts", tags=["Posts"])

   @router.get("", response_model=list[schemas.PostRead])
   def list_posts(db: DbSession, pagination: Pagination):
       return service.list_posts(db, offset=pagination.offset, limit=pagination.limit)
   ```
6. Mount it in `src/api/v1/router.py`:

   ```python
   from src.apps.posts.router import router as posts_router
   api_router.include_router(posts_router)
   ```
7. Add the model import to `alembic/env.py` so autogenerate sees the table.
8. `alembic revision --autogenerate -m "add posts" && alembic upgrade head`.

### Adding a new permission

1. Append a tuple to `DEFAULT_PERMISSIONS` in `src/apps/rbac/bootstrap.py`.
2. Add it to the `admin` role list (and any other role that needs it).
3. Restart the app — the bootstrap is idempotent, the new permission is created and added to existing roles automatically.
4. Use it on a route: `Depends(require_permission("your_new_perm"))`.

### Switching to PostgreSQL

```bash
pip install "psycopg[binary]"
```

Then in `.env`:

```
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/app
```

Run `alembic upgrade head`. No code changes required.

### Issuing tokens manually (e.g. from a CLI script)

```python
from src.core.security import create_access_token, create_refresh_token

access  = create_access_token(user.id)
refresh = create_refresh_token(user.id)
```

### Calling a service from a script

```python
from src.core.database import SessionLocal
from src.apps.users.service import create_user
from src.apps.users.schemas import UserCreate

with SessionLocal() as db:
    create_user(db, UserCreate(email="x@y.com", username="x", password="StrongPass1!"))
```

No HTTP round-trip required — the service layer is the same code the
HTTP routes call.

### Writing your own test

```python
def test_something(client):
    res = client.post("/api/v1/auth/register", json={...})
    assert res.status_code == 201
```

The `client` fixture (in `tests/conftest.py`) gives you:

- An in-memory SQLite database, freshly seeded with the default RBAC + superuser.
- The FastAPI app with `get_db` overridden to use that database.

---

## 8. Production checklist

Before you deploy:

- [ ] Set a strong `SECRET_KEY` (≥ 64 random characters). **Rotate it on a schedule.**
- [ ] `ENVIRONMENT=production`, `DEBUG=false`.
- [ ] Switch `DATABASE_URL` to a real Postgres (or your DB of choice).
- [ ] Configure SMTP, or replace `services/email.py` with a transactional-email provider client (SES, Postmark, Resend, ...).
- [ ] Run migrations explicitly: `alembic upgrade head`. Disable the dev-only auto `create_all` (it's gated by `DEBUG`, but double-check).
- [ ] Set `BACKEND_CORS_ORIGINS` to the *exact* origins of your frontend(s).
- [ ] Add a request-id middleware for tracing (one extra middleware in `core/app.py`).
- [ ] Put the app behind HTTPS (Caddy, Nginx, or Traefik). FastAPI doesn't terminate TLS itself.
- [ ] Run with multiple workers in production: `uvicorn src.main:app --workers 4` *(or use Gunicorn with the uvicorn worker class)*.
- [ ] Add a real logging sink (JSON to stdout → ship to your platform).
- [ ] Wire `/health` (and possibly `/health/ready`) to your platform's healthcheck.
- [ ] Audit RBAC: which routes need which permission? The defaults are a starting point, not a final answer.
