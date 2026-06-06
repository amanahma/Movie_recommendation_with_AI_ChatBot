"""Schemas for the conversational /chat endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Body for POST /chat. The user is taken from the JWT, not the body."""
    message: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    """The assistant's natural-language reply with suggestions."""
    reply: str
