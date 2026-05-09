# Models

The database tier: engine setup, the shared declarative `Base`, and
every ORM model in the project.

> Companion docs: **[Architecture](./Architecture.md)** • **[Schemas & APIs](./Schemas-and-APIs.md)** • **[Boilerplate overview](./BOILERPLATE.md)**

---

## 1. Engine + session

```22:24:src/core/database.py
engine = create_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
```

`get_db` is a generator-style FastAPI dependency that opens a session,
yields it, and closes it after the response is sent.

## 2. The shared `Base`

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

## 3. Persistence helpers

`core/database.py` also exports two tiny helpers so service code
doesn't repeat the `add → commit → refresh` boilerplate everywhere:

```python
def save(db: Session, obj: ModelT) -> ModelT:
    """Persist obj (insert OR update) and return the refreshed instance."""
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def remove(db: Session, obj: ModelT) -> None:
    """Delete obj and commit."""
    db.delete(obj)
    db.commit()
```

`db.add()` is a no-op for objects already attached to the session, so
`save()` works for both inserts and updates. There is also a
`save_all(db, objs)` for bulk inserts that commits once for the whole
batch.

## 4. Models

### `User` — `src/apps/users/models.py`

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

### `Role` — `src/apps/rbac/models.py`

| Column          | Type             | Constraints                 |
|-----------------|------------------|-----------------------------|
| `id`            | `int`            | PK, indexed                 |
| `name`          | `str(50)`        | unique, indexed             |
| `description`   | `str(255)?`      | nullable                    |
| `permissions`   | `list[Permission]` | many-to-many via `role_permissions` |
| `users`         | `list[User]`     | many-to-many via `user_roles` |

### `Permission` — `src/apps/rbac/models.py`

| Column          | Type        | Constraints     |
|-----------------|-------------|-----------------|
| `id`            | `int`       | PK, indexed     |
| `name`          | `str(100)`  | unique, indexed |
| `description`   | `str(255)?` | nullable        |
| `roles`         | `list[Role]`| many-to-many    |

### Association tables

| Table              | Columns                            |
|--------------------|------------------------------------|
| `user_roles`       | `user_id` ↔ `role_id`              |
| `role_permissions` | `role_id` ↔ `permission_id`        |

Both use `ondelete=CASCADE` so deleting a user/role/permission cleanly
removes its associations.

## 5. Entity-relationship diagram

```
┌─────────────────────┐        ┌────────────────┐       ┌────────────────────┐
│        User         │        │      Role      │       │    Permission      │
├─────────────────────┤        ├────────────────┤       ├────────────────────┤
│ id           PK     │        │ id        PK   │       │ id           PK    │
│ email        UNIQ   │  N:M   │ name      UNIQ │  N:M  │ name         UNIQ  │
│ username     UNIQ   │◀──────▶│ description    │◀─────▶│ description        │
│ full_name?          │        │ created_at     │       │ created_at         │
│ hashed_password     │        │ updated_at     │       │ updated_at         │
│ is_active           │        └────────────────┘       └────────────────────┘
│ is_superuser        │                ▲                          ▲
│ created_at          │                │                          │
│ updated_at          │                │                          │
└─────────────────────┘                │                          │
          ▲                            │                          │
          │                            │                          │
          │                            │                          │
   ┌──────┴──────────┐         ┌───────┴──────────────┐
   │   user_roles    │         │   role_permissions   │
   ├─────────────────┤         ├──────────────────────┤
   │ user_id  FK     │         │ role_id        FK    │
   │ role_id  FK     │         │ permission_id  FK    │
   └─────────────────┘         └──────────────────────┘
```

## 6. Why sync, not async?

Because async SQLAlchemy adds real cognitive overhead (greenlets,
async sessions, async relationships) and gives **no measurable
benefit** for IO-bound workloads up to a few hundred RPS. FastAPI runs
sync DB calls in a threadpool transparently. When you outgrow that,
swap `create_engine` / `Session` for `create_async_engine` /
`AsyncSession` and add `await` everywhere — the rest of the
architecture is unchanged.

## 7. Migrations workflow

```bash
# Create a new migration after editing any models.py
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

`alembic/env.py` imports every `models.py` so autogenerate sees all
tables. **When you add a new app with its own model, add the import
there too**:

```python
# alembic/env.py
from src.apps.posts import models as _post_models  # noqa: F401
```

> In `DEBUG=true` mode the lifespan auto-creates tables on startup so
> beginners can skip Alembic on day one. In production, always rely on
> migrations.
