"""The `llm_cache` table: stores LLM responses keyed by a hash of their input."""

from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class LLMCache(Base):
    """One cached LLM response.

    LLM calls cost money and add latency, and the same input (same user +
    movie + context) always deserves the same answer. So before calling the
    API we hash the full input, look it up here, and reuse the stored
    response on a hit. Only on a miss do we actually call the model and
    store the result.

    The primary key is the input hash (a SHA-256 hex string), so identical
    inputs collapse to one row.
    """

    __tablename__ = "llm_cache"

    hash_of_input: Mapped[str] = mapped_column(String(64), primary_key=True)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """Developer-friendly representation (truncates the response)."""
        preview = (self.response[:40] + "...") if len(self.response) > 40 else self.response
        return f"<LLMCache hash={self.hash_of_input[:8]}... response={preview!r}>"
