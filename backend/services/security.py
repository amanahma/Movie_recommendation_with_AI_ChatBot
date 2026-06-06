"""
Password hashing helpers.

We use bcrypt directly (rather than passlib) to keep dependencies minimal
and avoid version-compatibility warnings. bcrypt automatically generates a
random salt per password and embeds it in the resulting hash string, so we
don't manage salts ourselves.
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt and return it as a string.

    bcrypt works on bytes, so we encode going in and decode coming out.
    The returned string contains the algorithm, cost factor, salt, and
    hash all together -- everything `verify_password` needs later.
    """
    password_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if `plain_password` matches the stored bcrypt hash.

    bcrypt re-derives the salt from the stored hash, so a plain
    constant-time comparison is handled internally by `checkpw`.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )
