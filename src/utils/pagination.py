"""A generic pagination envelope.

Pair this with the ``Pagination`` dependency from
``src.core.dependencies`` whenever an endpoint needs to return page
metadata (total count, page number, has_next, ...) instead of a bare
``list[T]``::

    from src.utils.pagination import Page

    @router.get("/widgets", response_model=Page[WidgetRead])
    def list_widgets(db: DbSession, pagination: Pagination):
        items = service.list_widgets(db, offset=pagination.offset, limit=pagination.limit)
        total = service.count_widgets(db)
        return Page.build(items, total=total, page=pagination.page, per_page=pagination.per_page)
"""
from __future__ import annotations

from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def build(
        cls,
        items: Sequence[T],
        *,
        total: int,
        page: int,
        per_page: int,
    ) -> "Page[T]":
        pages = (total + per_page - 1) // per_page if total else 0
        return cls(
            items=list(items),
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
