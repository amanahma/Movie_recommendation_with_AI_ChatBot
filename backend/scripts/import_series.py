"""
Import web series from TMDB into the unified `content` table.

Mirrors scripts/import_movies.py but hits TMDB's TV endpoints and writes
rows with content_type='series'. For each series we make an extra detail
call (GET /tv/{id}) to fetch seasons/episodes counts; if that call fails we
store NULL for both and continue (never crash on one series).

Run AFTER applying the 0003 migration, from the backend/ directory:

    python scripts/import_series.py

Requires TMDB_API_KEY in backend/.env. Safe to re-run (dedupes by title+year
against everything already in `content`).
"""

import sys
import time
from pathlib import Path

import requests
from sqlalchemy import select, func

# Make the backend package importable when run as `python scripts/...`.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import settings          # noqa: E402
from db.database import SessionLocal  # noqa: E402
from models import Content           # noqa: E402

TMDB_BASE = "https://api.themoviedb.org/3"
SLEEP_SECONDS = 0.25  # rate-limit pause between every API call

# (label, endpoint, pages, extra query params)
CATEGORIES = [
    ("popular", "/tv/popular", 5, {"language": "en-US"}),
    ("Hindi", "/discover/tv", 5,
     {"with_original_language": "hi", "sort_by": "popularity.desc"}),
    ("top-rated", "/tv/top_rated", 3, {"language": "en-US"}),
]


def tmdb_get(path, params=None):
    """GET a TMDB endpoint and return parsed JSON, or None on any failure.

    Always sleeps SLEEP_SECONDS afterwards. Never raises.
    """
    query = dict(params or {})
    query["api_key"] = settings.TMDB_API_KEY
    try:
        resp = requests.get(f"{TMDB_BASE}{path}", params=query, timeout=10)
        if resp.status_code != 200:
            print(f"  ! TMDB {path} returned HTTP {resp.status_code}")
            return None
        return resp.json()
    except requests.RequestException as exc:
        print(f"  ! TMDB request to {path} failed: {exc}")
        return None
    finally:
        time.sleep(SLEEP_SECONDS)


def load_tv_genre_map():
    """Return {genre_id: name} from TMDB's TV genre list, or {} on failure."""
    data = tmdb_get("/genre/tv/list", {"language": "en-US"})
    if not data:
        return {}
    return {g["id"]: g["name"] for g in data.get("genres", [])}


def fetch_category(path, pages, extra_params):
    """Fetch `pages` worth of raw series dicts; a failed page is skipped."""
    results = []
    for page in range(1, pages + 1):
        params = dict(extra_params)
        params["page"] = page
        data = tmdb_get(path, params)
        if not data:
            continue
        results.extend(data.get("results", []))
    return results


def fetch_series_detail(tv_id):
    """Return (seasons, episodes) for a series, or (None, None) on failure.

    The constraint: a failed detail fetch must NOT crash the import. Since
    tmdb_get already returns None on any error, this just degrades to NULLs.
    """
    data = tmdb_get(f"/tv/{tv_id}")
    if not data:
        return (None, None)
    return (data.get("number_of_seasons"), data.get("number_of_episodes"))


def map_series(raw, genre_map):
    """Map one TMDB TV record to the content schema, or None if unusable.

    TMDB uses `name`/`first_air_date` for TV (not `title`/`release_date`).
    Skips records missing a title, overview, parsable year, or known genre.
    """
    try:
        title = (raw.get("name") or "").strip()
        overview = (raw.get("overview") or "").strip()
        first_air = raw.get("first_air_date") or ""
        year_str = first_air[:4]
        genre_ids = raw.get("genre_ids") or []

        if not title or not overview or len(year_str) != 4 or not genre_ids:
            return None

        year = int(year_str)  # raises on non-numeric -> caught below
        genre = genre_map.get(genre_ids[0])
        if not genre:
            return None

        vote = raw.get("vote_average")
        rating = round(float(vote), 1) if vote is not None else None

        return {
            "tmdb_id": raw.get("id"),
            "title": title,
            "genre": genre,
            "rating": rating,
            "description": overview,
            "year": year,
        }
    except (ValueError, TypeError):
        return None


def main():
    """Fetch series, dedupe, enrich with season/episode counts, insert."""
    if not settings.TMDB_API_KEY:
        print("TMDB_API_KEY is not set in backend/.env. Aborting.")
        return

    db = SessionLocal()
    try:
        genre_map = load_tv_genre_map()
        if not genre_map:
            print("Could not load the TMDB TV genre list. Aborting.")
            return

        # Dedupe against everything already in content (movies + any series).
        existing = db.execute(select(Content.title, Content.year)).all()
        seen = {(t.lower(), y) for t, y in existing}

        counts = {label: 0 for label, *_ in CATEGORIES}
        to_insert = []

        for label, path, pages, extra in CATEGORIES:
            print(f"Fetching {label} series ({pages} pages)...")
            for raw in fetch_category(path, pages, extra):
                mapped = map_series(raw, genre_map)
                if mapped is None:
                    continue

                key = (mapped["title"].lower(), mapped["year"])
                if key in seen:
                    continue
                seen.add(key)

                # Extra detail call for seasons/episodes (NULLs on failure).
                seasons, episodes = fetch_series_detail(mapped["tmdb_id"])

                to_insert.append(
                    Content(
                        title=mapped["title"],
                        content_type="series",
                        genre=mapped["genre"],
                        rating=mapped["rating"],
                        description=mapped["description"],
                        year=mapped["year"],
                        seasons=seasons,
                        episodes=episodes,
                        image_url=None,  # frontend fetches posters from TMDB
                    )
                )
                counts[label] += 1

        if to_insert:
            db.bulk_save_objects(to_insert)
            db.commit()

        total = db.execute(select(func.count()).select_from(Content)).scalar()

        print(
            f"Imported {counts['popular']} popular, "
            f"{counts['Hindi']} Hindi, "
            f"{counts['top-rated']} top-rated series"
        )
        print(f"Total content in database: {total} items")
    finally:
        db.close()


if __name__ == "__main__":
    main()
