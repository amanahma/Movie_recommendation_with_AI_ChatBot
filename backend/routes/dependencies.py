"""
Shared FastAPI dependencies for the route layer.

`get_current_user` is the gate that protects every route except
register/login: it extracts the Bearer token, validates it, loads the
matching user from the database, and hands that user to the route. Any
failure becomes a 401.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db.database import get_db
from models import User
from services.auth import decode_access_token

# HTTPBearer pulls the token out of the `Authorization: Bearer <token>`
# header and powers the "Authorize" button in the Swagger docs.
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the request's Bearer token.

    Raises 401 if the token is missing/invalid/expired, or if it points at
    a user that no longer exists.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
