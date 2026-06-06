"""
Search route: find movies by genre.

Reads from the in-memory catalog (catalog_service.search_movies_by_genre),
which filters the sorted catalog. Requires authentication.
"""

from fastapi import APIRouter, Depends, Query

from models import User
from routes.dependencies import get_current_user
from schemas.movie import MovieResponse
from services import catalog_service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[MovieResponse])
def search(
    genre: str = Query(..., min_length=1, description="Genre to filter by, e.g. 'action'."),
    _user: User = Depends(get_current_user),
):
    """Return all movies in the given genre (case-insensitive).

    Returns an empty list if nothing matches -- an empty result is a valid
    answer, not an error.
    """
    return catalog_service.search_movies_by_genre(genre)
