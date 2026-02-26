import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers import user_controller
from app.database.session import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import PasswordChange, RoleUpdate, UserCreate, UserRead, UserUpdate

router = APIRouter()

_admin_only = Depends(require_role(UserRole.ADMIN))
_managers = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))


@router.post("/", response_model=UserRead, status_code=201, dependencies=[_admin_only])
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_controller.create_user(db, data)


@router.get("/", response_model=PaginatedResponse[UserRead], dependencies=[_managers])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserRead]:
    users, total = await user_controller.get_users(db, skip=skip, limit=limit)
    return PaginatedResponse(items=users, total=total, skip=skip, limit=limit)  # type: ignore[arg-type]


@router.get("/{user_id}", response_model=UserRead, dependencies=[_managers])
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> User:
    return await user_controller.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Users can update themselves; admins can update anyone
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        from app.exceptions import ForbiddenError
        raise ForbiddenError()
    return await user_controller.update_user(db, user_id, data)


@router.patch("/{user_id}/role", response_model=UserRead, dependencies=[_admin_only])
async def update_role(
    user_id: uuid.UUID,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_controller.update_role(db, user_id, data.role)


@router.delete("/{user_id}", response_model=MessageResponse, dependencies=[_admin_only])
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await user_controller.deactivate_user(db, user_id)
    return MessageResponse(message="User deactivated")


@router.post("/{user_id}/change-password", response_model=MessageResponse)
async def change_password(
    user_id: uuid.UUID,
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    if current_user.id != user_id:
        from app.exceptions import ForbiddenError
        raise ForbiddenError()
    await user_controller.change_password(db, current_user, data.old_password, data.new_password)
    return MessageResponse(message="Password changed successfully")
