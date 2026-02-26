import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers import billing_controller
from app.database.session import get_db
from app.dependencies import get_current_principal, require_role
from app.models.billing import Folio, LineItem, Payment
from app.models.user import UserRole
from app.schemas.billing import (
    FolioRead,
    FolioStatement,
    LineItemCreate,
    LineItemRead,
    PaymentCreate,
    PaymentRead,
)
from app.schemas.common import MessageResponse

router = APIRouter()

_auth = Depends(get_current_principal)
_front_desk = Depends(
    require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.FRONT_DESK)
)


@router.get("/{folio_id}", response_model=FolioRead, dependencies=[_auth])
async def get_folio(folio_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Folio:
    return await billing_controller.get_folio(db, folio_id)


@router.get("/{folio_id}/statement", response_model=FolioStatement, dependencies=[_auth])
async def get_statement(
    folio_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> FolioStatement:
    return await billing_controller.get_folio_statement(db, folio_id)


@router.get(
    "/by-reservation/{reservation_id}", response_model=FolioRead, dependencies=[_auth]
)
async def get_folio_by_reservation(
    reservation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Folio:
    return await billing_controller.get_folio_by_reservation(db, reservation_id)


@router.post(
    "/{folio_id}/line-items",
    response_model=LineItemRead,
    status_code=201,
    dependencies=[_front_desk],
)
async def add_line_item(
    folio_id: uuid.UUID,
    data: LineItemCreate,
    db: AsyncSession = Depends(get_db),
) -> LineItem:
    return await billing_controller.add_line_item(db, folio_id, data)


@router.post(
    "/{folio_id}/line-items/{line_item_id}/void",
    response_model=LineItemRead,
    dependencies=[_front_desk],
)
async def void_line_item(
    folio_id: uuid.UUID,
    line_item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LineItem:
    return await billing_controller.void_line_item(db, line_item_id)


@router.post(
    "/{folio_id}/payments",
    response_model=PaymentRead,
    status_code=201,
    dependencies=[_front_desk],
)
async def post_payment(
    folio_id: uuid.UUID,
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
) -> Payment:
    return await billing_controller.post_payment(db, folio_id, data)


@router.post(
    "/{folio_id}/close", response_model=FolioRead, dependencies=[_front_desk]
)
async def close_folio(folio_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Folio:
    return await billing_controller.close_folio(db, folio_id)
