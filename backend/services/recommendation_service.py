"""
SERVICE 2: collaborative-filtering recommendations.

Pipeline:
  find_similar_users  -> who has taste like this user (cosine similarity)
  rank_recommendations -> what unseen movies those neighbors liked

Similarity scores are cached in the `similarity_cache` table and only
recomputed when the cache is missing or older than 24 hours, so repeated
requests are cheap.

All set math runs against the in-memory graph from graph_service; all
persistence uses SQLAlchemy (no raw SQL).
"""

from datetime import datetime, timedelta, timezone
from math import sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import SimilarityCache
from services import graph_service

# How long a cached similarity row stays valid before we recompute.
CACHE_TTL = timedelta(hours=24)


def _cosine_similarity(set_a: set[int], set_b: set[int]) -> float:
    """Cosine similarity between two users' watch-history sets.

    For 0/1 "watched" vectors this reduces to:

        overlap / (sqrt(|A|) * sqrt(|B|))

    where overlap is the number of movies both watched. Implemented by
    hand -- no sklearn. Returns 0.0 when there's no overlap or either set
    is empty (avoids divide-by-zero).
    """
    overlap = len(set_a & set_b)
    if overlap == 0 or not set_a or not set_b:
        return 0.0
    return overlap / (sqrt(len(set_a)) * sqrt(len(set_b)))


def _read_fresh_cache(db: Session, user_id: int) -> list[tuple[int, float]] | None:
    """Return cached (similar_user_id, score) pairs if still fresh, else None.

    "Fresh" means the newest cached row for this user is within CACHE_TTL.
    Returning None signals the caller to recompute.
    """
    rows = db.execute(
        select(SimilarityCache).where(SimilarityCache.user_id == user_id)
    ).scalars().all()

    if not rows:
        return None  # never computed

    newest = max(row.computed_at for row in rows)
    # computed_at is timezone-aware (stored with timezone=True).
    if datetime.now(timezone.utc) - newest > CACHE_TTL:
        return None  # stale

    pairs = [(row.similar_user_id, row.score) for row in rows]
    pairs.sort(key=lambda pair: pair[1], reverse=True)
    return pairs


def _write_cache(db: Session, user_id: int, pairs: list[tuple[int, float]]) -> None:
    """Replace this user's cached similarity rows with freshly computed ones.

    We delete the old rows first so a user who has *fewer* neighbors now
    doesn't keep stale leftovers. computed_at is set explicitly so the
    freshness check works without a round-trip refresh.
    """
    db.query(SimilarityCache).filter(SimilarityCache.user_id == user_id).delete()
    now = datetime.now(timezone.utc)
    for similar_user_id, score in pairs:
        db.add(
            SimilarityCache(
                user_id=user_id,
                similar_user_id=similar_user_id,
                score=score,
                computed_at=now,
            )
        )
    db.commit()


def invalidate_user_cache(db: Session, user_id: int) -> int:
    """FIX #3: delete this user's cached similarity rows.

    Called from POST /interactions after a new watch. Removing the user's
    rows means the next find_similar_users() sees no fresh cache and
    recomputes from the (just-updated) graph instead of serving stale
    results from within the 24h TTL window.

    Scope is deliberately narrow per the requirement: we delete ONLY rows
    where user_id matches -- never the whole table. Returns the number of
    rows deleted.

    (Note: this clears the user's view of *their* neighbors. Other users who
    happen to have this user cached as a neighbor keep their rows until their
    own TTL expires or they record an interaction -- an intentional trade-off
    to avoid a table-wide purge on every watch.)
    """
    deleted = (
        db.query(SimilarityCache)
        .filter(SimilarityCache.user_id == user_id)
        .delete()
    )
    db.commit()
    return deleted


def find_similar_users(db: Session, user_id: int, top_n: int = 5) -> list[tuple[int, float]]:
    """Return up to `top_n` users most similar to `user_id`.

    Result is a list of (similar_user_id, score) sorted high-to-low. Uses
    the 24h cache when fresh; otherwise recomputes via cosine similarity
    and refreshes the cache.

    Edge cases:
      - user has no watch history -> returns [] (nothing to compare).
      - no other user shares any movie -> returns [].
    """
    target_content = graph_service.get_user_neighbors(user_id)
    if not target_content:
        return []  # new user / no history: collaborative filtering can't help

    # Serve from cache when fresh.
    cached = _read_fresh_cache(db, user_id)
    if cached is not None:
        return cached[:top_n]

    # Candidate neighbors = users who share at least one content item with the
    # target. Gathering them via content_to_users avoids scanning every user.
    candidates: set[int] = set()
    for content_id in target_content:
        candidates |= graph_service.get_content_watchers(content_id)
    candidates.discard(user_id)  # never similar to oneself

    scored: list[tuple[int, float]] = []
    for other_id in candidates:
        score = _cosine_similarity(target_content, graph_service.get_user_neighbors(other_id))
        if score > 0:
            scored.append((other_id, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)

    # Cache the full computed set (not just top_n) for reuse.
    if scored:
        _write_cache(db, user_id, scored)

    return scored[:top_n]


def rank_recommendations(db: Session, user_id: int, top_n: int = 5) -> list[dict]:
    """Recommend unseen movies, scored by similarity-weighted neighbor votes.

    For each movie a similar user watched (and the target hasn't), we add
    that neighbor's similarity score to the movie's total. Weighting by
    similarity means a very-similar neighbor's pick counts more than a
    barely-similar one's.

    Returns a list of dicts sorted by score, each:
        {
          "content_id": int,
          "score": float,          # summed similarity weight
          "num_watchers": int,     # how many similar users watched it
        }
    `num_watchers` is what the API turns into the human reason string.

    Edge cases: no similar users, or neighbors only watched content the
    target already saw -> returns [].
    """
    similar_users = find_similar_users(db, user_id)
    if not similar_users:
        return []

    already_watched = graph_service.get_user_neighbors(user_id)

    scores: dict[int, float] = {}        # content_id -> summed similarity
    watcher_counts: dict[int, int] = {}  # content_id -> # of similar watchers

    for similar_user_id, similarity in similar_users:
        for content_id in graph_service.get_user_neighbors(similar_user_id):
            if content_id in already_watched:
                continue  # don't recommend something already seen
            scores[content_id] = scores.get(content_id, 0.0) + similarity
            watcher_counts[content_id] = watcher_counts.get(content_id, 0) + 1

    ranked = [
        {"content_id": cid, "score": score, "num_watchers": watcher_counts[cid]}
        for cid, score in scores.items()
    ]
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_n]
