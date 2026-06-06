"""Schemas for the interactions endpoint."""

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class InteractionCreate(BaseModel):
    """Body for POST /interactions. The user is taken from the JWT, not here.

    The field is `content_id`, but we also accept the legacy `movie_id` key
    (via an alias) so an un-migrated client doesn't break mid-rollout.
    """
    model_config = ConfigDict(populate_by_name=True)

    content_id: int = Field(validation_alias=AliasChoices("content_id", "movie_id"))
    watched: bool = True
    rating: float | None = Field(default=None, ge=0, le=5)  # optional 0-5 stars


class InteractionResponse(BaseModel):
    """An interaction row as returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    content_id: int
    watched: bool
    rating: float | None
    timestamp: datetime
