"""Request/response schemas for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    """Body for POST /auth/register."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Body for POST /auth/login (login by username + password)."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT returned on successful login."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public view of a user (never includes the password hash)."""
    model_config = ConfigDict(from_attributes=True)  # allow building from ORM objects

    id: int
    username: str
    email: EmailStr
    created_at: datetime
