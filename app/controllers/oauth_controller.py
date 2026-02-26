import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_token
from app.exceptions import NotFoundError, UnauthorizedError
from app.models.oauth_client import OAuthClient
from app.schemas.oauth_client import OAuthClientCreate


async def create_client(
    db: AsyncSession, data: OAuthClientCreate
) -> tuple[OAuthClient, str]:
    client_id = secrets.token_urlsafe(16)
    client_secret = secrets.token_urlsafe(32)
    client = OAuthClient(
        client_id=client_id,
        client_secret_hash=hash_token(client_secret),
        name=data.name,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client, client_secret


async def authenticate_client(
    db: AsyncSession, client_id: str | None, client_secret: str | None
) -> OAuthClient:
    if not client_id or not client_secret:
        raise UnauthorizedError()
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.client_id == client_id)
    )
    client = result.scalar_one_or_none()
    if client is None or not client.is_active:
        raise UnauthorizedError()
    if client.client_secret_hash != hash_token(client_secret):
        raise UnauthorizedError()
    return client


async def list_clients(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> tuple[list[OAuthClient], int]:
    result = await db.execute(select(OAuthClient).offset(skip).limit(limit))
    clients = list(result.scalars())
    total = (
        await db.execute(select(func.count()).select_from(OAuthClient))
    ).scalar_one()
    return clients, total


async def get_client(db: AsyncSession, client_id_uuid: uuid.UUID) -> OAuthClient:
    client = await db.get(OAuthClient, client_id_uuid)
    if client is None:
        raise NotFoundError(detail="OAuth client not found")
    return client


async def delete_client(db: AsyncSession, client_id_uuid: uuid.UUID) -> None:
    client = await get_client(db, client_id_uuid)
    await db.delete(client)
    await db.flush()


async def rotate_secret(
    db: AsyncSession, client_id_uuid: uuid.UUID
) -> tuple[OAuthClient, str]:
    client = await get_client(db, client_id_uuid)
    new_secret = secrets.token_urlsafe(32)
    client.client_secret_hash = hash_token(new_secret)
    await db.flush()
    await db.refresh(client)
    return client, new_secret
