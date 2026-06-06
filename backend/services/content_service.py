"""
Content-based ("mood") recommendations.

Where the collaborative filter asks "who is similar to you?", this asks
"what are you in the mood for *right now*?" -- inferred from your most
recent watches. The idea: recent behavior reflects current interest, so if
your last few watches were romances, surface more (highly-rated) romances.

Since the 0003 unified-content migration this queries the `content` table,
so a "mood" pick can be a movie OR a series.

This runs ALONGSIDE collaborative filtering; the route merges the two.
All DB access uses SQLAlchemy.
"""

from collections import Counter

from sqlalchemy import select, nullslast
from sqlalchemy.orm import Session

from models import Content, Interaction


class MoodBasedRecommender:
    """Recommends content by the genre/mood of a user's recent watches."""

    # Genre -> human-friendly mood label shown in the UI
    # ("You seem to be in a <mood> mood").
    mood_map = {
        "Romance": "romantic",
        "Action": "thrilling",
        "Horror": "scary",
        "Comedy": "fun",
        "Drama": "emotional",
        "Sci-Fi": "mind-bending",
        "Thriller": "suspenseful",
        "Animation": "lighthearted",
        "Documentary": "informative",
        "Crime": "gripping",
    }

    # How many recent interactions define "current mood".
    RECENT_WINDOW = 3

    def mood_for_genre(self, genre: str) -> str:
        """Map a genre to its mood label, with a sensible default."""
        return self.mood_map.get(genre, "curious")

    @staticmethod
    def _content_to_dict(item: Content) -> dict:
        """Plain dict matching the shape used elsewhere (catalog/route)."""
        return {
            "id": item.id,
            "title": item.title,
            "content_type": item.content_type,
            "genre": item.genre,
            "rating": item.rating,
            "description": item.description,
            "year": item.year,
            "seasons": item.seasons,
            "episodes": item.episodes,
            "image_url": item.image_url,
        }

    def get_genre_recommendations(
        self,
        db: Session,
        genre: str,
        exclude_content_ids,
        limit: int = 10,
        content_type: str | None = None,
    ) -> list[dict]:
        """Top-rated content in `genre`, excluding already-watched ids.

        Optional `content_type` ('movie'/'series') restricts the results to
        one kind; None returns both. Returns content dicts sorted by rating
        (highest first; NULL ratings last).

        NOTE: the brief listed this as (genre, exclude, limit); we also take
        `db` because the query needs a session.
        """
        stmt = select(Content).where(Content.genre == genre)
        if content_type is not None:
            stmt = stmt.where(Content.content_type == content_type)
        if exclude_content_ids:
            stmt = stmt.where(Content.id.notin_(list(exclude_content_ids)))
        stmt = stmt.order_by(nullslast(Content.rating.desc())).limit(limit)

        items = db.execute(stmt).scalars().all()
        return [self._content_to_dict(c) for c in items]

    def get_mood_recommendations(self, user_id: int, db: Session, limit: int = 10) -> dict:
        """Infer the user's current mood and recommend content for it.

        Steps:
          1. Pull the user's watched content_ids, newest first.
          2. Take the most recent RECENT_WINDOW distinct items.
          3. Pick the most frequent genre among them = current mood.
          4. Return top-rated unwatched content in that genre (movies + series).

        Returns {"genre", "mood", "items"}. If the user has no watch history,
        returns all-empty so the caller can skip mood filtering.
        """
        watched = db.execute(
            select(Interaction.content_id)
            .where(Interaction.user_id == user_id, Interaction.watched.is_(True))
            .order_by(Interaction.timestamp.desc())
        ).scalars().all()

        if not watched:
            # No history -> no mood signal. Caller falls back to collaborative.
            return {"genre": None, "mood": None, "items": []}

        # Most recent distinct items (preserve recency order).
        seen, recent = set(), []
        for content_id in watched:
            if content_id not in seen:
                seen.add(content_id)
                recent.append(content_id)
        last_n = recent[: self.RECENT_WINDOW]

        # Genres of those recent items.
        genre_rows = db.execute(
            select(Content.id, Content.genre).where(Content.id.in_(last_n))
        ).all()
        genre_by_id = {cid: g for cid, g in genre_rows}
        recent_genres = [
            genre_by_id[cid] for cid in last_n if genre_by_id.get(cid) is not None
        ]
        if not recent_genres:
            return {"genre": None, "mood": None, "items": []}

        # Most frequent genre = current mood. Counter.most_common breaks ties
        # by first-seen order, which here favors the most recent genre.
        top_genre = Counter(recent_genres).most_common(1)[0][0]
        mood = self.mood_for_genre(top_genre)

        # Exclude everything already watched (not just the recent window).
        items = self.get_genre_recommendations(db, top_genre, set(watched), limit)
        return {"genre": top_genre, "mood": mood, "items": items}
