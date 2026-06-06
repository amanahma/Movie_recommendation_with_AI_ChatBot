"""Schemas for content and recommendation responses.

After the 0003 unified-content migration these carry movies AND series, so
the response includes content_type plus the series-only seasons/episodes.
The historical names (MovieResponse / PaginatedMovies) are kept and aliased
to avoid churn in older imports.
"""

from pydantic import BaseModel


class ContentResponse(BaseModel):
    """A single content item (movie or series) as returned by the API."""
    id: int
    title: str
    content_type: str | None = None      # 'movie' | 'series'
    genre: str | None = None
    rating: float | None = None
    description: str | None = None
    year: int | None = None
    seasons: int | None = None           # series only
    episodes: int | None = None          # series only
    image_url: str | None = None


class PaginatedContent(BaseModel):
    """A page of content plus pagination metadata."""
    total: int      # total items matching the (optional) filters
    skip: int       # how many were skipped
    limit: int      # page size requested
    items: list[ContentResponse]


# Back-compat aliases (old movie-named schemas point at the content ones).
MovieResponse = ContentResponse
PaginatedMovies = PaginatedContent


class RecommendationItem(BaseModel):
    """One recommended item: full details plus a human-readable reason."""
    movie: ContentResponse   # kept key name "movie" for frontend compatibility
    score: float             # final merged score (collaborative and/or mood)
    reason: str
    mood_tag: str | None = None  # set when this item matches the current mood


class RecommendationsResponse(BaseModel):
    """The full recommendations payload: detected mood + ranked items."""
    current_mood: str | None = None
    recommendations: list[RecommendationItem]
