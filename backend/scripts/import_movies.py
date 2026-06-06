"""
Populate the movies table with a real catalog from TMDB.

Fetches three categories (popular "Hollywood", Hindi-language "Bollywood",
and top-rated), maps each TMDB record onto our schema, skips junk and
duplicates, and bulk-inserts the rest.

Run from the backend/ directory:

    python scripts/import_movies.py

Requires TMDB_API_KEY in backend/.env. It is safe to re-run: anything
already in the database (matched by title + year) is skipped as a duplicate.
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
from models import Movie             # noqa: E402

TMDB_BASE = "https://api.themoviedb.org/3"
SLEEP_SECONDS = 0.25  # rate-limit pause between every API call

# (label, endpoint, pages, extra query params)
CATEGORIES = [
    ("Hollywood", "/movie/popular", 5, {"language": "en-US"}),
    ("Bollywood", "/discover/movie", 5,
     {"with_original_language": "hi", "sort_by": "popularity.desc"}),
    ("Top Rated", "/movie/top_rated", 3, {"language": "en-US"}),
]


def tmdb_get(path, params=None):
    """GET a TMDB endpoint and return parsed JSON, or None on any failure.

    Always sleeps SLEEP_SECONDS afterwards to respect rate limits. Never
    raises -- network errors, non-200 responses, and bad JSON all return
    None so the caller can skip and continue.
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


def load_genre_map():
    """Return {genre_id: genre_name} from TMDB, or {} if it can't be loaded."""
    data = tmdb_get("/genre/movie/list", {"language": "en-US"})
    if not data:
        return {}
    return {g["id"]: g["name"] for g in data.get("genres", [])}


def fetch_category(path, pages, extra_params):
    """Fetch `pages` worth of raw movie dicts from one endpoint.

    A failed page is skipped (not fatal) so one bad request doesn't abort
    the whole category.
    """
    results = []
    for page in range(1, pages + 1):
        params = dict(extra_params)
        params["page"] = page
        data = tmdb_get(path, params)
        if not data:
            continue
        results.extend(data.get("results", []))
    return results


def map_movie(raw, genre_map):
    """Map one TMDB record to our schema, or return None if it's unusable.

    Skips records missing a title, overview, parsable year, or a known
    genre. Wrapped so a single malformed record can never crash the import.
    """
    try:
        title = (raw.get("title") or "").strip()
        overview = (raw.get("overview") or "").strip()
        release_date = raw.get("release_date") or ""
        year_str = release_date[:4]
        genre_ids = raw.get("genre_ids") or []

        # Required-field checks (skip movies with empty/missing data).
        if not title or not overview or len(year_str) != 4:
            return None
        if not genre_ids:
            return None

        year = int(year_str)  # raises on non-numeric -> caught below
        genre = genre_map.get(genre_ids[0])
        if not genre:
            return None

        vote = raw.get("vote_average")
        rating = round(float(vote), 1) if vote is not None else None

        return {
            "title": title,
            "genre": genre,
            "rating": rating,
            "description": overview,
            "year": year,
        }
    except (ValueError, TypeError):
        return None  # never crash on a single bad movie


def main():
    """Fetch, dedupe, bulk-insert, and print a summary."""
    if not settings.TMDB_API_KEY:
        print("TMDB_API_KEY is not set in backend/.env. Aborting.")
        return

    db = SessionLocal()
    try:
        genre_map = load_genre_map()
        if not genre_map:
            print("Could not load the TMDB genre list. Aborting.")
            return

        # Seed the dedupe set with movies already in the DB (title + year),
        # lowercased so casing differences still match.
        existing = db.execute(select(Movie.title, Movie.year)).all()
        seen = {(t.lower(), y) for t, y in existing}

        counts = {label: 0 for label, *_ in CATEGORIES}
        duplicates = 0
        to_insert = []

        for label, path, pages, extra in CATEGORIES:
            print(f"Fetching {label} ({pages} pages)...")
            for raw in fetch_category(path, pages, extra):
                mapped = map_movie(raw, genre_map)
                if mapped is None:
                    continue

                key = (mapped["title"].lower(), mapped["year"])
                if key in seen:
                    duplicates += 1
                    continue

                seen.add(key)              # also dedupes across categories
                to_insert.append(Movie(**mapped))
                counts[label] += 1

        # Single bulk insert for everything collected.
        if to_insert:
            db.bulk_save_objects(to_insert)
            db.commit()

        total = db.execute(select(func.count()).select_from(Movie)).scalar()

        print(
            f"Imported {counts['Hollywood']} Hollywood, "
            f"{counts['Bollywood']} Bollywood, "
            f"{counts['Top Rated']} Top Rated movies"
        )
        print(f"Skipped {duplicates} duplicates")
        print(f"Total in database: {total} movies")
    finally:
        db.close()


if __name__ == "__main__":
    main()
