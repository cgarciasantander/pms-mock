# Import all models here so Alembic's autogenerate can discover all tables
# via Base.metadata when alembic/env.py imports this module.

from app.models.billing import Folio, FolioStatus, LineItem, LineItemType, Payment, PaymentMethod
from app.models.guest import Guest, IdDocumentType
from app.models.oauth_client import OAuthClient
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomCategory, RoomStatus, RoomType
from app.models.user import RefreshToken, User, UserRole

__all__ = [
    # User
    "User",
    "UserRole",
    "RefreshToken",
    # Guest
    "Guest",
    "IdDocumentType",
    # Room
    "RoomType",
    "RoomCategory",
    "Room",
    "RoomStatus",
    # Reservation
    "Reservation",
    "ReservationStatus",
    # Billing
    "Folio",
    "FolioStatus",
    "LineItem",
    "LineItemType",
    "Payment",
    "PaymentMethod",
    # OAuth
    "OAuthClient",
]
