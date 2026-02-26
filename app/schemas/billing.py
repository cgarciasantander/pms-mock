import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.billing import FolioStatus, LineItemType, PaymentMethod


class LineItemCreate(BaseModel):
    item_type: LineItemType
    description: str
    quantity: Decimal = Decimal("1.00")
    unit_price: Decimal


class LineItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    folio_id: uuid.UUID
    item_type: LineItemType
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    created_at: datetime


class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: Decimal
    reference_no: str | None = None
    notes: str | None = None


class PaymentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    folio_id: uuid.UUID
    method: PaymentMethod
    amount: Decimal
    reference_no: str | None
    notes: str | None
    created_at: datetime


class FolioRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    reservation_id: uuid.UUID
    status: FolioStatus
    total_charges: Decimal
    total_payments: Decimal
    balance: Decimal
    created_at: datetime
    updated_at: datetime


class FolioStatement(BaseModel):
    folio: FolioRead
    line_items: list[LineItemRead]
    payments: list[PaymentRead]
