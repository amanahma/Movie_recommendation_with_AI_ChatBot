"""
Legacy /movies routes — kept as backward-compatible aliases of /content.

After the unified-content migration these simply delegate to the same
catalog/filter logic as /content, so old clients keep working. New code
should use /content.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from models import User
from routes.dependencies import get_current_user
from routes.content import filter_catalog
from schemas.movie import ContentResponse, PaginatedContent
from services import catalog_service

router = APIRouter(prefix="/movies", tags=["movies (deprecated)"])


@router.get("", response_model=PaginatedContent)
def list_movies(
    limit: int = Query(500, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    content_type: str | None = Query(None, pattern="^(movie|series)$"),
    genre: str | None = Query(None),
    search: str | None = Query(None),
    _user: User = Depends(get_current_user),
):
    """Deprecated alias of GET /content (returns the unified catalog)."""
    items = filter_catalog(content_type, genre, search)
    page = items[skip : skip + limit]
    return PaginatedContent(total=len(items), skip=skip, limit=limit, items=page)


@router.get("/{movie_id}", response_model=ContentResponse)
def get_movie(movie_id: int, _user: User = Depends(get_current_user)):
    """Deprecated alias of GET /content/{id}."""
    item = catalog_service.get_content_by_id(movie_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content {movie_id} not found.",
        )
    return item
