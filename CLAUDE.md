# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install          # install all deps (pip install -e ".[dev]")
make up               # start PostgreSQL + pgAdmin via Docker
make migrate          # alembic upgrade head
make dev              # uvicorn with --reload on :8000
make seed             # python -m scripts.seed
make test             # pytest with coverage (requires pms_test DB)
make lint             # ruff check app tests
make format           # ruff format app tests

# Migrations
make revision MSG="describe your change"   # autogenerate migration
make downgrade                             # roll back one step

# Run a single test file or test
pytest tests/unit/test_jwt.py
pytest -k test_create_reservation
```

Integration tests require a running PostgreSQL instance. Set `TEST_DATABASE_URL` or use the default:
`postgresql+asyncpg://pms_user:pms_secret@localhost:5432/pms_test`

Each integration test runs inside a transaction that is rolled back automatically — no cleanup needed.

## Architecture

**MVC pattern** — strict separation:

| Layer | Path | Responsibility |
|---|---|---|
| Models | `app/models/` | SQLAlchemy ORM only — no logic |
| Schemas | `app/schemas/` | Pydantic v2 request/response shapes |
| Controllers | `app/controllers/` | All business logic (plain async functions) |
| Routers | `app/routers/` | HTTP layer — calls controllers, returns responses |
| Auth | `app/auth/` | `jwt.py`, `password.py`, `oauth2_scheme.py` |

**Entry point**: `app/main.py` — registers routers under `/auth` and `/api/v1/{resource}`.

**Shared infrastructure**:
- `app/database/base.py` — `Base` (DeclarativeBase) + `TimestampMixin` (`created_at`/`updated_at`)
- `app/database/session.py` — async engine and `get_db` session dependency
- `app/dependencies.py` — `get_current_user`, `require_role(*roles)` (dependency factory for RBAC)
- `app/exceptions.py` — `NotFoundError`, `ConflictError`, `ForbiddenError`, `UnauthorizedError`, `UnprocessableError`
- `app/schemas/common.py` — `PaginatedResponse[T]`, `MessageResponse`

## Key Patterns

**Models**: All PKs are `UUID` (default=`uuid.uuid4`). Every model inherits `Base` and `TimestampMixin`. SQLAlchemy `Mapped`/`mapped_column` style throughout.

**Controllers**: Plain async functions (not classes). They accept `db: AsyncSession` plus data arguments, call `db.flush()` (never `db.commit()` — commits are managed by the session dependency), and raise exceptions from `app/exceptions.py`.

**Routers**: Declare FastAPI path operations, inject `db` and `current_user` via `Depends`, and delegate all logic to controllers.

**RBAC**: `require_role(UserRole.ADMIN, UserRole.MANAGER)` as a path-operation dependency. Roles: `admin`, `manager`, `front_desk`, `housekeeping`.

**Pagination**: Controllers return `tuple[list[Model], int]`. Routers wrap in `PaginatedResponse[Schema]` with `skip`/`limit` query params.

**Auth**: OAuth2 password flow. Access tokens include `sub` (user_id), `role`, and `type: "access"`. Refresh tokens are stored in the DB as SHA-256 hashes only (raw token never persisted). `/auth/refresh` rotates the token (old one is revoked).

**Billing**: Folio balance is denormalized on the `Folio` row (`balance = total_charges - total_payments`). Always update via `billing_controller` functions which keep these fields in sync. Voiding a line item adds a negative credit line item (preserves audit trail).

**Reservation lifecycle**: `CONFIRMED → CHECKED_IN → CHECKED_OUT` (or `CANCELLED` / `NO_SHOW`). Check-in sets room status to `OCCUPIED` and posts first-night room charge. Check-out sets room status to `HOUSEKEEPING` and posts remaining charges.

**Room status machine**: Manual transitions are limited (`OCCUPIED` can only change via reservation check-in/check-out). See `_ALLOWED_MANUAL_TRANSITIONS` in `room_controller.py`.

**Availability query**: Uses a `NOT IN` subquery on `Reservation.room_id` for overlapping date ranges with `CONFIRMED` or `CHECKED_IN` status.

**Adding a new domain module**: create `app/models/x.py`, `app/schemas/x.py`, `app/controllers/x_controller.py`, `app/routers/x.py`, register the router in `app/main.py`, then generate a migration.
