from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database.session import engine
from app.exceptions import register_exception_handlers
from app.routers import auth, billing, guests, reservations, rooms, users

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: nothing needed here — Alembic manages the schema, not create_all
    yield
    # Shutdown: dispose the async engine connection pool
    await engine.dispose()


app = FastAPI(
    title="Hotel PMS API",
    description="Property Management System for hotels — FastAPI boilerplate",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

register_exception_handlers(app)


@app.get("/health", tags=["Health"], include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


# Auth endpoints have no API prefix so the OAuth2PasswordBearer tokenUrl matches
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["Users"])
app.include_router(guests.router, prefix=f"{API_PREFIX}/guests", tags=["Guests"])
app.include_router(rooms.router, prefix=f"{API_PREFIX}/rooms", tags=["Rooms"])
app.include_router(
    reservations.router, prefix=f"{API_PREFIX}/reservations", tags=["Reservations"]
)
app.include_router(billing.router, prefix=f"{API_PREFIX}/billing", tags=["Billing"])
