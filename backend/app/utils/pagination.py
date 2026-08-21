from pydantic import BaseModel, Field
from typing import TypeVar, Generic, List, Optional
from fastapi import Query

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=10000, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=10000, description="Items per page"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Alias for size"),
    skip: Optional[int] = Query(None, ge=0, description="Skip N items (overrides page)"),
) -> PaginationParams:
    """FastAPI dependency for pagination parameters. Accepts limit/size and skip/page."""
    actual_size = limit if limit is not None else size
    if skip is not None:
        actual_page = (skip // actual_size) + 1
    else:
        actual_page = page
    return PaginationParams(page=actual_page, size=actual_size)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int
    pages: int


def paginate_query(query, db, params: PaginationParams) -> PaginatedResponse:
    """Apply pagination to a SQLAlchemy query and return a PaginatedResponse."""
    total = query.count()
    items = query.offset(params.offset).limit(params.limit).all()
    pages = (total + params.size - 1) // params.size if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )
