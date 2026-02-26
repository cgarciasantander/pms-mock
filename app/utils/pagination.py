from typing import TypeVar

from app.schemas.common import PaginatedResponse

T = TypeVar("T")


def paginate(items: list[T], total: int, skip: int, limit: int) -> PaginatedResponse[T]:
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)
