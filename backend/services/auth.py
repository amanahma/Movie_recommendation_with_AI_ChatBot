"""
JWT token creation and decoding.

A JWT (JSON Web Token) is a signed string the client sends on every
request to prove who it is. We sign with our SECRET_KEY using HS256, so
only our server can produce or validate a token -- if anyone tampers with
the payload, the signature check fails.

The token carries a `sub` (subject) claim holding the user's id, and an
`exp` (expiry) claim so old tokens stop working automatically.
"""

from datetime import datetime, timedelta, timezone

import jwt

from config import settings

# Signing algorithm. HS256 is symmetric: same secret signs and verifies.
ALGORITHM = "HS256"
# How long a freshly issued token stays valid.
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(user_id: int) -> str:
    """Create a signed JWT whose subject is the given user id.

    `sub` must be a string per the JWT spec, so we stringify the id. We
    also stamp an expiry so the token can't be replayed forever.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Validate a token's signature/expiry and return the user id.

    Raises jwt.InvalidTokenError (or a subclass like ExpiredSignatureError)
    if the token is forged, expired, or malformed. The caller turns that
    into an HTTP 401.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    return int(payload["sub"])
