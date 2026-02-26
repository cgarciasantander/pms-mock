import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers import room_controller
from app.database.session import get_db
from app.dependencies import get_current_principal, require_role
from app.models.room import Room, RoomStatus, RoomType
from app.models.user import UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.room import (
    RoomCreate,
    RoomRead,
    RoomStatusUpdate,
    RoomTypeCreate,
    RoomTypeRead,
    RoomTypeUpdate,
    RoomUpdate,
)

router = APIRouter()

_auth = Depends(get_current_principal)
_managers = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))


# ── Room Types ─────────────────────────────────────────────────────────────────


@router.post("/types", response_model=RoomTypeRead, status_code=201, dependencies=[_managers])
async def create_room_type(
    data: RoomTypeCreate, db: AsyncSession = Depends(get_db)
) -> RoomType:
    return await room_controller.create_room_type(db, data)


@router.get("/types", response_model=PaginatedResponse[RoomTypeRead], dependencies=[_auth])
async def list_room_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RoomTypeRead]:
    room_types, total = await room_controller.get_room_types(db, skip=skip, limit=limit)
    return PaginatedResponse(items=room_types, total=total, skip=skip, limit=limit)  # type: ignore[arg-type]


@router.get("/types/{room_type_id}", response_model=RoomTypeRead, dependencies=[_auth])
async def get_room_type(
    room_type_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> RoomType:
    return await room_controller.get_room_type(db, room_type_id)


@router.patch(
    "/types/{room_type_id}", response_model=RoomTypeRead, dependencies=[_managers]
)
async def update_room_type(
    room_type_id: uuid.UUID,
    data: RoomTypeUpdate,
    db: AsyncSession = Depends(get_db),
) -> RoomType:
    return await room_controller.update_room_type(db, room_type_id, data)


# ── Rooms ──────────────────────────────────────────────────────────────────────


@router.post("/", response_model=RoomRead, status_code=201, dependencies=[_managers])
async def create_room(data: RoomCreate, db: AsyncSession = Depends(get_db)) -> Room:
    return await room_controller.create_room(db, data)


@router.get("/", response_model=PaginatedResponse[RoomRead], dependencies=[_auth])
async def list_rooms(
    status: RoomStatus | None = Query(None),
    floor: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RoomRead]:
    rooms, total = await room_controller.get_rooms(
        db, status_filter=status, floor_filter=floor, skip=skip, limit=limit
    )
    return PaginatedResponse(items=rooms, total=total, skip=skip, limit=limit)  # type: ignore[arg-type]


@router.get("/available", response_model=list[RoomRead], dependencies=[_auth])
async def available_rooms(
    check_in_date: date = Query(...),
    check_out_date: date = Query(...),
    room_type_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[Room]:
    return await room_controller.get_available_rooms(
        db, check_in_date, check_out_date, room_type_id
    )


@router.get("/{room_id}", response_model=RoomRead, dependencies=[_auth])
async def get_room(room_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Room:
    return await room_controller.get_room(db, room_id)


@router.patch("/{room_id}", response_model=RoomRead, dependencies=[_managers])
async def update_room(
    room_id: uuid.UUID, data: RoomUpdate, db: AsyncSession = Depends(get_db)
) -> Room:
    return await room_controller.update_room(db, room_id, data)


@router.patch("/{room_id}/status", response_model=RoomRead, dependencies=[_auth])
async def update_room_status(
    room_id: uuid.UUID, data: RoomStatusUpdate, db: AsyncSession = Depends(get_db)
) -> Room:
    return await room_controller.update_room_status(db, room_id, data.status)
