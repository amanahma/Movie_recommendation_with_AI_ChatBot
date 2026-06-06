"""The `interactions` table: the edges connecting users to content."""

from datetime import datetime

from sqlalchemy import Boolean, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Interaction(Base):
    """One user's engagement with one piece of content (watched and/or rated).

    This is the core signal the recommender learns from -- it's the database
    version of the user-item graph's edges. We index `user_id` and
    `content_id` because the recommender constantly asks "what did this user
    watch?" and "who watched this content?", and indexes turn those from
    full-table scans into fast lookups.
    """

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Repointed from movies -> content in migration 0003.
    content_id: Mapped[int] = mapped_column(
        ForeignKey("content.id", ondelete="CASCADE"), index=True, nullable=False
    )
    watched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # The user's personal rating (e.g. 1-5). Nullable: they may have watched
    # without rating, or rated without finishing.
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Convenience links back to the related rows.
    user: Mapped["User"] = relationship(back_populates="interactions")
    content: Mapped["Content"] = relationship(back_populates="interactions")

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"<Interaction user_id={self.user_id} content_id={self.content_id} "
            f"watched={self.watched} rating={self.rating}>"
        )
