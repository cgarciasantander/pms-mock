"""Integration tests for room and room-type endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import RoomCategory, RoomType


@pytest.fixture()
async def room_type(db_session: AsyncSession) -> RoomType:
    rt = RoomType(
        name="Deluxe Double",
        category=RoomCategory.DOUBLE,
        base_rate="180.00",
        max_occupancy=2,
    )
    db_session.add(rt)
    await db_session.flush()
    return rt


async def test_create_room_type(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/v1/rooms/types",
        json={"name": "Standard Single", "category": "single", "base_rate": "99.00"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Standard Single"


async def test_create_room_type_duplicate_name(
    client: AsyncClient, admin_headers: dict, room_type: RoomType
):
    resp = await client.post(
        "/api/v1/rooms/types",
        json={"name": room_type.name, "category": "double", "base_rate": "100.00"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


async def test_create_room(client: AsyncClient, admin_headers: dict, room_type: RoomType):
    resp = await client.post(
        "/api/v1/rooms/",
        json={
            "room_number": "201",
            "floor": 2,
            "room_type_id": str(room_type.id),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["room_number"] == "201"
    assert resp.json()["status"] == "available"


async def test_list_rooms(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/rooms/", headers=admin_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_check_available_rooms(
    client: AsyncClient, admin_headers: dict, room_type: RoomType
):
    # Create a room
    await client.post(
        "/api/v1/rooms/",
        json={"room_number": "301", "floor": 3, "room_type_id": str(room_type.id)},
        headers=admin_headers,
    )
    resp = await client.get(
        "/api/v1/rooms/available",
        params={"check_in_date": "2026-06-01", "check_out_date": "2026-06-05"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
