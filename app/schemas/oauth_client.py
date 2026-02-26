import uuid
from datetime import datetime

from pydantic import BaseModel


class OAuthClientCreate(BaseModel):
    name: str


class OAuthClientRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    client_id: str
    name: str
    is_active: bool
    created_at: datetime


class OAuthClientCreated(OAuthClientRead):
    client_secret: str
