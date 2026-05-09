# Schemas & APIs

Every Pydantic schema in the project, every HTTP endpoint, the seed
data created on first boot, and the design recipes you'll reach for
most often.

> Companion docs: **[Architecture](./Architecture.md)** • **[Models](./Models.md)** • **[Boilerplate overview](./BOILERPLATE.md)**

---

## 1. Schema conventions (Pydantic v2)

Each app declares its own input/output models. Convention:

| Suffix          | Purpose                                                                                            |
|-----------------|----------------------------------------------------------------------------------------------------|
| `…Base`         | Fields shared by Create / Read / Update.                                                           |
| `…Create`       | What the client sends to create the resource. **All fields required**.                             |
| `…Update`       | What the client sends to PATCH. **All fields Optional**, applied via `model_dump(exclude_unset=True)`. |
| `…Read`         | What the API returns. `model_config = ConfigDict(from_attributes=True)` so it can serialize ORM objects directly. |
| `…SelfUpdate`   | When self-edit and admin-edit need different field sets, the smaller (self) schema is the parent.   |

Pydantic schemas are the project's DTOs. The split between
`User` (SQLAlchemy entity, owns the DB row, includes `hashed_password`)
and `UserRead` (API response, no `hashed_password` ever serialized) is
exactly the DTO pattern — secrets cannot accidentally leak to clients.

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

| Schema             | Fields                                                                                       |
|--------------------|----------------------------------------------------------------------------------------------|
| `UserBase`         | `email`, `username` (3–64, regex `^[A-Za-z0-9_.-]+$`), `full_name?`                          |
| `UserCreate`       | `UserBase` + `password` (8–128)                                                              |
| `UserSelfUpdate`   | `email?`, `full_name?`  *(what a user can change about themself)*                            |
| `UserUpdate`       | `UserSelfUpdate` + `is_active?`  *(admin can also toggle active)*                            |
| `UserAdminUpdate`  | `UserUpdate` + `is_superuser?`, `role_ids?`  *(full admin power)*                            |
| `PasswordChange`   | `current_password`, `new_password`                                                           |
| `UserRead`         | `UserBase` + `id`, `is_active`, `is_superuser`, `created_at`, `updated_at`, `roles[RoleRead]` |

The inheritance chain is the **authorization model**:
`SelfUpdate` ⊂ `Update` ⊂ `AdminUpdate`. Each route binds the
narrowest schema it needs, so `/users/me` literally cannot accept
`is_active` — it isn't a field on `UserSelfUpdate`.

### RBAC schemas — `src/apps/rbac/schemas.py`

| Schema             | Fields                                                                       |
|--------------------|------------------------------------------------------------------------------|
| `PermissionBase`   | `name` (2–100), `description?` (≤255)                                        |
| `PermissionCreate` | `PermissionBase`                                                             |
| `PermissionRead`   | `PermissionBase` + `id`, `created_at`, `updated_at`                          |
| `RoleBase`         | `name` (2–50), `description?` (≤255)                                         |
| `RoleCreate`       | `RoleBase` + `permission_ids: list[int]`                                     |
| `RoleUpdate`       | `description?`, `permission_ids?`                                            |
| `RoleRead`         | `RoleBase` + `id`, `created_at`, `updated_at`, `permissions[PermissionRead]` |

### Shared schemas — `src/utils/pagination.py`

| Schema   | Fields                                                                                |
|----------|---------------------------------------------------------------------------------------|
| `Page[T]` | `items: list[T]`, `total`, `page`, `per_page`, `pages`, `has_next`, `has_prev`       |

---

## 2. API reference

> Base URL: `/api/v1` &nbsp; (configurable via `API_V1_PREFIX`)
> All endpoints below are also browsable at `GET /docs`.

### Health (no auth)

| Method | Path        | Response                                       |
|--------|-------------|------------------------------------------------|
| GET    | `/health`   | `{"status": "ok", "environment": "..."}`       |

### Auth — `/api/v1/auth`

| Method | Path                          | Request body                                                  | Response (201/200/202/204) | Auth |
|--------|-------------------------------|---------------------------------------------------------------|----------------------------|------|
| POST   | `/auth/register`              | `UserCreate`                                                  | `UserRead` (201)           | —    |
| POST   | `/auth/login`                 | `application/x-www-form-urlencoded` (`username`, `password`)  | `TokenPair`                | —    |
| POST   | `/auth/refresh`               | `RefreshRequest`                                              | `AccessTokenOnly`          | —    |
| POST   | `/auth/password-reset/request`| `PasswordResetRequest`                                        | `{"detail": "..."}` (202)  | —    |
| POST   | `/auth/password-reset/confirm`| `PasswordResetConfirm`                                        | _(204 No Content)_         | —    |

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

### Standard query parameters

Any list endpoint accepts:

| Param      | Type | Default | Notes                      |
|------------|------|---------|----------------------------|
| `page`     | int  | `1`     | 1-indexed.                 |
| `per_page` | int  | `20`    | Min `1`, max `100`.        |

### Standard error envelope

Every error returned by the API has the same shape:

```json
{ "detail": "Human-readable explanation." }
```

For 422 validation errors, `detail` is the list of Pydantic errors:

```json
{ "detail": [{ "type": "...", "loc": ["body", "email"], "msg": "..." }] }
```

---

## 3. Default seed data

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

## 4. Design recipes

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

The list endpoints in this boilerplate return either a bare `list[T]`
(simplest possible response) or a `Page[T]` envelope (when total
count / page math matters). Use `Page[T]` whenever a UI needs to
render "page 2 of 7":

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

> The two halves of pagination live in different folders on purpose —
> the request-side `Pagination` dependency uses `fastapi.Query()` and
> belongs in `core/dependencies.py`; the response-side `Page[T]` is a
> pure Pydantic model and belongs in `utils/pagination.py`. See
> [Architecture → Pagination is split in two — on purpose](./Architecture.md#pagination-is-split-in-two--on-purpose).
