"""
factory_boy factories for generating test model instances.

Usage:
    user = UserFactory.build()             # unsaved instance
    room_type = RoomTypeFactory.build(base_rate=Decimal("150.00"))
"""

import uuid
from decimal import Decimal

import factory
from faker import Faker

from app.auth.password import hash_password
from app.models.billing import FolioStatus, LineItemType, PaymentMethod
from app.models.guest import Guest, IdDocumentType
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room, RoomCategory, RoomStatus, RoomType
from app.models.user import User, UserRole

fake = Faker()


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.LazyAttribute(lambda _: fake.unique.email())
    hashed_password = factory.LazyFunction(lambda: hash_password("TestPass123!"))
    full_name = factory.LazyAttribute(lambda _: fake.name())
    role = UserRole.FRONT_DESK
    is_active = True


class GuestFactory(factory.Factory):
    class Meta:
        model = Guest

    id = factory.LazyFunction(uuid.uuid4)
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    email = factory.LazyAttribute(lambda _: fake.unique.email())
    phone = factory.LazyAttribute(lambda _: fake.phone_number()[:30])
    nationality = "US"
    doc_type = IdDocumentType.PASSPORT
    doc_number = factory.LazyAttribute(lambda _: fake.bothify(text="??########"))


class RoomTypeFactory(factory.Factory):
    class Meta:
        model = RoomType

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.LazyAttribute(lambda _: fake.unique.word().capitalize() + " Room")
    category = RoomCategory.DOUBLE
    base_rate = Decimal("120.00")
    max_occupancy = 2
    description = factory.LazyAttribute(lambda _: fake.sentence())


class RoomFactory(factory.Factory):
    class Meta:
        model = Room

    id = factory.LazyFunction(uuid.uuid4)
    room_number = factory.LazyAttribute(lambda _: str(fake.unique.random_int(min=100, max=999)))
    floor = factory.LazyAttribute(lambda o: int(o.room_number[0]))
    room_type_id = factory.LazyFunction(uuid.uuid4)
    status = RoomStatus.AVAILABLE
    is_smoking = False
