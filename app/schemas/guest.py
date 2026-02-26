import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr

from app.models.guest import IdDocumentType


class GuestCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = None
    address: str | None = None
    doc_type: IdDocumentType | None = None
    doc_number: str | None = None
    preferences: str | None = None
    notes: str | None = None


class GuestRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    date_of_birth: date | None
    nationality: str | None
    address: str | None
    doc_type: IdDocumentType | None
    doc_number: str | None
    preferences: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class GuestUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = None
    address: str | None = None
    doc_type: IdDocumentType | None = None
    doc_number: str | None = None
    preferences: str | None = None
    notes: str | None = None
