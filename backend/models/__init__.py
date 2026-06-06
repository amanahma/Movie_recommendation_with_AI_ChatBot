"""
Models package.

Importing every model here serves two purposes:
  1. Callers can do `from models import User, Movie, ...` in one line.
  2. It guarantees all tables are registered on `Base.metadata` before
     Alembic inspects it -- otherwise migrations would silently miss any
     model that hadn't been imported elsewhere.
"""

from models.user import User
from models.movie import Movie
from models.content import Content
from models.interaction import Interaction
from models.similarity_cache import SimilarityCache
from models.llm_cache import LLMCache

__all__ = [
    "User",
    "Movie",
    "Content",
    "Interaction",
    "SimilarityCache",
    "LLMCache",
]
