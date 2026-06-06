"""
Recommendations route.

Combines two signals into one ranked list:
  - COLLABORATIVE filtering (recommendation_service): "users like you watched
    these" -- scored by similarity-weighted neighbor votes.
  - CONTENT/MOOD filtering (content_service): "you've been watching romances,
    here are more romances" -- inferred from the user's recent watches.

Since the unified-content migration, both signals operate over content
(movies AND series), so recommendations naturally mix the two types.

Merge rules:
  * Collaborative scores are kept as-is.
  * Mood picks get a base score from their rating plus a +0.3 mood boost.
  * If an item shows up in both, we keep the higher score.
  * Every item carries a mood_tag when its genre matches the current mood.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from models import User
from routes.dependencies import get_current_user
from schemas.movie import RecommendationItem, RecommendationsResponse
from services import catalog_service, recommendation_service, llm_service
from services.content_service import MoodBasedRecommender

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Extra score added to a mood pick (it matches the user's current mood).
MOOD_BOOST = 0.3

_recommender = MoodBasedRecommender()


def _build_reason(num_watchers: int) -> str:
    """Turn a watcher count into a friendly explanation string."""
    if num_watchers == 1:
        return "Because 1 user with similar taste watched this"
    return f"Because {num_watchers} users with similar taste watched this"


@router.get("/{user_id}", response_model=RecommendationsResponse)
def get_recommendations(
    user_id: int,
    use_llm: bool = Query(
        True,
        description="If true, generate a personalized LLM reason for "
        "collaborative picks (cached; falls back to a template on failure).",
    ),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return merged collaborative + mood recommendations (movies + series).

    Response shape:
        {
          "current_mood": "romantic" | null,
          "recommendations": [
            {"movie": {...content...}, "score": 1.43, "mood_tag": "romantic",
             "reason": "..."}
          ]
        }
    """
    if db.get(User, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    # --- 1. Collaborative filtering --------------------------------------
    collaborative = recommendation_service.rank_recommendations(db, user_id)

    # --- 2. Mood-based filtering -----------------------------------------
    mood = _recommender.get_mood_recommendations(user_id, db)
    mood_genre = mood["genre"]
    current_mood = mood["mood"]

    # --- 3. Merge by content id, keeping the higher score on overlap -----
    merged: dict[int, dict] = {}

    for entry in collaborative:
        item = catalog_service.get_content_by_id(entry["content_id"])
        if item is None:
            continue  # in graph but not catalog -> skip
        merged[item["id"]] = {
            "item": item,
            "score": entry["score"],          # collaborative score as-is
            "num_watchers": entry["num_watchers"],
        }

    for item in mood["items"]:
        base = (item["rating"] or 0) / 10.0   # normalize rating to ~0..1
        mood_score = base + MOOD_BOOST        # matches current mood -> boost
        existing = merged.get(item["id"])
        if existing is not None:
            existing["score"] = max(existing["score"], mood_score)
        else:
            merged[item["id"]] = {
                "item": item,
                "score": mood_score,
                "num_watchers": None,         # mood-only pick
            }

    # --- 4. Build response items (mood_tag + reason), sorted by score ----
    results: list[RecommendationItem] = []
    for data in merged.values():
        item = data["item"]

        mood_tag = (
            current_mood if mood_genre and item["genre"] == mood_genre else None
        )

        if data["num_watchers"] is not None:
            if use_llm:
                reason = llm_service.generate_recommendation_reason(
                    db, user_id, item["id"], data["num_watchers"]
                )
            else:
                reason = _build_reason(data["num_watchers"])
        else:
            # Mood-only pick -> concise template reason (no LLM cost).
            kind = item.get("content_type") or "title"
            reason = (
                f"Because you're in a {current_mood} mood — "
                f"a top-rated {item['genre']} {kind}."
            )

        results.append(
            RecommendationItem(
                movie=item,
                score=round(data["score"], 2),
                reason=reason,
                mood_tag=mood_tag,
            )
        )

    results.sort(key=lambda it: it.score, reverse=True)
    return RecommendationsResponse(current_mood=current_mood, recommendations=results)
