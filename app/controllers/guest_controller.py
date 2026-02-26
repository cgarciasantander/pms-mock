import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.guest import Guest
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.guest import GuestCreate, GuestUpdate


async def create_guest(db: AsyncSession, data: GuestCreate) -> Guest:
    if data.email:
        existing = await db.execute(select(Guest).where(Guest.email == data.email))
        if existing.scalar_one_or_none():
            raise ConflictError(detail="A guest with this email already exists")

    guest = Guest(**data.model_dump())
    db.add(guest)
    await db.flush()
    await db.refresh(guest)
    return guest


async def get_guest(db: AsyncSession, guest_id: uuid.UUID) -> Guest:
    guest = await db.get(Guest, guest_id)
    if guest is None:
        raise NotFoundError(detail="Guest not found")
    return guest


async def search_guests(
    db: AsyncSession, query: str = "", skip: int = 0, limit: int = 20
) -> tuple[list[Guest], int]:
    q = select(Guest)
    if query:
        pattern = f"%{query}%"
        q = q.where(
            or_(
                Guest.first_name.ilike(pattern),
                Guest.last_name.ilike(pattern),
                Guest.email.ilike(pattern),
            )
        )
    result = await db.execute(q.offset(skip).limit(limit))
    guests = list(result.scalars())

    count_q = select(func.count()).select_from(Guest)
    if query:
        pattern = f"%{query}%"
        count_q = count_q.where(
            or_(
                Guest.first_name.ilike(pattern),
                Guest.last_name.ilike(pattern),
                Guest.email.ilike(pattern),
            )
        )
    total = (await db.execute(count_q)).scalar_one()
    return guests, total


async def update_guest(db: AsyncSession, guest_id: uuid.UUID, data: GuestUpdate) -> Guest:
    guest = await get_guest(db, guest_id)

    if data.email and data.email != guest.email:
        existing = await db.execute(select(Guest).where(Guest.email == data.email))
        if existing.scalar_one_or_none():
            raise ConflictError(detail="Email already in use")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(guest, field, value)

    await db.flush()
    await db.refresh(guest)
    return guest


async def delete_guest(db: AsyncSession, guest_id: uuid.UUID) -> None:
    guest = await get_guest(db, guest_id)

    active = await db.execute(
        select(Reservation).where(
            Reservation.guest_id == guest_id,
            Reservation.status.in_(
                [ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN]
            ),
        )
    )
    if active.scalar_one_or_none():
        raise UnprocessableError(
            detail="Cannot delete guest with active or upcoming reservations"
        )

    await db.delete(guest)
    await db.flush()


async def get_guest_stay_history(
    db: AsyncSession, guest_id: uuid.UUID
) -> list[Reservation]:
    await get_guest(db, guest_id)
    result = await db.execute(
        select(Reservation)
        .where(Reservation.guest_id == guest_id)
        .order_by(Reservation.check_in_date.desc())
    )
    return list(result.scalars())
