"""Integration tests for the reservations endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import Guest
from app.models.room import RoomCategory, RoomStatus, RoomType, Room


@pytest.fixture()
async def seeded_room(db_session: AsyncSession) -> Room:
    rt = RoomType(
        name="Test Suite", category=RoomCategory.SUITE, base_rate="250.00", max_occupancy=3
    )
    db_session.add(rt)
    await db_session.flush()

    room = Room(room_number="501", floor=5, room_type_id=rt.id, status=RoomStatus.AVAILABLE)
    db_session.add(room)
    await db_session.flush()
    return room


@pytest.fixture()
async def seeded_guest(db_session: AsyncSession) -> Guest:
    guest = Guest(first_name="Jane", last_name="Doe", email="jane.doe@example.com")
    db_session.add(guest)
    await db_session.flush()
    return guest


async def test_create_reservation(
    client: AsyncClient,
    admin_headers: dict,
    seeded_room: Room,
    seeded_guest: Guest,
):
    resp = await client.post(
        "/api/v1/reservations/",
        json={
            "guest_id": str(seeded_guest.id),
            "room_id": str(seeded_room.id),
            "check_in_date": "2026-07-01",
            "check_out_date": "2026-07-05",
            "adults": 2,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["confirmation_no"].startswith("RES-")


async def test_overlapping_reservation_rejected(
    client: AsyncClient,
    admin_headers: dict,
    seeded_room: Room,
    seeded_guest: Guest,
):
    payload = {
        "guest_id": str(seeded_guest.id),
        "room_id": str(seeded_room.id),
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-05",
        "adults": 1,
    }
    r1 = await client.post("/api/v1/reservations/", json=payload, headers=admin_headers)
    assert r1.status_code == 201

    # Overlapping dates
    payload["check_in_date"] = "2026-08-03"
    payload["check_out_date"] = "2026-08-07"
    r2 = await client.post("/api/v1/reservations/", json=payload, headers=admin_headers)
    assert r2.status_code == 409


async def test_cancel_reservation(
    client: AsyncClient,
    admin_headers: dict,
    seeded_room: Room,
    seeded_guest: Guest,
):
    r = await client.post(
        "/api/v1/reservations/",
        json={
            "guest_id": str(seeded_guest.id),
            "room_id": str(seeded_room.id),
            "check_in_date": "2026-09-01",
            "check_out_date": "2026-09-03",
            "adults": 1,
        },
        headers=admin_headers,
    )
    reservation_id = r.json()["id"]
    cancel = await client.post(
        f"/api/v1/reservations/{reservation_id}/cancel", headers=admin_headers
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
