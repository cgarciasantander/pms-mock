from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from app.auth.password import hash_token, verify_password
from app.config import settings
from app.exceptions import UnauthorizedError
from app.models.user import RefreshToken, User
from app.schemas.auth import TokenResponse


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError(detail="Incorrect email or password")

    if not user.is_active:
        raise UnauthorizedError(detail="Inactive user account")

    return user


async def issue_token_pair(db: AsyncSession, user: User) -> TokenResponse:
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    raw_refresh, expires_at = create_refresh_token(subject=str(user.id))

    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
    )
    db.add(token_record)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_token_pair(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(raw_refresh_token)
    except JWTError:
        raise UnauthorizedError(detail="Invalid refresh token")

    if not verify_token_type(payload, "refresh"):
        raise UnauthorizedError(detail="Invalid token type")

    token_hash = hash_token(raw_refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if token_record is None or token_record.revoked:
        raise UnauthorizedError(detail="Refresh token has been revoked")

    if token_record.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError(detail="Refresh token has expired")

    # Revoke old token
    token_record.revoked = True
    await db.flush()

    user = await db.get(User, token_record.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()

    return await issue_token_pair(db, user)


async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = hash_token(raw_refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()
    if token_record:
        token_record.revoked = True
        await db.flush()


async def revoke_all_user_tokens(db: AsyncSession, user_id: str) -> None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    for token in result.scalars():
        token.revoked = True
    await db.flush()
