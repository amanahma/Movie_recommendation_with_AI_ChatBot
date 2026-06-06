"""Routes package: HTTP endpoints, grouped into APIRouters."""

from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.content import router as content_router
from routes.movies import router as movies_router
from routes.interactions import router as interactions_router
from routes.recommendations import router as recommendations_router
from routes.search import router as search_router
from routes.chat import router as chat_router

__all__ = [
    "health_router",
    "auth_router",
    "content_router",
    "movies_router",
    "interactions_router",
    "recommendations_router",
    "search_router",
    "chat_router",
]
