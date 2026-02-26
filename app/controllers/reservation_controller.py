import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.controllers.billing_controller import (
    apply_room_charges_for_night,
    create_folio,
)
from app.controllers.room_controller import get_available_rooms, get_room
from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.billing import Folio
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomStatus
from app.schemas.reservation import CheckOutResponse, ReservationCreate, ReservationUpdate
from app.utils.date_helpers import night_count


def _generate_confirmation_no(seq: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"RES-{today}-{seq:04d}"


async def _next_confirmation_no(db: AsyncSession) -> str:
    result = await db.execute(select(func.count()).select_from(Reservation))
    count = result.scalar_one()
    return _generate_confirmation_no(count + 1)


async def create_reservation(
    db: AsyncSession, data: ReservationCreate
) -> Reservation:
    available = await get_available_rooms(db, data.check_in_date, data.check_out_date)
    available_ids = {r.id for r in available}

    if data.room_id not in available_ids:
        raise ConflictError(
            detail="Room is not available for the requested dates"
        )

    room = await get_room(db, data.room_id)
    capacity = room.room_type.max_occupancy
    if (data.adults + data.children) > capacity:
        raise UnprocessableError(
            detail=f"Room max occupancy is {capacity} guests"
        )

    confirmation_no = await _next_confirmation_no(db)
    reservation = Reservation(
        confirmation_no=confirmation_no,
        guest_id=data.guest_id,
        room_id=data.room_id,
        check_in_date=data.check_in_date,
        check_out_date=data.check_out_date,
        adults=data.adults,
        children=data.children,
        rate_per_night=room.room_type.base_rate,
        special_requests=data.special_requests,
    )
    db.add(reservation)
    await db.flush()

    # Create the folio immediately upon reservation
    await create_folio(db, reservation.id)

    await db.refresh(reservation)
    return reservation


async def get_reservation(db: AsyncSession, reservation_id: uuid.UUID) -> Reservation:
    result = await db.execute(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(
            selectinload(Reservation.guest),
            selectinload(Reservation.room).selectinload(Room.room_type),
        )
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise NotFoundError(detail="Reservation not found")
    return reservation


async def get_reservations(
    db: AsyncSession,
    guest_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
    status: ReservationStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Reservation], int]:
    q = select(Reservation)
    if guest_id:
        q = q.where(Reservation.guest_id == guest_id)
    if room_id:
        q = q.where(Reservation.room_id == room_id)
    if status:
        q = q.where(Reservation.status == status)

    result = await db.execute(q.offset(skip).limit(limit))
    reservations = list(result.scalars())

    count_q = select(func.count()).select_from(Reservation)
    if guest_id:
        count_q = count_q.where(Reservation.guest_id == guest_id)
    if room_id:
        count_q = count_q.where(Reservation.room_id == room_id)
    if status:
        count_q = count_q.where(Reservation.status == status)
    total = (await db.execute(count_q)).scalar_one()
    return reservations, total


async def update_reservation(
    db: AsyncSession, reservation_id: uuid.UUID, data: ReservationUpdate
) -> Reservation:
    reservation = await get_reservation(db, reservation_id)

    if reservation.status != ReservationStatus.CONFIRMED:
        raise UnprocessableError(detail="Only confirmed reservations can be updated")

    new_check_in = data.check_in_date or reservation.check_in_date
    new_check_out = data.check_out_date or reservation.check_out_date
    new_room_id = data.room_id or reservation.room_id

    if new_room_id != reservation.room_id or new_check_in != reservation.check_in_date or new_check_out != reservation.check_out_date:
        available = await get_available_rooms(db, new_check_in, new_check_out)
        available_ids = {r.id for r in available}
        # Allow the current reservation's room (it's not conflicting with itself)
        existing_room_available = new_room_id == reservation.room_id or new_room_id in available_ids
        if not existing_room_available:
            raise ConflictError(detail="Room is not available for the updated dates")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reservation, field, value)

    await db.flush()
    await db.refresh(reservation)
    return reservation


async def cancel_reservation(
    db: AsyncSession, reservation_id: uuid.UUID, reason: str | None = None
) -> Reservation:
    reservation = await get_reservation(db, reservation_id)

    if reservation.status not in (ReservationStatus.CONFIRMED,):
        raise UnprocessableError(detail="Only confirmed reservations can be cancelled")

    reservation.status = ReservationStatus.CANCELLED
    if reason:
        reservation.special_requests = (
            (reservation.special_requests or "") + f"\n[CANCEL REASON]: {reason}"
        ).strip()

    await db.flush()
    await db.refresh(reservation)
    return reservation


async def check_in(
    db: AsyncSession,
    reservation_id: uuid.UUID,
) -> Reservation:
    reservation = await get_reservation(db, reservation_id)

    if reservation.status != ReservationStatus.CONFIRMED:
        raise UnprocessableError(detail="Reservation is not in confirmed status")

    reservation.status = ReservationStatus.CHECKED_IN

    room = await db.get(Room, reservation.room_id)
    if room:
        room.status = RoomStatus.OCCUPIED

    # Post first night room charge
    today = datetime.now(timezone.utc).date()
    await apply_room_charges_for_night(db, reservation, today)

    await db.flush()
    await db.refresh(reservation)
    return reservation


async def check_out(
    db: AsyncSession,
    reservation_id: uuid.UUID,
) -> CheckOutResponse:
    reservation = await get_reservation(db, reservation_id)

    if reservation.status != ReservationStatus.CHECKED_IN:
        raise UnprocessableError(detail="Reservation is not in checked-in status")

    reservation.status = ReservationStatus.CHECKED_OUT

    room = await db.get(Room, reservation.room_id)
    if room:
        room.status = RoomStatus.HOUSEKEEPING

    # Post any remaining room charges
    today = datetime.now(timezone.utc).date()
    nights = night_count(reservation.check_in_date, today)
    # Post one charge for each remaining night (if not already posted)
    # Simplified: post remaining nights as a batch line item
    remaining = night_count(
        max(reservation.check_in_date, today - timedelta(days=1)),
        reservation.check_out_date,
    )
    if remaining > 0:
        await apply_room_charges_for_night(db, reservation, today, nights_override=remaining)

    folio_result = await db.execute(
        select(Folio).where(Folio.reservation_id == reservation_id)
    )
    folio = folio_result.scalar_one_or_none()

    await db.flush()
    await db.refresh(reservation)

    return CheckOutResponse(
        reservation_id=reservation.id,
        confirmation_no=reservation.confirmation_no,
        folio_id=folio.id if folio else uuid.UUID(int=0),
        balance=folio.balance if folio else reservation.rate_per_night,
        message="Check-out complete. Please settle the folio balance.",
    )


async def mark_no_show(db: AsyncSession, reservation_id: uuid.UUID) -> Reservation:
    reservation = await get_reservation(db, reservation_id)

    if reservation.status != ReservationStatus.CONFIRMED:
        raise UnprocessableError(detail="Only confirmed reservations can be marked as no-show")

    reservation.status = ReservationStatus.NO_SHOW
    await db.flush()
    await db.refresh(reservation)
    return reservation
