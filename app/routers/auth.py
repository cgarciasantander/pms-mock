import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_client_access_token
from app.config import settings
from app.controllers import auth_controller
from app.controllers import oauth_controller
from app.database.session import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.auth import LogoutRequest, TokenRefreshRequest, TokenResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.oauth_client import OAuthClientCreate, OAuthClientCreated, OAuthClientRead
from app.schemas.user import UserRead

router = APIRouter()

_admin = Depends(require_role(UserRole.ADMIN))


@router.post("/token", response_model=TokenResponse, summary="Obtain JWT access token")
async def token(
    grant_type: str = Form(...),
    username: str | None = Form(default=None),
    password: str | None = Form(default=None),
    client_id: str | None = Form(default=None),
    client_secret: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Supports `password` and `client_credentials` grant types."""
    if grant_type == "password":
        user = await auth_controller.authenticate_user(db, username, password)
        return await auth_controller.issue_token_pair(db, user)
    elif grant_type == "client_credentials":
        client = await oauth_controller.authenticate_client(db, client_id, client_secret)
        access_token = create_client_access_token(client.client_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=None,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant_type")


@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
async def refresh(
    body: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair (rotation)."""
    return await auth_controller.refresh_token_pair(db, body.refresh_token)


@router.post("/logout", summary="Revoke refresh token")
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await auth_controller.revoke_refresh_token(db, body.refresh_token)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserRead, summary="Get current user profile")
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ── OAuth Client Management (admin only) ─────────────────────────────────────


@router.post(
    "/clients",
    response_model=OAuthClientCreated,
    status_code=201,
    dependencies=[_admin],
    summary="Register a new OAuth client",
)
async def create_client(
    data: OAuthClientCreate,
    db: AsyncSession = Depends(get_db),
) -> OAuthClientCreated:
    client, raw_secret = await oauth_controller.create_client(db, data)
    return OAuthClientCreated(
        id=client.id,
        client_id=client.client_id,
        name=client.name,
        is_active=client.is_active,
        created_at=client.created_at,
        client_secret=raw_secret,
    )


@router.get(
    "/clients",
    response_model=PaginatedResponse[OAuthClientRead],
    dependencies=[_admin],
    summary="List OAuth clients",
)
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OAuthClientRead]:
    clients, total = await oauth_controller.list_clients(db, skip=skip, limit=limit)
    return PaginatedResponse(items=clients, total=total, skip=skip, limit=limit)  # type: ignore[arg-type]


@router.get(
    "/clients/{client_id}",
    response_model=OAuthClientRead,
    dependencies=[_admin],
    summary="Get OAuth client by ID",
)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OAuthClientRead:
    return await oauth_controller.get_client(db, client_id)  # type: ignore[return-value]


@router.delete(
    "/clients/{client_id}",
    response_model=MessageResponse,
    dependencies=[_admin],
    summary="Delete OAuth client",
)
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await oauth_controller.delete_client(db, client_id)
    return MessageResponse(message="OAuth client deleted")


@router.post(
    "/clients/{client_id}/rotate-secret",
    response_model=OAuthClientCreated,
    dependencies=[_admin],
    summary="Rotate OAuth client secret",
)
async def rotate_secret(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OAuthClientCreated:
    client, raw_secret = await oauth_controller.rotate_secret(db, client_id)
    return OAuthClientCreated(
        id=client.id,
        client_id=client.client_id,
        name=client.name,
        is_active=client.is_active,
        created_at=client.created_at,
        client_secret=raw_secret,
    )
