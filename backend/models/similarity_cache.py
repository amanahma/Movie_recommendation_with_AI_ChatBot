"""The `similarity_cache` table: precomputed user-to-user similarity scores."""

from datetime import datetime

from sqlalchemy import Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SimilarityCache(Base):
    """A cached similarity score between two users.

    Computing cosine similarity across all user pairs on every request is
    expensive. Instead we compute it periodically and store the results
    here, so serving recommendations becomes a fast lookup.

    The primary key is the *pair* (user_id, similar_user_id) -- one cached
    score per ordered pair of users. `computed_at` lets us know how stale a
    score is and refresh it later.
    """

    __tablename__ = "similarity_cache"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    similar_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"<SimilarityCache user_id={self.user_id} "
            f"similar_user_id={self.similar_user_id} score={self.score:.3f}>"
        )
