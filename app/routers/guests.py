import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers import guest_controller
from app.database.session import get_db
from app.dependencies import get_current_principal
from app.models.guest import Guest
from app.models.reservation import Reservation
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.guest import GuestCreate, GuestRead, GuestUpdate
from app.schemas.reservation import ReservationRead

router = APIRouter()

_auth = Depends(get_current_principal)


@router.post("/", response_model=GuestRead, status_code=201, dependencies=[_auth])
async def create_guest(
    data: GuestCreate,
    db: AsyncSession = Depends(get_db),
) -> Guest:
    return await guest_controller.create_guest(db, data)


@router.get("/", response_model=PaginatedResponse[GuestRead], dependencies=[_auth])
async def list_guests(
    q: str = Query("", description="Search by name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[GuestRead]:
    guests, total = await guest_controller.search_guests(db, query=q, skip=skip, limit=limit)
    return PaginatedResponse(items=guests, total=total, skip=skip, limit=limit)  # type: ignore[arg-type]


@router.get("/{guest_id}", response_model=GuestRead, dependencies=[_auth])
async def get_guest(guest_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Guest:
    return await guest_controller.get_guest(db, guest_id)


@router.patch("/{guest_id}", response_model=GuestRead, dependencies=[_auth])
async def update_guest(
    guest_id: uuid.UUID,
    data: GuestUpdate,
    db: AsyncSession = Depends(get_db),
) -> Guest:
    return await guest_controller.update_guest(db, guest_id, data)


@router.delete("/{guest_id}", response_model=MessageResponse, dependencies=[_auth])
async def delete_guest(
    guest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await guest_controller.delete_guest(db, guest_id)
    return MessageResponse(message="Guest deleted")


@router.get(
    "/{guest_id}/stay-history",
    response_model=list[ReservationRead],
    dependencies=[_auth],
)
async def stay_history(
    guest_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[Reservation]:
    return await guest_controller.get_guest_stay_history(db, guest_id)
