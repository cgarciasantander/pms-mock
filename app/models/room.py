import enum
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class RoomCategory(str, enum.Enum):
    SINGLE = "single"
    DOUBLE = "double"
    TWIN = "twin"
    SUITE = "suite"
    PENTHOUSE = "penthouse"


class RoomStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    HOUSEKEEPING = "housekeeping"
    MAINTENANCE = "maintenance"
    OUT_OF_ORDER = "out_of_order"


class RoomType(Base, TimestampMixin):
    __tablename__ = "room_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[RoomCategory] = mapped_column(SAEnum(RoomCategory), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_occupancy: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    # JSON array of amenity strings
    amenities: Mapped[str | None] = mapped_column(Text, nullable=True)

    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    room_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("room_types.id"),
        nullable=False,
    )
    status: Mapped[RoomStatus] = mapped_column(
        SAEnum(RoomStatus), nullable=False, default=RoomStatus.AVAILABLE
    )
    is_smoking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    room_type: Mapped["RoomType"] = relationship(
        back_populates="rooms",
        foreign_keys=[room_type_id],
        primaryjoin="Room.room_type_id == RoomType.id",
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="room")  # type: ignore[name-defined]  # noqa: F821
