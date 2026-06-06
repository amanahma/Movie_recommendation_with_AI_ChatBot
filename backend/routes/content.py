"""
Content routes: the unified movies + series catalog.

Replaces the old /movies endpoints. Reads from the in-memory catalog
(catalog_service), so listing/lookups never touch the database. Both
require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from models import User
from routes.dependencies import get_current_user
from schemas.movie import ContentResponse, PaginatedContent
from services import catalog_service

router = APIRouter(prefix="/content", tags=["content"])


def filter_catalog(content_type=None, genre=None, search=None) -> list[dict]:
    """Apply optional content_type / genre / title-search filters.

    A None filter is a no-op, so passing nothing returns the whole catalog.
    Shared with the legacy /movies alias routes.
    """
    items = catalog_service.get_all_content()
    if content_type:
        # Case-insensitive so a value stored as 'Series'/'SERIES' still
        # matches the 'series' query param (defends against cause "b").
        ct = content_type.strip().lower()
        items = [c for c in items if (c["content_type"] or "").lower() == ct]
    if genre:
        g = genre.strip().lower()
        items = [c for c in items if c["genre"] and c["genre"].lower() == g]
    if search:
        s = search.strip().lower()
        items = [c for c in items if s in c["title"].lower()]
    return items


@router.get("", response_model=PaginatedContent)
def list_content(
    limit: int = Query(500, ge=1, le=1000, description="Page size."),
    skip: int = Query(0, ge=0, description="How many items to skip."),
    content_type: str | None = Query(
        None, pattern="^(movie|series)$",
        description="Filter by type: 'movie' or 'series'. Omit for everything.",
    ),
    genre: str | None = Query(None, description="Filter by genre (case-insensitive)."),
    search: str | None = Query(None, description="Filter by title substring."),
    _user: User = Depends(get_current_user),
):
    """Return content, optionally filtered by type/genre/search.

    With no filters this returns the full catalog (movies + series).
    """
    items = filter_catalog(content_type, genre, search)
    page = items[skip : skip + limit]
    return PaginatedContent(total=len(items), skip=skip, limit=limit, items=page)


@router.get("/{content_id}", response_model=ContentResponse)
def get_content(content_id: int, _user: User = Depends(get_current_user)):
    """Return one content item by id via binary search, or 404 if not found."""
    item = catalog_service.get_content_by_id(content_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content {content_id} not found.",
        )
    return item
