"""
LLM-powered text generation, backed by Groq.

Groq serves an OpenAI-compatible API, so we use the official `openai` SDK
pointed at Groq's base URL (configured in settings). Three public
functions cover the product needs:

  generate_recommendation_reason -> why this movie suits this user
  generate_movie_summary         -> a description for a movie that lacks one
  chat_with_recommendations      -> conversational suggestions

Design rules enforced here:
  * Every API call is wrapped in try/except -- an LLM failure NEVER crashes
    the request. On failure we return a template-based fallback instead.
  * Responses are cached in the `llm_cache` table, keyed by a SHA-256 hash
    of the full input, so identical inputs never hit the API twice.
  * max_tokens is capped (200) to keep responses short and costs low.

NOTE ON MODEL: the brief asked for "gpt-4o-mini", but that is an OpenAI
model not hosted by Groq. Since the project uses a Groq key, we use the
Groq model from settings (default: llama-3.3-70b-versatile). Only the model
name differs -- the SDK, caching, and fallbacks are unchanged.
"""

import hashlib
import json

from openai import OpenAI
from sqlalchemy.orm import Session

from config import settings
from models import LLMCache, Movie
from services import graph_service, catalog_service

# Hard cap on output length -- keeps every call cheap and responses tight.
MAX_TOKENS = 200

# Lazily-created shared client (see _get_client). Created on first use so
# importing this module never requires a valid key.
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return a shared OpenAI SDK client configured for Groq's endpoint."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
        )
    return _client


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------
def _hash_input(*parts) -> str:
    """Build a stable SHA-256 hex key from the call's inputs.

    We JSON-encode the parts with sorted keys so the same logical input
    always hashes to the same string regardless of dict ordering.
    """
    raw = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(db: Session, key: str) -> str | None:
    """Return a previously cached response for this input hash, or None."""
    row = db.get(LLMCache, key)
    return row.response if row is not None else None


def _cache_set(db: Session, key: str, response: str) -> None:
    """Store a response under its input hash (ignores duplicate races)."""
    if db.get(LLMCache, key) is not None:
        return  # already cached (e.g. concurrent request beat us to it)
    db.add(LLMCache(hash_of_input=key, response=response))
    db.commit()


def _call_llm(db: Session, cache_key: str, system_prompt: str, user_prompt: str) -> str | None:
    """Core LLM call: check cache, else call Groq, cache, and return text.

    Returns the generated string on success (from cache or fresh), or None
    if the API call failed -- the caller is responsible for substituting a
    template fallback when None comes back. We never let an exception
    escape, so a flaky LLM can't take down the API.
    """
    # 1. Cache hit? Return immediately, no API call.
    cached = _cache_get(db, cache_key)
    if cached is not None:
        return cached

    # 2. Cache miss -> call the model, guarded by try/except.
    try:
        response = _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            return None  # treat empty completion as a failure -> fallback
        _cache_set(db, cache_key, text)
        return text
    except Exception:
        # Network error, bad key, rate limit, etc. Signal fallback.
        return None


# ---------------------------------------------------------------------------
# Context helpers (turn ids into human-readable titles for the prompt)
# ---------------------------------------------------------------------------
def _watch_history_titles(user_id: int, limit: int = 10) -> list[str]:
    """Return titles of movies the user watched, for use as LLM context."""
    movie_ids = sorted(graph_service.get_user_neighbors(user_id))[:limit]
    titles = []
    for mid in movie_ids:
        movie = catalog_service.get_movie_by_id(mid)
        if movie is not None:
            titles.append(movie["title"])
    return titles


# ---------------------------------------------------------------------------
# 1. Recommendation reason
# ---------------------------------------------------------------------------
def _fallback_reason(num_similar_watchers: int) -> str:
    """Template reason used when the LLM is unavailable."""
    if num_similar_watchers == 1:
        return "Because 1 user with similar taste watched this"
    return f"Because {num_similar_watchers} users with similar taste watched this"


def generate_recommendation_reason(
    db: Session,
    user_id: int,
    movie_id: int,
    similar_users,
) -> str:
    """Generate a 2-sentence personalized reason this movie suits the user.

    `similar_users` may be an int (count of similar viewers who watched the
    movie) or a list of such viewers; we accept either and derive the count.

    Inputs sent to the model: the user's watch history, the target movie's
    details, and how many similar viewers watched it. On any failure we
    return the template reason instead (never raises).
    """
    # Accept either a count or a collection of similar users.
    num_watchers = similar_users if isinstance(similar_users, int) else len(similar_users)

    movie = catalog_service.get_movie_by_id(movie_id)
    if movie is None:
        # Can't describe a movie we don't have; fall straight back.
        return _fallback_reason(num_watchers)

    history = _watch_history_titles(user_id)
    history_str = ", ".join(history) if history else "no movies yet"

    cache_key = _hash_input("reason", user_id, movie_id, num_watchers, sorted(history))

    system_prompt = (
        "You write short, warm movie recommendation blurbs. "
        "Always reply in exactly two sentences. Be specific and never invent "
        "facts about the user beyond what you are told."
    )
    user_prompt = (
        f"User has watched: {history_str}.\n"
        f"Recommend this movie: \"{movie['title']}\" "
        f"(genre: {movie['genre']}, year: {movie['year']}).\n"
        f"{num_watchers} viewers with similar taste also watched it.\n"
        "Explain in two sentences why this movie fits this user's taste."
    )

    result = _call_llm(db, cache_key, system_prompt, user_prompt)
    return result if result is not None else _fallback_reason(num_watchers)


# ---------------------------------------------------------------------------
# 2. Movie summary (with write-back to movies.description)
# ---------------------------------------------------------------------------
def generate_movie_summary(
    db: Session,
    movie_id: int,
    movie_title: str,
    genre: str,
    year: int | None,
) -> str:
    """Generate a movie description and cache it into movies.description.

    Returns the existing description if the movie already has one (no API
    call). Otherwise generates a 2-sentence summary, writes it back to the
    movies row AND refreshes the in-memory catalog, and returns it.

    NOTE: the brief's signature was (movie_title, genre, year). We also take
    `db` and `movie_id` because writing the result back to the correct
    movies row is impossible without them.

    On LLM failure, returns a minimal template description (and does not
    persist it, so a real summary can be generated later).
    """
    movie = db.get(Movie, movie_id)
    if movie is not None and movie.description:
        return movie.description  # already have one -> no LLM call

    cache_key = _hash_input("summary", movie_title, genre, year)

    system_prompt = (
        "You write concise, spoiler-free movie descriptions in exactly two "
        "sentences. Do not invent specific plot details you are unsure of."
    )
    user_prompt = (
        f"Write a short description for the movie \"{movie_title}\" "
        f"(genre: {genre}, year: {year})."
    )

    result = _call_llm(db, cache_key, system_prompt, user_prompt)
    if result is None:
        # Fallback: don't persist, so we can try again for a real one later.
        return f"A {genre} film from {year}." if year else f"A {genre} film."

    # Persist the generated description back to the DB and the live catalog.
    if movie is not None:
        movie.description = result
        db.commit()
        cached = catalog_service.get_movie_by_id(movie_id)
        if cached is not None:
            cached["description"] = result
    return result


# ---------------------------------------------------------------------------
# 3. Conversational recommendations
# ---------------------------------------------------------------------------
def _fallback_chat_reply() -> str:
    """Reply used when the chat LLM call fails."""
    return (
        "Sorry, I can't generate suggestions right now. "
        "Try the /recommendations endpoint for picks based on your watch history."
    )


def chat_with_recommendations(db: Session, user_id: int, user_message: str) -> str:
    """Answer a free-form request like 'suggest me something like Inception'.

    The model is given the user's watch history and the catalog of
    available movie titles (so it suggests real titles, not hallucinated
    ones) plus the user's message. Returns a natural-language reply with
    suggestions and reasons. On failure, returns a safe fallback message.
    """
    history = _watch_history_titles(user_id)
    history_str = ", ".join(history) if history else "no movies yet"

    # Provide the real catalog so suggestions stay grounded in what exists.
    catalog_titles = [m["title"] for m in catalog_service.get_all_movies()]
    catalog_str = ", ".join(catalog_titles) if catalog_titles else "none available"

    cache_key = _hash_input("chat", user_id, sorted(history), user_message.strip().lower())

    system_prompt = (
        "You are a friendly movie recommendation assistant. Suggest 1-3 "
        "movies ONLY from the provided catalog, and give a one-line reason "
        "for each. Keep the whole reply under 200 tokens."
    )
    user_prompt = (
        f"Available movies: {catalog_str}.\n"
        f"This user has watched: {history_str}.\n"
        f"User says: \"{user_message}\"\n"
        "Recommend movies from the catalog with brief reasons."
    )

    result = _call_llm(db, cache_key, system_prompt, user_prompt)
    return result if result is not None else _fallback_chat_reply()
