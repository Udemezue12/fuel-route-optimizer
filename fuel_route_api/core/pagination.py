from typing import Generic, List, TypeVar

from ninja import Schema
from ninja_extra.pagination import PaginationBase

T = TypeVar("T")


class CustomPaginatedOutput(Schema, Generic[T]):
    items: List[T]
    total: int
    per_page: int


class CustomPagination(PaginationBase):
    class Input(Schema):
        skip: int = 0
        limit: int = 6

    def paginate_queryset(self, queryset, pagination: Input, **params):
        skip = pagination.skip
        limit = pagination.limit
        total = len(queryset) if isinstance(queryset, list) else queryset.count()
        return {
            "items": queryset[skip : skip + limit],
            "total": total,
            "per_page": limit,
        }
