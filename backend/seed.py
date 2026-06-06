"""
Seed the database with sample data: 20 movies, 10 users, and some
interactions so the recommender has something to chew on later.

Run from the backend/ directory AFTER applying migrations:

    alembic upgrade head
    python seed.py

The script is idempotent-ish: it bails out early if data already exists,
so you can run it twice without creating duplicates.
"""

import random

from db.database import SessionLocal
from models import User, Movie, Interaction
from services.security import hash_password


# 20 movies: (title, genre, critic_rating, year, description)
MOVIES = [
    ("Inception",        "Sci-Fi",   8.8, 2010, "A thief who steals corporate secrets through dream-sharing."),
    ("Interstellar",     "Sci-Fi",   8.6, 2014, "Explorers travel through a wormhole to save humanity."),
    ("The Dark Knight",  "Action",   9.0, 2008, "Batman faces the Joker, a criminal mastermind."),
    ("Avengers",         "Action",   8.0, 2012, "Earth's mightiest heroes unite against Loki."),
    ("Joker",            "Drama",    8.4, 2019, "A failed comedian's descent into madness and crime."),
    ("Titanic",          "Romance",  7.9, 1997, "A romance blossoms aboard the ill-fated ocean liner."),
    ("The Matrix",       "Sci-Fi",   8.7, 1999, "A hacker learns reality is a simulation."),
    ("Parasite",         "Thriller", 8.5, 2019, "A poor family schemes their way into a wealthy household."),
    ("Dune",             "Sci-Fi",   8.0, 2021, "A noble heir fights for control of a desert planet."),
    ("Oppenheimer",      "Drama",    8.3, 2023, "The story of the father of the atomic bomb."),
    ("Gladiator",        "Action",   8.5, 2000, "A betrayed general fights as a gladiator for revenge."),
    ("The Notebook",     "Romance",  7.8, 2004, "A poor man and rich woman fall in love in the 1940s."),
    ("Se7en",            "Thriller", 8.6, 1995, "Detectives hunt a killer using the seven deadly sins."),
    ("La La Land",       "Romance",  8.0, 2016, "A jazz musician and an actress chase their dreams."),
    ("Whiplash",         "Drama",    8.5, 2014, "A young drummer is pushed to his limits by a brutal mentor."),
    ("Mad Max: Fury Road","Action",  8.1, 2015, "A woman rebels against a tyrant in a post-apocalyptic wasteland."),
    ("Arrival",          "Sci-Fi",   7.9, 2016, "A linguist works to communicate with alien visitors."),
    ("Get Out",          "Thriller", 7.7, 2017, "A man uncovers a disturbing secret on a visit to his girlfriend's family."),
    ("The Prestige",     "Drama",    8.5, 2006, "Two rival magicians battle to create the ultimate illusion."),
    ("Blade Runner 2049","Sci-Fi",   8.0, 2017, "A new blade runner unearths a long-buried secret."),
]

# 10 users: (username, email). All share a demo password.
USERS = [
    ("alice",   "alice@example.com"),
    ("bob",     "bob@example.com"),
    ("charlie", "charlie@example.com"),
    ("diana",   "diana@example.com"),
    ("eve",     "eve@example.com"),
    ("frank",   "frank@example.com"),
    ("grace",   "grace@example.com"),
    ("heidi",   "heidi@example.com"),
    ("ivan",    "ivan@example.com"),
    ("judy",    "judy@example.com"),
]

DEMO_PASSWORD = "password123"  # hashed before storage; for local testing only


def seed():
    """Insert sample movies, users, and random interactions.

    Wrapped in a single session/transaction so either all the data lands
    or none of it does (on error we roll back).
    """
    db = SessionLocal()
    try:
        # Guard: don't double-seed.
        if db.query(Movie).first() is not None:
            print("Database already has data -- skipping seed. "
                  "(Drop/recreate the DB to re-seed.)")
            return

        # --- Movies -----------------------------------------------------
        movies = [
            Movie(title=t, genre=g, rating=r, year=y, description=d)
            for (t, g, r, y, d) in MOVIES
        ]
        db.add_all(movies)
        print(f"Inserting {len(movies)} movies...")

        # --- Users (with hashed passwords) ------------------------------
        password_hash = hash_password(DEMO_PASSWORD)
        users = [
            User(username=u, email=e, password_hash=password_hash)
            for (u, e) in USERS
        ]
        db.add_all(users)
        print(f"Inserting {len(users)} users (password = {DEMO_PASSWORD!r})...")

        # Flush so the rows get their auto-generated ids before we
        # reference them in interactions below.
        db.flush()

        # --- Interactions ----------------------------------------------
        # Give each user a random handful of watched movies, some rated.
        # A fixed seed makes the sample data reproducible run-to-run.
        random.seed(42)
        interactions = []
        for user in users:
            watched_movies = random.sample(movies, k=random.randint(4, 8))
            for movie in watched_movies:
                interactions.append(
                    Interaction(
                        user_id=user.id,
                        movie_id=movie.id,
                        watched=True,
                        # ~70% of watched movies also get a 3-5 star rating.
                        rating=random.choice([3, 4, 4, 5, None]),
                    )
                )
        db.add_all(interactions)
        print(f"Inserting {len(interactions)} interactions...")

        db.commit()
        print("Seed complete.")
    except Exception:
        db.rollback()
        print("Seed failed -- rolled back.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
