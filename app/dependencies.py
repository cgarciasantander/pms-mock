from fastapi import Depends
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token, verify_token_type
from app.auth.oauth2_scheme import oauth2_scheme
from app.database.session import get_db
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models.oauth_client import OAuthClient
from app.models.user import User, UserRole


async def get_current_principal(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | OAuthClient:
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError()

    if not verify_token_type(payload, "access"):
        raise UnauthorizedError()

    sub: str | None = payload.get("sub")
    if not sub:
        raise UnauthorizedError()

    if payload.get("grant") == "client_credentials":
        result = await db.execute(
            select(OAuthClient).where(OAuthClient.client_id == sub)
        )
        client = result.scalar_one_or_none()
        if client is None or not client.is_active:
            raise UnauthorizedError()
        return client

    user = await db.get(User, sub)
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return user


async def get_current_user(
    principal: User | OAuthClient = Depends(get_current_principal),
) -> User:
    if isinstance(principal, OAuthClient):
        raise UnauthorizedError()
    return principal


def require_role(*roles: UserRole):
    """Dependency factory for role-based access control.

    OAuth clients bypass role checks and are granted full access.
    """

    async def checker(
        principal: User | OAuthClient = Depends(get_current_principal),
    ) -> User | OAuthClient:
        if isinstance(principal, OAuthClient):
            return principal
        if principal.role not in roles:
            raise ForbiddenError()
        return principal

    return checker
