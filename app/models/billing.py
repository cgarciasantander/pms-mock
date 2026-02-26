import enum
import uuid
from decimal import Decimal

from sqlalchemy import Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class FolioStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class LineItemType(str, enum.Enum):
    ROOM_CHARGE = "room_charge"
    FOOD_BEVERAGE = "food_beverage"
    SPA = "spa"
    LAUNDRY = "laundry"
    PARKING = "parking"
    TAX = "tax"
    DISCOUNT = "discount"
    OTHER = "other"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    POINTS = "points"


class Folio(Base, TimestampMixin):
    __tablename__ = "folios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reservations.id"), unique=True, nullable=False
    )
    status: Mapped[FolioStatus] = mapped_column(
        SAEnum(FolioStatus), default=FolioStatus.OPEN, nullable=False
    )
    # Denormalized totals for fast reads — kept in sync by billing_controller
    total_charges: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_payments: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    reservation: Mapped["Reservation"] = relationship(back_populates="folio")  # type: ignore[name-defined]  # noqa: F821
    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="folio", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="folio", cascade="all, delete-orphan"
    )


class LineItem(Base, TimestampMixin):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    folio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[LineItemType] = mapped_column(SAEnum(LineItemType), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=Decimal("1.00"), nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    folio: Mapped["Folio"] = relationship(back_populates="line_items")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    folio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reference_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    folio: Mapped["Folio"] = relationship(back_populates="payments")
