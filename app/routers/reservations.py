import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers import reservation_controller
from app.database.session import get_db
from app.dependencies import get_current_principal, require_role
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.reservation import (
    CheckInRequest,
    CheckOutResponse,
    ReservationCreate,
    ReservationRead,
    ReservationUpdate,
)

router = APIRouter()

_auth = Depends(get_current_principal)
_front_desk = Depends(
    require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.FRONT_DESK)
)


@router.post("/", response_model=ReservationRead, status_code=201, dependencies=[_front_desk])
async def create_reservation(
    data: ReservationCreate,
    db: AsyncSession = Depends(get_db),
) -> Reservation:
    return await reservation_controller.create_reservation(db, data)


@router.get("/", response_model=PaginatedResponse[ReservationRead], dependencies=[_auth])
async def list_reservations(
    guest_id: uuid.UUID | None = Query(None),
    room_id: uuid.UUID | None = Query(None),
    status: ReservationStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReservationRead]:
    reservations, total = await reservation_controller.get_reservations(
        db, guest_id=guest_id, room_id=room_id, status=status, skip=skip, limit=limit
    )
    return PaginatedResponse(items=reservations, total=total, skip=skip, limit=limit)  # type: ignore[arg-type]


@router.get("/{reservation_id}", response_model=ReservationRead, dependencies=[_auth])
async def get_reservation(
    reservation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Reservation:
    return await reservation_controller.get_reservation(db, reservation_id)


@router.patch(
    "/{reservation_id}", response_model=ReservationRead, dependencies=[_front_desk]
)
async def update_reservation(
    reservation_id: uuid.UUID,
    data: ReservationUpdate,
    db: AsyncSession = Depends(get_db),
) -> Reservation:
    return await reservation_controller.update_reservation(db, reservation_id, data)


@router.post(
    "/{reservation_id}/cancel",
    response_model=ReservationRead,
    dependencies=[_front_desk],
)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    reason: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Reservation:
    return await reservation_controller.cancel_reservation(db, reservation_id, reason)


@router.post(
    "/{reservation_id}/check-in",
    response_model=ReservationRead,
    dependencies=[_front_desk],
)
async def check_in(
    reservation_id: uuid.UUID,
    body: CheckInRequest,
    db: AsyncSession = Depends(get_db),
) -> Reservation:
    return await reservation_controller.check_in(db, reservation_id)


@router.post(
    "/{reservation_id}/check-out",
    response_model=CheckOutResponse,
    dependencies=[_front_desk],
)
async def check_out(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CheckOutResponse:
    return await reservation_controller.check_out(db, reservation_id)


@router.post(
    "/{reservation_id}/no-show",
    response_model=ReservationRead,
    dependencies=[_front_desk],
)
async def mark_no_show(
    reservation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Reservation:
    return await reservation_controller.mark_no_show(db, reservation_id)
