import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.reservation import ReservationStatus


class ReservationCreate(BaseModel):
    guest_id: uuid.UUID
    room_id: uuid.UUID
    check_in_date: date
    check_out_date: date
    adults: int = 1
    children: int = 0
    special_requests: str | None = None

    @model_validator(mode="after")
    def check_dates(self) -> "ReservationCreate":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")
        return self


class ReservationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    confirmation_no: str
    guest_id: uuid.UUID
    room_id: uuid.UUID
    check_in_date: date
    check_out_date: date
    adults: int
    children: int
    status: ReservationStatus
    rate_per_night: Decimal
    special_requests: str | None
    created_at: datetime
    updated_at: datetime


class ReservationUpdate(BaseModel):
    check_in_date: date | None = None
    check_out_date: date | None = None
    room_id: uuid.UUID | None = None
    adults: int | None = None
    children: int | None = None
    special_requests: str | None = None

    @model_validator(mode="after")
    def check_dates(self) -> "ReservationUpdate":
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValueError("check_out_date must be after check_in_date")
        return self


class CheckInRequest(BaseModel):
    early_check_in: bool = False


class CheckOutResponse(BaseModel):
    reservation_id: uuid.UUID
    confirmation_no: str
    folio_id: uuid.UUID
    balance: Decimal
    message: str
