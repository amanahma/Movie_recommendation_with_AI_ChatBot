"""
Authentication routes: register and login.

These are the only two routes that do NOT require a JWT -- everything else
depends on get_current_user. Register creates a user with a hashed
password; login verifies credentials and returns a signed token.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.database import get_db
from models import User
from schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from services.auth import create_access_token
from services.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new account.

    Rejects duplicate usernames or emails with 409 Conflict. The password
    is hashed with bcrypt before storage -- plaintext never touches the DB.
    """
    # Check for an existing username or email in one query.
    existing = db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    ).scalars().first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered.",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # populate id and created_at from the DB
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Verify username + password and return a JWT access token.

    We return the same 401 whether the username is unknown or the password
    is wrong, so an attacker can't tell which usernames exist.
    """
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalars().first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
