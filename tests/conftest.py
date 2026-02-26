"""
Shared pytest fixtures for all tests.

Integration tests use a real PostgreSQL test database.
Set TEST_DATABASE_URL in your environment or .env.test before running.

Each test gets its own DB transaction that is rolled back after the test,
ensuring complete isolation with no data pollution between tests.
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.session import get_db
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pms_user:pms_secret@localhost:5432/pms_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create the test database schema once per session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(test_engine):
    """
    Each test gets a connection with an open transaction.
    The transaction is rolled back at the end so tests don't pollute each other.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):
    """AsyncClient with the DB dependency overridden to use the test session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def admin_headers(client: AsyncClient, db_session: AsyncSession):
    """Create an admin user and return Authorization headers."""
    from app.auth.password import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="admin@test.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post(
        "/auth/token",
        data={"username": "admin@test.com", "password": "AdminPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
