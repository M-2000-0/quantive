"""Pagination, search, and filtering utilities for API endpoints.

Provides:
- Cursor-based pagination with consistent response format
- Full-text search across specified fields
- Filtering by exact match, range, and date range
- Consistent headers: X-Total-Count, X-Page-Count, Link
"""
import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Generic, Optional, Sequence, TypeVar

from fastapi import Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import Column, asc, desc, or_
from sqlalchemy.orm import Query as SQLAlchemyQuery, Session

T = TypeVar("T")


@dataclass
class PaginationParams:
    """Parsed pagination parameters."""
    limit: int
    offset: int
    cursor: Optional[str]
    search: Optional[str]
    sort_by: Optional[str]
    sort_order: str  # "asc" or "desc"


@dataclass
class PaginationMeta:
    """Metadata for paginated responses."""
    total: int
    limit: int
    offset: int
    has_more: bool
    next_cursor: Optional[str] = None


def encode_cursor(offset: int, extra: Optional[dict] = None) -> str:
    """Encode pagination cursor."""
    data = {"o": offset}
    if extra:
        data.update(extra)
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode pagination cursor."""
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        return {"o": 0}


def paginate_query(
    query: SQLAlchemyQuery,
    limit: int = 20,
    offset: int = 0,
    cursor: Optional[str] = None,
    search: Optional[str] = None,
    search_fields: Optional[list[str]] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    model: Optional[Any] = None,
) -> tuple[Sequence[Any], int]:
    """Apply pagination, search, and sorting to a SQLAlchemy query.

    Returns:
        Tuple of (items, total_count)
    """
    # Decode cursor if provided
    if cursor:
        cursor_data = decode_cursor(cursor)
        offset = cursor_data.get("o", 0)

    # Apply search filter
    if search and search_fields and model:
        search_conditions = []
        for field_name in search_fields:
            column = getattr(model, field_name, None)
            if column is not None and hasattr(column, "like"):
                search_conditions.append(column.ilike(f"%{search}%"))
        if search_conditions:
            query = query.filter(or_(*search_conditions))

    # Get total count before applying limit/offset
    total = query.count()

    # Apply sorting
    if sort_by and model:
        sort_column = getattr(model, sort_by, None)
        if sort_column is not None:
            if sort_order == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

    # Apply limit and offset
    items = query.offset(offset).limit(limit).all()

    return items, total


def create_paginated_response(
    items: Sequence[Any],
    total: int,
    limit: int,
    offset: int,
    serializer: Callable[[Any], Any],
    request: Optional[Request] = None,
) -> JSONResponse:
    """Create a paginated JSON response with proper headers.

    Args:
        items: List of items to serialize
        total: Total count of items (without pagination)
        limit: Page size
        offset: Current offset
        serializer: Function to serialize each item
        request: Optional FastAPI request for URL generation
    """
    has_more = (offset + limit) < total
    next_cursor = encode_cursor(offset + limit) if has_more else None

    data = [serializer(item) for item in items]
    meta = PaginationMeta(
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
        next_cursor=next_cursor,
    )

    response_data = {
        "data": data,
        "meta": {
            "total": meta.total,
            "limit": meta.limit,
            "offset": meta.offset,
            "has_more": meta.has_more,
            "next_cursor": meta.next_cursor,
        },
    }

    headers = {
        "X-Total-Count": str(total),
        "X-Page-Count": str((total + limit - 1) // limit if limit > 0 else 0),
        "X-Has-More": "true" if has_more else "false",
    }

    if next_cursor:
        headers["X-Next-Cursor"] = next_cursor

    return JSONResponse(content=response_data, headers=headers)


class PaginationQuery:
    """FastAPI dependency for pagination query parameters."""

    def __init__(
        self,
        limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
        offset: int = Query(default=0, ge=0, description="Items to skip"),
        cursor: Optional[str] = Query(default=None, description="Pagination cursor"),
        search: Optional[str] = Query(default=None, min_length=1, max_length=200, description="Search query"),
        sort_by: Optional[str] = Query(default=None, description="Field to sort by"),
        sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order"),
    ):
        self.limit = limit
        self.offset = offset
        self.cursor = cursor
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order


class FilterQuery:
    """FastAPI dependency for filtering query parameters."""

    def __init__(
        self,
        status: Optional[str] = Query(default=None, description="Filter by status"),
        org_id: Optional[str] = Query(default=None, description="Filter by organization"),
        created_after: Optional[datetime] = Query(default=None, description="Created after date"),
        created_before: Optional[datetime] = Query(default=None, description="Created before date"),
        currency: Optional[str] = Query(default=None, description="Filter by currency"),
        instrument_type: Optional[str] = Query(default=None, description="Filter by instrument type"),
        min_principal: Optional[float] = Query(default=None, ge=0, description="Minimum principal"),
        max_principal: Optional[float] = Query(default=None, ge=0, description="Maximum principal"),
    ):
        self.status = status
        self.org_id = org_id
        self.created_after = created_after
        self.created_before = created_before
        self.currency = currency
        self.instrument_type = instrument_type
        self.min_principal = min_principal
        self.max_principal = max_principal


def apply_filters(
    query: SQLAlchemyQuery,
    filters: FilterQuery,
    model: Any,
) -> SQLAlchemyQuery:
    """Apply filter parameters to a SQLAlchemy query."""
    if filters.status:
        status_col = getattr(model, "status", None)
        if status_col is not None:
            query = query.filter(status_col == filters.status)

    if filters.org_id:
        org_col = getattr(model, "org_id", None)
        if org_col is not None:
            query = query.filter(org_col == filters.org_id)

    if filters.created_after:
        created_col = getattr(model, "created_at", None)
        if created_col is not None:
            query = query.filter(created_col >= filters.created_after)

    if filters.created_before:
        created_col = getattr(model, "created_at", None)
        if created_col is not None:
            query = query.filter(created_col <= filters.created_before)

    if filters.currency:
        ccy_col = getattr(model, "currency", None)
        if ccy_col is not None:
            query = query.filter(ccy_col == filters.currency.upper())

    if filters.instrument_type:
        type_col = getattr(model, "instrument_type", None)
        if type_col is not None:
            query = query.filter(type_col == filters.instrument_type)

    if filters.min_principal is not None:
        principal_col = getattr(model, "principal_outstanding", None)
        if principal_col is not None:
            query = query.filter(principal_col >= filters.min_principal)

    if filters.max_principal is not None:
        principal_col = getattr(model, "principal_outstanding", None)
        if principal_col is not None:
            query = query.filter(principal_col <= filters.max_principal)

    return query
