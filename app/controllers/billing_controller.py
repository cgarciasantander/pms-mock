import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, UnprocessableError
from app.models.billing import Folio, FolioStatus, LineItem, LineItemType, Payment
from app.models.reservation import Reservation
from app.schemas.billing import FolioStatement, LineItemCreate, PaymentCreate
from app.utils.date_helpers import night_count

_BALANCE_TOLERANCE = Decimal("0.01")


async def create_folio(db: AsyncSession, reservation_id: uuid.UUID) -> Folio:
    folio = Folio(reservation_id=reservation_id)
    db.add(folio)
    await db.flush()
    return folio


async def get_folio(db: AsyncSession, folio_id: uuid.UUID) -> Folio:
    result = await db.execute(
        select(Folio)
        .where(Folio.id == folio_id)
        .options(
            selectinload(Folio.line_items),
            selectinload(Folio.payments),
        )
    )
    folio = result.scalar_one_or_none()
    if folio is None:
        raise NotFoundError(detail="Folio not found")
    return folio


async def get_folio_by_reservation(
    db: AsyncSession, reservation_id: uuid.UUID
) -> Folio:
    result = await db.execute(
        select(Folio)
        .where(Folio.reservation_id == reservation_id)
        .options(
            selectinload(Folio.line_items),
            selectinload(Folio.payments),
        )
    )
    folio = result.scalar_one_or_none()
    if folio is None:
        raise NotFoundError(detail="Folio not found for this reservation")
    return folio


async def add_line_item(
    db: AsyncSession, folio_id: uuid.UUID, data: LineItemCreate
) -> LineItem:
    folio = await db.get(Folio, folio_id)
    if folio is None:
        raise NotFoundError(detail="Folio not found")
    if folio.status != FolioStatus.OPEN:
        raise UnprocessableError(detail="Cannot add charges to a closed folio")

    total = data.quantity * data.unit_price

    item = LineItem(
        folio_id=folio_id,
        item_type=data.item_type,
        description=data.description,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total=total,
    )
    db.add(item)

    folio.total_charges += total
    folio.balance = folio.total_charges - folio.total_payments

    await db.flush()
    await db.refresh(item)
    return item


async def void_line_item(
    db: AsyncSession, line_item_id: uuid.UUID
) -> LineItem:
    item = await db.get(LineItem, line_item_id)
    if item is None:
        raise NotFoundError(detail="Line item not found")

    folio = await db.get(Folio, item.folio_id)
    if folio is None or folio.status != FolioStatus.OPEN:
        raise UnprocessableError(detail="Cannot void items on a closed folio")

    # Add a negative credit line to preserve audit trail
    void_item = LineItem(
        folio_id=item.folio_id,
        item_type=item.item_type,
        description=f"VOID: {item.description}",
        quantity=item.quantity,
        unit_price=-item.unit_price,
        total=-item.total,
    )
    db.add(void_item)

    folio.total_charges += void_item.total
    folio.balance = folio.total_charges - folio.total_payments

    await db.flush()
    await db.refresh(void_item)
    return void_item


async def post_payment(
    db: AsyncSession,
    folio_id: uuid.UUID,
    data: PaymentCreate,
) -> Payment:
    folio = await db.get(Folio, folio_id)
    if folio is None:
        raise NotFoundError(detail="Folio not found")
    if folio.status != FolioStatus.OPEN:
        raise UnprocessableError(detail="Cannot post payments to a closed folio")

    payment = Payment(
        folio_id=folio_id,
        method=data.method,
        amount=data.amount,
        reference_no=data.reference_no,
        notes=data.notes,
    )
    db.add(payment)

    folio.total_payments += data.amount
    folio.balance = folio.total_charges - folio.total_payments

    await db.flush()
    await db.refresh(payment)
    return payment


async def close_folio(db: AsyncSession, folio_id: uuid.UUID) -> Folio:
    folio = await db.get(Folio, folio_id)
    if folio is None:
        raise NotFoundError(detail="Folio not found")
    if folio.status == FolioStatus.CLOSED:
        raise UnprocessableError(detail="Folio is already closed")
    if abs(folio.balance) > _BALANCE_TOLERANCE:
        raise UnprocessableError(
            detail=f"Folio balance must be zero before closing (current: {folio.balance})"
        )

    folio.status = FolioStatus.CLOSED
    await db.flush()
    await db.refresh(folio)
    return folio


async def get_folio_statement(db: AsyncSession, folio_id: uuid.UUID) -> FolioStatement:
    folio = await get_folio(db, folio_id)
    return FolioStatement(
        folio=folio,  # type: ignore[arg-type]
        line_items=folio.line_items,  # type: ignore[arg-type]
        payments=folio.payments,  # type: ignore[arg-type]
    )


async def apply_room_charges_for_night(
    db: AsyncSession,
    reservation: Reservation,
    night_date: datetime | None = None,
    nights_override: int | None = None,
) -> LineItem:
    """Post a ROOM_CHARGE line item for one or more nights."""
    folio_result = await db.execute(
        select(Folio).where(Folio.reservation_id == reservation.id)
    )
    folio = folio_result.scalar_one_or_none()
    if folio is None:
        raise NotFoundError(detail="Folio not found for reservation")

    nights = nights_override or 1
    total = reservation.rate_per_night * Decimal(str(nights))
    date_label = (night_date or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    description = (
        f"Room {reservation.room_id} — {nights} night(s) @ {reservation.rate_per_night} ({date_label})"
    )

    item = LineItem(
        folio_id=folio.id,
        item_type=LineItemType.ROOM_CHARGE,
        description=description,
        quantity=Decimal(str(nights)),
        unit_price=reservation.rate_per_night,
        total=total,
    )
    db.add(item)

    folio.total_charges += total
    folio.balance = folio.total_charges - folio.total_payments

    await db.flush()
    await db.refresh(item)
    return item
