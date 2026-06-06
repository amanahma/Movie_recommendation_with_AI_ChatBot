"""
FastAPI application entry point.

Run the dev server from the `backend/` directory with:

    uvicorn main:app --reload

Then visit http://localhost:8000/docs for the auto-generated API docs.

On startup we rebuild two in-memory structures from the database:
  - the user-item graph (graph_service), and
  - the sorted movie catalog (catalog_service).
Both are derived from DB data, never hardcoded.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import SessionLocal
from routes import (
    health_router,
    auth_router,
    content_router,
    movies_router,
    interactions_router,
    recommendations_router,
    search_router,
    chat_router,
)
from services import graph_service, catalog_service

# Importing the models package registers every table on Base.metadata.
import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build in-memory state from the DB on startup; clean up on shutdown.

    We open a short-lived session just for the warm-up queries, then close
    it -- request handlers get their own sessions via get_db.
    """
    db = SessionLocal()
    try:
        graph_service.build_graph(db)      # user-item graph from interactions
        catalog_service.build_catalog(db)  # sorted movie catalog
    finally:
        db.close()
    yield
    # (no shutdown work needed for now)


app = FastAPI(
    title="Movie Recommendation API",
    version="0.2.0",
    description="Phase 2: graph + recommendations + catalog, with JWT auth.",
    lifespan=lifespan,
)

# CORS: allow the local Vite dev server (exact origin) and any Vercel
# deployment. Note: CORSMiddleware matches allow_origins by EXACT string, so
# a wildcard like "https://*.vercel.app" would never match -- subdomain
# wildcards must go through allow_origin_regex instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes.
app.include_router(health_router)
app.include_router(auth_router)
# JWT-protected routes.
app.include_router(content_router)
app.include_router(movies_router)
app.include_router(interactions_router)
app.include_router(recommendations_router)
app.include_router(search_router)
app.include_router(chat_router)


@app.get("/")
def root():
    """Root endpoint -- a friendly pointer to the docs."""
    return {"message": "Movie Recommendation API. See /docs for endpoints."}
