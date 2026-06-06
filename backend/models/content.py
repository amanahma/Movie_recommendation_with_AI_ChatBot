"""The `content` table: unified catalog of movies AND series."""

from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, DateTime, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Content(Base):
    """A single piece of content -- either a movie or a series.

    One table for both (like Netflix internally). `content_type` discriminates
    the two, and `seasons`/`episodes` are populated only for series (NULL for
    movies). Indexes on content_type, genre, and rating support the common
    filter/sort queries.
    """

    __tablename__ = "content"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # 'movie' or 'series' (enforced by a CHECK constraint, see __table_args__).
    content_type: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Series-only fields; NULL for movies.
    seasons: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episodes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "content_type IN ('movie', 'series')", name="ck_content_content_type"
        ),
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"<Content id={self.id} type={self.content_type} "
            f"title={self.title!r} ({self.year})>"
        )
