import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.room import RoomCategory, RoomStatus


class RoomTypeCreate(BaseModel):
    name: str
    category: RoomCategory
    description: str | None = None
    base_rate: Decimal
    max_occupancy: int = 2
    amenities: str | None = None  # JSON string e.g. '["wifi","minibar"]'


class RoomTypeRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    category: RoomCategory
    description: str | None
    base_rate: Decimal
    max_occupancy: int
    amenities: str | None
    created_at: datetime
    updated_at: datetime


class RoomTypeUpdate(BaseModel):
    name: str | None = None
    category: RoomCategory | None = None
    description: str | None = None
    base_rate: Decimal | None = None
    max_occupancy: int | None = None
    amenities: str | None = None


class RoomCreate(BaseModel):
    room_number: str
    floor: int
    room_type_id: uuid.UUID
    is_smoking: bool = False
    notes: str | None = None


class RoomRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    room_number: str
    floor: int
    room_type_id: uuid.UUID
    status: RoomStatus
    is_smoking: bool
    notes: str | None
    room_type: RoomTypeRead
    created_at: datetime
    updated_at: datetime


class RoomUpdate(BaseModel):
    floor: int | None = None
    room_type_id: uuid.UUID | None = None
    is_smoking: bool | None = None
    notes: str | None = None


class RoomStatusUpdate(BaseModel):
    status: RoomStatus
