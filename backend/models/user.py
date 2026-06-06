"""The `users` table: people who use the app."""

from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class User(Base):
    """A registered user.

    We store only a bcrypt *hash* of the password, never the plaintext.
    `username` and `email` are unique so two accounts can't collide, and
    both are indexed because we'll look users up by them at login.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Convenience link to this user's interactions (not a DB column).
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Developer-friendly representation (shown in logs/debugger)."""
        return f"<User id={self.id} username={self.username!r}>"
