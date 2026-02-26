"""Integration tests for the auth endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.models.user import User, UserRole


@pytest.fixture()
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@hotel.com",
        hashed_password=hash_password("Passw0rd!"),
        full_name="Test User",
        role=UserRole.FRONT_DESK,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_login_success(client: AsyncClient, test_user: User):
    resp = await client.post(
        "/auth/token",
        data={"username": "test@hotel.com", "password": "Passw0rd!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, test_user: User):
    resp = await client.post(
        "/auth/token",
        data={"username": "test@hotel.com", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401


async def test_refresh_token(client: AsyncClient, test_user: User):
    login = await client.post(
        "/auth/token",
        data={"username": "test@hotel.com", "password": "Passw0rd!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_logout(client: AsyncClient, test_user: User):
    login = await client.post(
        "/auth/token",
        data={"username": "test@hotel.com", "password": "Passw0rd!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 200

    # Token should now be revoked
    resp2 = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp2.status_code == 401


async def test_me_endpoint(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"
