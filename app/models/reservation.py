import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    confirmation_no: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guests.id"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False
    )
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    adults: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    children: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus), nullable=False, default=ReservationStatus.CONFIRMED
    )
    # Snapshot of nightly rate at booking time — decoupled from room_type.base_rate
    rate_per_night: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)

    guest: Mapped["Guest"] = relationship(back_populates="reservations")  # type: ignore[name-defined]  # noqa: F821
    room: Mapped["Room"] = relationship(back_populates="reservations")  # type: ignore[name-defined]  # noqa: F821
    folio: Mapped["Folio | None"] = relationship(back_populates="reservation", uselist=False)  # type: ignore[name-defined]  # noqa: F821
