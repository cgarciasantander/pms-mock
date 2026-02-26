import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus, RoomType
from app.schemas.room import RoomCreate, RoomTypeCreate, RoomTypeUpdate, RoomUpdate

# Status transitions that staff can set manually (front-desk / maintenance)
_ALLOWED_MANUAL_TRANSITIONS: dict[RoomStatus, set[RoomStatus]] = {
    RoomStatus.AVAILABLE: {RoomStatus.HOUSEKEEPING, RoomStatus.MAINTENANCE},
    RoomStatus.HOUSEKEEPING: {RoomStatus.AVAILABLE, RoomStatus.MAINTENANCE},
    RoomStatus.MAINTENANCE: {RoomStatus.AVAILABLE, RoomStatus.HOUSEKEEPING},
    RoomStatus.OUT_OF_ORDER: {RoomStatus.MAINTENANCE, RoomStatus.AVAILABLE},
    # OCCUPIED transitions are managed by reservation_controller (check-in/check-out)
    RoomStatus.OCCUPIED: set(),
}


# ── Room Types ─────────────────────────────────────────────────────────────────


async def create_room_type(db: AsyncSession, data: RoomTypeCreate) -> RoomType:
    existing = await db.execute(select(RoomType).where(RoomType.name == data.name))
    if existing.scalar_one_or_none():
        raise ConflictError(detail="A room type with this name already exists")

    room_type = RoomType(**data.model_dump())
    db.add(room_type)
    await db.flush()
    await db.refresh(room_type)
    return room_type


async def get_room_type(db: AsyncSession, room_type_id: uuid.UUID) -> RoomType:
    rt = await db.get(RoomType, room_type_id)
    if rt is None:
        raise NotFoundError(detail="Room type not found")
    return rt


async def get_room_types(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> tuple[list[RoomType], int]:
    result = await db.execute(select(RoomType).offset(skip).limit(limit))
    room_types = list(result.scalars())
    total = (await db.execute(select(func.count()).select_from(RoomType))).scalar_one()
    return room_types, total


async def update_room_type(
    db: AsyncSession, room_type_id: uuid.UUID, data: RoomTypeUpdate
) -> RoomType:
    rt = await get_room_type(db, room_type_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rt, field, value)
    await db.flush()
    await db.refresh(rt)
    return rt


# ── Rooms ──────────────────────────────────────────────────────────────────────


async def create_room(db: AsyncSession, data: RoomCreate) -> Room:
    await get_room_type(db, data.room_type_id)  # validates FK exists

    existing = await db.execute(select(Room).where(Room.room_number == data.room_number))
    if existing.scalar_one_or_none():
        raise ConflictError(detail="Room number already exists")

    room = Room(**data.model_dump())
    db.add(room)
    await db.flush()
    await db.refresh(room)
    return room


async def get_room(db: AsyncSession, room_id: uuid.UUID) -> Room:
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.room_type))
    )
    room = result.scalar_one_or_none()
    if room is None:
        raise NotFoundError(detail="Room not found")
    return room


async def get_rooms(
    db: AsyncSession,
    status_filter: RoomStatus | None = None,
    floor_filter: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Room], int]:
    q = select(Room).options(selectinload(Room.room_type))
    if status_filter:
        q = q.where(Room.status == status_filter)
    if floor_filter is not None:
        q = q.where(Room.floor == floor_filter)

    result = await db.execute(q.offset(skip).limit(limit))
    rooms = list(result.scalars())

    count_q = select(func.count()).select_from(Room)
    if status_filter:
        count_q = count_q.where(Room.status == status_filter)
    if floor_filter is not None:
        count_q = count_q.where(Room.floor == floor_filter)
    total = (await db.execute(count_q)).scalar_one()
    return rooms, total


async def update_room(db: AsyncSession, room_id: uuid.UUID, data: RoomUpdate) -> Room:
    room = await get_room(db, room_id)
    if data.room_type_id:
        await get_room_type(db, data.room_type_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(room, field, value)
    await db.flush()
    await db.refresh(room)
    return room


async def update_room_status(
    db: AsyncSession, room_id: uuid.UUID, new_status: RoomStatus
) -> Room:
    room = await get_room(db, room_id)
    allowed = _ALLOWED_MANUAL_TRANSITIONS.get(room.status, set())
    if new_status not in allowed:
        raise UnprocessableError(
            detail=f"Cannot transition room from {room.status.value} to {new_status.value} manually"
        )
    room.status = new_status
    await db.flush()
    await db.refresh(room)
    return room


async def get_available_rooms(
    db: AsyncSession,
    check_in: date,
    check_out: date,
    room_type_id: uuid.UUID | None = None,
) -> list[Room]:
    """Return rooms that have no overlapping confirmed/checked-in reservation."""
    # Subquery: rooms with overlapping reservations
    overlapping = (
        select(Reservation.room_id)
        .where(
            Reservation.status.in_(
                [ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN]
            ),
            Reservation.check_in_date < check_out,
            Reservation.check_out_date > check_in,
        )
    ).scalar_subquery()

    q = (
        select(Room)
        .options(selectinload(Room.room_type))
        .where(
            Room.status == RoomStatus.AVAILABLE,
            Room.id.not_in(overlapping),
        )
    )
    if room_type_id:
        q = q.where(Room.room_type_id == room_type_id)

    result = await db.execute(q)
    return list(result.scalars())
