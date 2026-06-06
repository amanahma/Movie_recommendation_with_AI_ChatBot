"""The legacy `movies` table.

Kept as a read-only safety net after the 0003 unified-content migration:
its rows were copied into `content`, and `interactions` now references
`content` instead. Nothing in the app reads from this model anymore, but we
keep the mapping so the table isn't orphaned from the ORM's metadata. Do not
add new code against it -- use Content.
"""

from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Movie(Base):
    """Legacy movie row (see module docstring). No interactions relationship:
    interactions were repointed to `content` in migration 0003."""

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<Movie id={self.id} title={self.title!r} ({self.year})>"
