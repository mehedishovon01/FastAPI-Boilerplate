# FastAPI Boilerplate — Architecture, Models, Schemas & APIs

This document is the **single source of truth** for what is in this
boilerplate, *why* it is shaped this way, and *how* every endpoint,
model, and schema fits together.

It is written in the order I'd want a learner to read it:

1. The mental model (request lifecycle)
2. Project layout
3. Configuration
4. Database & models
5. Schemas (Pydantic)
6. Security (passwords + JWT)
7. Dependencies (DB, current user, RBAC, pagination)
8. The application factory & lifespan
9. The full API reference (endpoint → schema)
10. Default seed data (roles, permissions, superuser)
11. Common recipes ("how do I add a new app?")
12. Production checklist

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

Every endpoint in this boilerplate follows this layered shape:

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
├── BOILERPLATE.md              # ← you are here
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
    │   ├── database.py         # Engine, SessionLocal, Base
    │   ├── dependencies.py     # get_current_user, require_permission, Pagination, ...
    │   ├── exceptions.py       # AppException tree + handlers
    │   ├── lifespan.py         # Startup/shutdown
    │   ├── logging.py          # Logging config
    │   └── security.py         # JWT + bcrypt
    ├── services/                # Cross-cutting infrastructure services (have I/O)
    │   └── email.py             # SMTP wrapper
    ├── utils/                   # Pure helpers (no I/O, no DB, no env)
    │   └── pagination.py        # Page[T] response envelope
    └── tests/
        ├── conftest.py          # Fresh in-memory DB per test
        ├── test_auth.py
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

## 4. Database & models

### The engine + session

```22:24:src/core/database.py
engine = create_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
```

`get_db` is a generator-style FastAPI dependency that opens a session,
yields it, and closes it after the response is sent.

### The shared `Base`

```27:44:src/core/database.py
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
```

Every model in the project automatically gets timestamp columns — you
do **not** repeat `created_at`/`updated_at` per table.

### Models

#### `User` — `src/apps/users/models.py`

| Column            | Type            | Constraints                       |
|-------------------|-----------------|-----------------------------------|
| `id`              | `int`           | PK, indexed                       |
| `email`           | `str(255)`      | unique, indexed, not null         |
| `username`        | `str(64)`       | unique, indexed, not null         |
| `full_name`       | `str(255)?`     | nullable                          |
| `hashed_password` | `str(255)`      | not null (bcrypt hash)            |
| `is_active`       | `bool`          | default `True`                    |
| `is_superuser`    | `bool`          | default `False`                   |
| `created_at`     *(from Base)* |||
| `updated_at`     *(from Base)* |||
| `roles`           | `list[Role]`    | many-to-many via `user_roles`     |

#### `Role` — `src/apps/rbac/models.py`

| Column          | Type             | Constraints                 |
|-----------------|------------------|-----------------------------|
| `id`            | `int`            | PK, indexed                 |
| `name`          | `str(50)`        | unique, indexed             |
| `description`   | `str(255)?`      | nullable                    |
| `permissions`   | `list[Permission]` | many-to-many via `role_permissions` |
| `users`         | `list[User]`     | many-to-many via `user_roles` |

#### `Permission` — `src/apps/rbac/models.py`

| Column          | Type        | Constraints     |
|-----------------|-------------|-----------------|
| `id`            | `int`       | PK, indexed     |
| `name`          | `str(100)`  | unique, indexed |
| `description`   | `str(255)?` | nullable        |
| `roles`         | `list[Role]`| many-to-many    |

#### Association tables

| Table              | Columns                            |
|--------------------|------------------------------------|
| `user_roles`       | `user_id` ↔ `role_id`              |
| `role_permissions` | `role_id` ↔ `permission_id`        |

Both use `ondelete=CASCADE` so deleting a user/role/permission cleanly
removes its associations.

### Why sync, not async?

Because async SQLAlchemy adds real cognitive overhead (greenlets,
async sessions, async relationships) and gives **no measurable
benefit** for IO-bound workloads up to a few hundred RPS. FastAPI runs
sync DB calls in a threadpool transparently. When you outgrow that,
swap `create_engine`/`Session` for `create_async_engine`/`AsyncSession`
and add `await` everywhere — the rest of the architecture is unchanged.

---

## 5. Schemas (Pydantic v2)

Each app declares its own input/output models. Convention:

| Suffix       | Purpose                                          |
|--------------|--------------------------------------------------|
| `…Base`      | Fields shared by Create / Read / Update.         |
| `…Create`    | What the client sends to create the resource.    |
| `…Update`    | What the client sends to patch the resource.     |
| `…Read`      | What the API returns. `model_config = ConfigDict(from_attributes=True)` so it can serialize ORM objects directly. |

### Auth schemas — `src/apps/auth/schemas.py`

```python
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime

class AccessTokenOnly(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

class RefreshRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
```

### User schemas — `src/apps/users/schemas.py`

| Schema             | Fields                                                                                     |
|--------------------|--------------------------------------------------------------------------------------------|
| `UserBase`         | `email`, `username` (3–64, regex `^[A-Za-z0-9_.-]+$`), `full_name?`                        |
| `UserCreate`       | `UserBase` + `password` (8–128)                                                            |
| `UserSelfUpdate`   | `email?`, `full_name?`  *(what a user can change about themself)*                           |
| `UserUpdate`       | `UserSelfUpdate` + `is_active?`  *(admin can also toggle active)*                           |
| `UserAdminUpdate`  | `UserUpdate` + `is_superuser?`, `role_ids?`  *(full admin power)*                           |
| `PasswordChange`   | `current_password`, `new_password`                                                         |
| `UserRead`         | `UserBase` + `id`, `is_active`, `is_superuser`, `created_at`, `updated_at`, `roles[RoleRead]` |

### RBAC schemas — `src/apps/rbac/schemas.py`

| Schema             | Fields                                                                       |
|--------------------|------------------------------------------------------------------------------|
| `PermissionBase`   | `name` (2–100), `description?` (≤255)                                        |
| `PermissionCreate` | `PermissionBase`                                                             |
| `PermissionRead`   | `PermissionBase` + `id`, `created_at`, `updated_at`                          |
| `RoleBase`         | `name` (2–50), `description?` (≤255)                                         |
| `RoleCreate`       | `RoleBase` + `permission_ids: list[int]`                                     |
| `RoleUpdate`       | `description?`, `permission_ids?` *(only the fields you want to change)*     |
| `RoleRead`         | `RoleBase` + `id`, `created_at`, `updated_at`, `permissions[PermissionRead]` |

---

## 6. Security

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

## 7. Dependencies

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

---

## 8. Application factory & lifespan

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

## 9. API reference

> Base URL: `/api/v1` &nbsp; (configurable via `API_V1_PREFIX`)
> All endpoints below are also browsable at `GET /docs`.

### Health (no auth)

| Method | Path        | Response                                       |
|--------|-------------|------------------------------------------------|
| GET    | `/health`   | `{"status": "ok", "environment": "..."}`       |

### Auth — `/api/v1/auth`

| Method | Path                          | Request body                | Response (201/200)            | Auth |
|--------|-------------------------------|------------------------------|-------------------------------|------|
| POST   | `/auth/register`              | `UserCreate`                 | `UserRead` (201)              | —    |
| POST   | `/auth/login`                 | `application/x-www-form-urlencoded` (`username`, `password`) | `TokenPair` | — |
| POST   | `/auth/refresh`               | `RefreshRequest`             | `AccessTokenOnly`             | —    |
| POST   | `/auth/password-reset/request`| `PasswordResetRequest`       | `{"detail": "..."}` (202)     | —    |
| POST   | `/auth/password-reset/confirm`| `PasswordResetConfirm`       | _(204 No Content)_            | —    |

#### Examples

**Register**

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "alice@example.com",
  "username": "alice",
  "full_name": "Alice",
  "password": "SuperSecret1!"
}
```

**Login** *(OAuth2 password flow — username can be username **or** email)*

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=alice&password=SuperSecret1!
```

Response:

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_at": "2026-05-09T18:30:00+00:00"
}
```

### Users — `/api/v1/users`

#### Self-service (any authenticated user)

| Method | Path                        | Body              | Response  |
|--------|-----------------------------|-------------------|-----------|
| GET    | `/users/me`                 | —                 | `UserRead`|
| PATCH  | `/users/me`                 | `UserSelfUpdate`  | `UserRead`|
| POST   | `/users/me/change-password` | `PasswordChange`  | 204       |

#### Admin (gated by RBAC permissions)

| Method  | Path              | Body              | Response             | Required permission |
|---------|-------------------|-------------------|----------------------|---------------------|
| GET     | `/users`          | _(query: `page`, `per_page`)_ | `Page[UserRead]` | `read_user`     |
| GET     | `/users/{id}`     | —                 | `UserRead`           | `read_user`         |
| PATCH   | `/users/{id}`     | `UserAdminUpdate` | `UserRead`           | `update_user`       |
| DELETE  | `/users/{id}`     | —                 | 204                  | `delete_user`       |

### RBAC — `/api/v1/rbac`

#### Permissions

| Method | Path                              | Body                | Response               | Required permission |
|--------|-----------------------------------|---------------------|------------------------|---------------------|
| GET    | `/rbac/permissions`               | _(paginated)_       | `list[PermissionRead]` | `read_rbac`         |
| POST   | `/rbac/permissions`               | `PermissionCreate`  | `PermissionRead` (201) | `manage_rbac`       |
| DELETE | `/rbac/permissions/{id}`          | —                   | 204                    | `manage_rbac`       |

#### Roles

| Method | Path                            | Body         | Response          | Required permission |
|--------|---------------------------------|--------------|-------------------|---------------------|
| GET    | `/rbac/roles`                   | _(paginated)_| `list[RoleRead]`  | `read_rbac`         |
| GET    | `/rbac/roles/{id}`              | —            | `RoleRead`        | `read_rbac`         |
| POST   | `/rbac/roles`                   | `RoleCreate` | `RoleRead` (201)  | `manage_rbac`       |
| PATCH  | `/rbac/roles/{id}`              | `RoleUpdate` | `RoleRead`        | `manage_rbac`       |
| DELETE | `/rbac/roles/{id}`              | —            | 204               | `manage_rbac`       |

#### Standard query parameters

Any list endpoint accepts:

| Param      | Type | Default | Notes                      |
|------------|------|---------|----------------------------|
| `page`     | int  | `1`     | 1-indexed.                 |
| `per_page` | int  | `20`    | Min `1`, max `100`.        |

#### Standard error envelope

Every error returned by the API has the same shape:

```json
{ "detail": "Human-readable explanation." }
```

For 422 validation errors, `detail` is the list of Pydantic errors:

```json
{ "detail": [{ "type": "...", "loc": ["body", "email"], "msg": "..." }] }
```

---

## 10. Default seed data

On the first startup the lifespan creates:

### Permissions

| Name           | Description                                |
|----------------|--------------------------------------------|
| `read_user`    | Read user details                          |
| `create_user`  | Create users                               |
| `update_user`  | Update users                               |
| `delete_user`  | Delete users                               |
| `read_rbac`    | Read roles and permissions                 |
| `manage_rbac`  | Create/update/delete roles and permissions |

### Roles

| Role     | Permissions                |
|----------|----------------------------|
| `admin`  | *(all of the above)*       |
| `user`   | `read_user`                |

### First superuser

Created **only if** all three of these env vars are set:

```
FIRST_SUPERUSER_EMAIL
FIRST_SUPERUSER_USERNAME
FIRST_SUPERUSER_PASSWORD
```

The user is given `is_superuser=True` *and* the `admin` role, and the
boilerplate logs a warning telling you to change the password.

---

## 11. Common recipes

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

### Writing a PATCH endpoint that does the right thing

Always model PATCH inputs with **all fields Optional**, then apply
them with `model_dump(exclude_unset=True)`:

```python
class WidgetPatch(BaseModel):
    name:        str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)   # nullable in DB
    color:       str | None = None

def update_widget(db: Session, widget: Widget, data: WidgetPatch) -> Widget:
    updates = data.model_dump(exclude_unset=True)
    # ...any pre-update validation (uniqueness, etc.)...
    for field, value in updates.items():
        setattr(widget, field, value)
    return save(db, widget)
```

`exclude_unset=True` is the magic: it returns *only the fields the
client actually sent*. So:

| Client sends            | Result                                    |
|-------------------------|--------------------------------------------|
| `{}`                    | No fields touched.                         |
| `{"name": "Bob"}`       | `name` → `"Bob"`, others untouched.        |
| `{"description": null}` | `description` → `NULL` in the DB.          |

The classic anti-pattern is `if data.field is not None: ...`, which
makes it **impossible** for a client to clear a nullable field — they
can only ever set it to a non-null value.

**Authorization tip.** When the same resource is editable by both the
owner and an admin, give each a different schema (e.g. `UserSelfUpdate`
omits `is_active`/`is_superuser`/`role_ids`). That way the OpenAPI
docs honestly show which fields each endpoint accepts, and a self-edit
request that includes a privileged field is silently dropped at the
schema layer instead of executing a sensitive change.

### Adding a PUT endpoint (when you really need replace semantics)

PATCH is the right default for almost every resource. If you have a
case where the client truly *replaces* the resource (e.g. a settings
blob), define a separate schema where every field is **required**:

```python
class WidgetPut(BaseModel):
    name:        str = Field(..., max_length=100)
    description: str | None = Field(..., max_length=500)
    color:       str

@router.put("/widgets/{id}", response_model=WidgetRead)
def replace_widget(id: int, payload: WidgetPut, db: DbSession):
    widget = service.get_widget(db, id)
    for field, value in payload.model_dump().items():   # no exclude_unset!
        setattr(widget, field, value)
    return save(db, widget)
```

Don't reuse the PATCH schema for PUT — making fields Optional defeats
the whole point of PUT.

### Returning paginated results with metadata

The list endpoints in this boilerplate return a bare `list[T]` because
that's the simplest possible response shape. When a client needs to
know the total count or how many pages there are, opt into the generic
`Page[T]` envelope from `src/utils/pagination.py`:

```python
from src.utils.pagination import Page

@router.get("/widgets", response_model=Page[WidgetRead])
def list_widgets(db: DbSession, pagination: Pagination):
    items = service.list_widgets(db, offset=pagination.offset, limit=pagination.limit)
    total = service.count_widgets(db)
    return Page.build(
        items, total=total, page=pagination.page, per_page=pagination.per_page,
    )
```

The response then looks like:

```json
{
  "items": [ ... ],
  "total": 137,
  "page": 2,
  "per_page": 20,
  "pages": 7,
  "has_next": true,
  "has_prev": true
}
```

### Calling a service from a script

```python
from src.core.database import SessionLocal
from src.apps.users.service import create_user
from src.apps.users.schemas import UserCreate

with SessionLocal() as db:
    create_user(db, UserCreate(email="x@y.com", username="x", password="StrongPass1!"))
```

No HTTP round-trip required.

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

## 12. Production checklist

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

---

## What changed vs. the original boilerplate

For the curious, here's what was wrong with the previous version and
what was done about it:

| Old problem                                                                 | Fix                                                                           |
|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| Two competing `User` models (`src/models/user.py` + `src/apps/auth/models.py`) | One canonical `User` in `apps/users/models.py`; old files removed.            |
| Three competing auth routers (`routers/auth.py`, `apps/auth/routers.py`, `apps/auth/views.py`) | One router per app, mounted via `api/v1/router.py`.                           |
| `core/app.py` referenced `schemas.PermissionCreate` without importing it.   | Bootstrap moved to dedicated `apps/<x>/bootstrap.py` files.                   |
| Deprecated `@app.on_event("startup")`.                                      | Replaced with `lifespan` async context manager.                               |
| RBAC middleware accessed `request.state.current_user` which was never set, and mixed two middleware styles. | RBAC implemented as composable `Depends(require_permission(...))`. Middleware deleted. |
| `pydantic<2` and `pydantic-settings>=2` declared together — a hard conflict. | Pydantic v2 throughout, with proper `ConfigDict(from_attributes=True)`.        |
| `passlib` + `python-jose` (both unmaintained, the latter has known CVEs).   | `bcrypt` and `PyJWT` directly.                                                |
| Duplicated `[alembic]` and `[loggers]` sections in `alembic.ini`; folder named `alembic.` (with a stray period). | Clean `alembic.ini`, proper `alembic/` folder, env reads `DATABASE_URL` from settings. |
| `views.py` referenced `datetime.utcnow()` without importing `datetime`, and instantiated `AuthView()` at module level despite needing constructor args. | Plain function-based router, no fragile DI hacks.                             |
| Empty `tests/test_auth.py`.                                                 | 10 tests covering health, auth, RBAC, and pagination, all passing.            |

That's the boilerplate. Read the code top-down starting at
`src/main.py` → `src/core/app.py` → `src/api/v1/router.py` → an app of
your choice, and you'll have the whole thing in your head in 30 minutes.
