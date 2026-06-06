"""
SERVICE 3: the in-memory content catalog with binary-search lookups.

On startup we load every content row (movies + series) from the database
into a list sorted by id. Because the list is sorted, we can find any item
by id with binary search in O(log n) instead of scanning the whole list. We
implement binary search by hand (no bisect) so the halving logic is visible.

Items are stored as plain dicts rather than ORM objects so they're safe to
read after the loading DB session has closed (no detached-instance issues).

Back-compat: the old movie-named helpers are kept as thin aliases so nothing
that still imports them breaks.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Content

# Module-level cache: a list of content dicts kept sorted by "id".
_catalog: list[dict] = []


def _content_to_dict(item: Content) -> dict:
    """Convert a Content ORM object into a plain, session-independent dict."""
    return {
        "id": item.id,
        "title": item.title,
        "content_type": item.content_type,
        "genre": item.genre,
        "rating": item.rating,
        "description": item.description,
        "year": item.year,
        "seasons": item.seasons,
        "episodes": item.episodes,
        "image_url": item.image_url,
    }


def build_catalog(db: Session) -> None:
    """Load all content from the DB into memory, sorted by id.

    Called once on server startup. We ask the database to return rows already
    ordered by id; sorting in SQL is cheap and guarantees the invariant
    binary search depends on.
    """
    global _catalog
    items = db.execute(select(Content).order_by(Content.id)).scalars().all()
    _catalog = [_content_to_dict(c) for c in items]


def _binary_search(items: list[dict], content_id: int) -> dict | None:
    """Find the content dict with `content_id` in a list sorted by id.

    Classic binary search: two pointers bound the still-unsearched slice;
    each step inspects the middle element and discards the half that can't
    contain the target. Returns None if the id isn't present.
    """
    low = 0
    high = len(items) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_id = items[mid]["id"]

        if mid_id == content_id:
            return items[mid]           # found it
        elif mid_id < content_id:
            low = mid + 1               # discard left half
        else:
            high = mid - 1              # discard right half

    return None  # not found


def get_content_by_id(content_id: int) -> dict | None:
    """Return a content dict by id via binary search, or None if not found."""
    return _binary_search(_catalog, content_id)


def get_all_content() -> list[dict]:
    """Return the full catalog (movies + series), sorted by id.

    Returns the shared list directly; callers that paginate/filter should
    work off a copy rather than mutate it.
    """
    return _catalog


def search_by_genre(genre: str) -> list[dict]:
    """Return all content in a genre (case-insensitive), sorted by id.

    Returns an empty list if nothing matches.
    """
    target = genre.strip().lower()
    return [c for c in _catalog if c["genre"] and c["genre"].lower() == target]


def find_in_results(results: list[dict], content_id: int) -> dict | None:
    """Binary-search for a content id within an already-sorted result list."""
    return _binary_search(results, content_id)


# --- Back-compat aliases (old movie-named API) -----------------------------
def get_movie_by_id(content_id: int) -> dict | None:
    """Deprecated alias for get_content_by_id."""
    return get_content_by_id(content_id)


def get_all_movies() -> list[dict]:
    """Deprecated alias for get_all_content."""
    return get_all_content()


def search_movies_by_genre(genre: str) -> list[dict]:
    """Deprecated alias for search_by_genre."""
    return search_by_genre(genre)
