#!/usr/bin/env python3
"""Seed the database with realistic fake data for development.

Usage:
    python -m scripts.seed
"""
import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy import select

from app.auth.password import hash_password
from app.controllers import billing_controller, reservation_controller
from app.controllers import oauth_controller
from app.database.session import AsyncSessionLocal
from app.models.billing import Folio, LineItemType, PaymentMethod
from app.models.guest import Guest, IdDocumentType
from app.models.reservation import Reservation
from app.models.room import Room, RoomCategory, RoomType
from app.models.user import User, UserRole
from app.schemas.billing import LineItemCreate, PaymentCreate
from app.schemas.oauth_client import OAuthClientCreate
from app.schemas.reservation import ReservationCreate

fake = Faker()
TODAY = date.today()

# ── Static seed data ───────────────────────────────────────────────────────────

STAFF = [
    {"email": "admin@hotel.com",       "full_name": "Admin User",      "role": UserRole.ADMIN},
    {"email": "manager@hotel.com",     "full_name": "Maria Gonzalez",  "role": UserRole.MANAGER},
    {"email": "frontdesk1@hotel.com",  "full_name": "James Parker",    "role": UserRole.FRONT_DESK},
    {"email": "frontdesk2@hotel.com",  "full_name": "Aisha Rahman",    "role": UserRole.FRONT_DESK},
    {"email": "housekeeping@hotel.com","full_name": "Carlos Silva",    "role": UserRole.HOUSEKEEPING},
]

ROOM_TYPES = [
    {
        "name": "Standard Single",
        "category": RoomCategory.SINGLE,
        "description": "Cosy room with a single bed, ideal for solo travellers.",
        "base_rate": Decimal("89.00"),
        "max_occupancy": 1,
        "amenities": '["wifi","tv","safe"]',
    },
    {
        "name": "Deluxe Double",
        "category": RoomCategory.DOUBLE,
        "description": "Spacious room with a queen bed and city view.",
        "base_rate": Decimal("149.00"),
        "max_occupancy": 2,
        "amenities": '["wifi","tv","minibar","safe"]',
    },
    {
        "name": "Executive Twin",
        "category": RoomCategory.TWIN,
        "description": "Bright room with two single beds, perfect for colleagues.",
        "base_rate": Decimal("159.00"),
        "max_occupancy": 2,
        "amenities": '["wifi","tv","minibar","safe","bathrobe"]',
    },
    {
        "name": "Junior Suite",
        "category": RoomCategory.SUITE,
        "description": "Elegant suite with a separate living area and king bed.",
        "base_rate": Decimal("299.00"),
        "max_occupancy": 3,
        "amenities": '["wifi","tv","minibar","safe","bathrobe","jacuzzi"]',
    },
    {
        "name": "Grand Penthouse",
        "category": RoomCategory.PENTHOUSE,
        "description": "Luxury penthouse spanning the top floor with panoramic views.",
        "base_rate": Decimal("699.00"),
        "max_occupancy": 4,
        "amenities": '["wifi","tv","minibar","safe","bathrobe","jacuzzi","butler"]',
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fake_guest_payload() -> dict:
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "phone": fake.phone_number()[:20],
        "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80),
        "nationality": fake.country_code(representation="alpha-2"),
        "address": fake.address().replace("\n", ", ")[:255],
        "doc_type": random.choice(list(IdDocumentType)),
        "doc_number": fake.bothify("??#######").upper(),
        "preferences": random.choice([
            "High floor preferred",
            "Extra pillows please",
            "Late check-in expected",
            "Quiet room away from elevator",
            None,
        ]),
        "notes": None,
    }


# ── Main seed ──────────────────────────────────────────────────────────────────

async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ── Idempotency guard ──────────────────────────────────────────────────
        existing = (await db.execute(select(User))).scalars().first()
        if existing:
            print("Database already seeded — skipping.")
            return

        print("Seeding database...")

        # ── Users ──────────────────────────────────────────────────────────────
        users: list[User] = []
        for s in STAFF:
            user = User(
                email=s["email"],
                hashed_password=hash_password("admin123"),
                full_name=s["full_name"],
                role=s["role"],
            )
            db.add(user)
            users.append(user)

        await db.flush()
        print(f"  Created {len(users)} users")

        # ── Room types ─────────────────────────────────────────────────────────
        room_types: list[RoomType] = []
        for rt_data in ROOM_TYPES:
            rt = RoomType(**rt_data)
            db.add(rt)
            room_types.append(rt)

        await db.flush()
        print(f"  Created {len(room_types)} room types")

        # ── Rooms (5 per type, floors 1-5) ─────────────────────────────────────
        # Room numbers: floor * 100 + sequence, e.g. 101-105, 201-205 …
        rooms: list[Room] = []
        for floor, rt in enumerate(room_types, start=1):
            for seq in range(1, 6):
                room = Room(
                    room_number=f"{floor}{seq:02d}",
                    floor=floor,
                    room_type_id=rt.id,
                    is_smoking=False,
                )
                db.add(room)
                rooms.append(room)

        await db.flush()
        print(f"  Created {len(rooms)} rooms")

        # ── Guests ─────────────────────────────────────────────────────────────
        guests: list[Guest] = []
        for _ in range(30):
            g = Guest(**_fake_guest_payload())
            db.add(g)
            guests.append(g)

        await db.flush()
        print(f"  Created {len(guests)} guests")

        # Shuffle so reservations get varied guests and rooms
        random.shuffle(guests)
        room_pool = list(rooms)  # copy — pop from front for each reservation

        # ── Helper: create reservation via controller ──────────────────────────
        async def make_reservation(
            room: Room, guest: Guest, check_in: date, check_out: date, adults: int = 1
        ) -> Reservation:
            data = ReservationCreate(
                guest_id=guest.id,
                room_id=room.id,
                check_in_date=check_in,
                check_out_date=check_out,
                adults=min(adults, room.room_type.max_occupancy),
            )
            return await reservation_controller.create_reservation(db, data)

        # ── 1. CHECKED_OUT reservations (7) — past stays with closed folios ───
        checked_out_rooms = room_pool[:7]
        for i, room in enumerate(checked_out_rooms):
            check_in  = TODAY - timedelta(days=14 + i * 2)
            check_out = check_in + timedelta(days=random.randint(2, 5))
            guest = guests[i]

            res = await make_reservation(room, guest, check_in, check_out, adults=random.randint(1, 2))
            await reservation_controller.check_in(db, res.id)
            await reservation_controller.check_out(db, res.id)

            # Post full-balance payment and close the folio
            folio_row = (
                await db.execute(select(Folio).where(Folio.reservation_id == res.id))
            ).scalar_one()
            if folio_row.balance > 0:
                await billing_controller.post_payment(
                    db,
                    folio_row.id,
                    PaymentCreate(
                        method=random.choice(list(PaymentMethod)),
                        amount=folio_row.balance,
                        reference_no=fake.bothify("TXN-####-????").upper(),
                    ),
                )
            await billing_controller.close_folio(db, folio_row.id)

        print("  Created 7 checked-out reservations (folios closed)")

        # ── 2. CHECKED_IN reservations (5) — current in-house guests ──────────
        checked_in_rooms = room_pool[7:12]
        for i, room in enumerate(checked_in_rooms):
            check_in  = TODAY - timedelta(days=random.randint(1, 3))
            check_out = TODAY + timedelta(days=random.randint(1, 4))
            guest = guests[7 + i]

            res = await make_reservation(room, guest, check_in, check_out, adults=random.randint(1, 2))
            await reservation_controller.check_in(db, res.id)

            # Add an incidental charge
            folio_row = (
                await db.execute(select(Folio).where(Folio.reservation_id == res.id))
            ).scalar_one()
            await billing_controller.add_line_item(
                db,
                folio_row.id,
                LineItemCreate(
                    item_type=random.choice([LineItemType.FOOD_BEVERAGE, LineItemType.SPA, LineItemType.PARKING]),
                    description=random.choice(["Room service — dinner", "Spa treatment", "Valet parking"]),
                    quantity=Decimal("1.00"),
                    unit_price=Decimal(str(random.randint(20, 120))),
                ),
            )

        print("  Created 5 checked-in reservations (in-house)")

        # ── 3. CONFIRMED reservations (7) — upcoming bookings ─────────────────
        confirmed_rooms = room_pool[12:19]
        for i, room in enumerate(confirmed_rooms):
            check_in  = TODAY + timedelta(days=7 + i * 10)
            check_out = check_in + timedelta(days=random.randint(2, 5))
            guest = guests[12 + i]

            await make_reservation(room, guest, check_in, check_out, adults=random.randint(1, 2))

        print("  Created 7 confirmed (future) reservations")

        # ── 4. CANCELLED reservations (3) ────────────────────────────────────
        cancelled_rooms = room_pool[19:22]
        for i, room in enumerate(cancelled_rooms):
            check_in  = TODAY + timedelta(days=20 + i * 14)
            check_out = check_in + timedelta(days=3)
            guest = guests[19 + i]

            res = await make_reservation(room, guest, check_in, check_out)
            await reservation_controller.cancel_reservation(db, res.id, reason="Guest request")

        print("  Created 3 cancelled reservations")

        # ── 5. NO-SHOW reservations (3) ───────────────────────────────────────
        noshow_rooms = room_pool[22:25]
        for i, room in enumerate(noshow_rooms):
            check_in  = TODAY - timedelta(days=3 + i)
            check_out = check_in + timedelta(days=2)
            guest = guests[22 + i]

            res = await make_reservation(room, guest, check_in, check_out)
            await reservation_controller.mark_no_show(db, res.id)

        print("  Created 3 no-show reservations")

        # ── 6. OAuth clients ──────────────────────────────────────────────────
        oauth_clients = [
            ("PMS Mobile App",       "Client for the hotel's guest-facing mobile application"),
            ("Channel Manager",      "Booking.com / Expedia channel manager integration"),
            ("Revenue Dashboard",    "Read-only reporting and analytics service"),
        ]
        client_creds: list[tuple[str, str, str]] = []
        for name, _ in oauth_clients:
            client, raw_secret = await oauth_controller.create_client(
                db, OAuthClientCreate(name=name)
            )
            client_creds.append((name, client.client_id, raw_secret))

        print(f"  Created {len(client_creds)} OAuth clients")

        await db.commit()
        print("\nDone! Seed credentials:")
        print("  admin@hotel.com        / admin123  (admin)")
        print("  manager@hotel.com      / admin123  (manager)")
        print("  frontdesk1@hotel.com   / admin123  (front desk)")
        print("  frontdesk2@hotel.com   / admin123  (front desk)")
        print("  housekeeping@hotel.com / admin123  (housekeeping)")
        print("\n  OAuth clients (client_credentials grant) — secrets shown once:")
        for name, client_id, secret in client_creds:
            print(f"  [{name}]")
            print(f"    client_id:     {client_id}")
            print(f"    client_secret: {secret}")


if __name__ == "__main__":
    asyncio.run(seed())
