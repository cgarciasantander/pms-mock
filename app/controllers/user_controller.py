import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password, verify_password
from app.controllers.auth_controller import revoke_all_user_tokens
from app.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError(detail="A user with this email already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError(detail="User not found")
    return user


async def get_users(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> tuple[list[User], int]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = list(result.scalars())
    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar_one()
    return users, total


async def update_user(db: AsyncSession, user_id: uuid.UUID, data: UserUpdate) -> User:
    user = await get_user(db, user_id)

    if data.email and data.email != user.email:
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise ConflictError(detail="Email already in use")
        user.email = data.email

    if data.full_name:
        user.full_name = data.full_name

    await db.flush()
    await db.refresh(user)
    return user


async def update_role(db: AsyncSession, user_id: uuid.UUID, role: UserRole) -> User:
    user = await get_user(db, user_id)
    user.role = role
    await db.flush()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await get_user(db, user_id)
    user.is_active = False
    await revoke_all_user_tokens(db, str(user_id))
    await db.flush()
    await db.refresh(user)
    return user


async def change_password(
    db: AsyncSession,
    user: User,
    old_password: str,
    new_password: str,
) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise UnauthorizedError(detail="Current password is incorrect")

    user.hashed_password = hash_password(new_password)
    await revoke_all_user_tokens(db, str(user.id))
    await db.flush()
