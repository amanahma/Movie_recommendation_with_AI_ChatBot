"""
A Netflix/Amazon-style recommendation system built from scratch.

The goal here is *clarity*, not performance. Each of the five components
lives in its own class or function so you can study them in isolation and
see how they connect:

    1. UserItemGraph      -> who watched what (a graph, stored as adjacency lists)
    2. find_similar_users -> collaborative filtering via manual cosine similarity
    3. rank_recommendations -> score unseen movies by similar-user popularity
    4. generate_description -> a fake "LLM" that fills in a template
    5. MovieCatalog       -> fast lookup of movie details via manual binary search

No ML libraries, no pandas, no external APIs. Everything is plain Python.
"""

from math import sqrt


# ---------------------------------------------------------------------------
# COMPONENT 1: THE USER-ITEM GRAPH
# ---------------------------------------------------------------------------
class UserItemGraph:
    """A bipartite graph connecting users to the movies they watched.

    "Bipartite" just means there are two kinds of nodes (users and movies)
    and every edge goes from a user to a movie -- never user-to-user or
    movie-to-movie.

    We store the graph as two adjacency lists (here, dictionaries of sets):

        users_to_movies[user]  -> set of movie_ids that user watched
        movies_to_users[movie] -> set of users who watched that movie

    Keeping both directions is redundant data, but it makes lookups in
    *either* direction O(1), which the later components rely on. This is a
    classic space-for-speed trade-off.
    """

    def __init__(self):
        """Create an empty graph with no users and no movies."""
        self.users_to_movies = {}   # user_name -> set of movie_ids
        self.movies_to_users = {}   # movie_id  -> set of user_names

    def add_user(self, user):
        """Register a user node. Safe to call more than once.

        A brand-new user simply starts with an empty set of watched movies.
        We guard with `not in` so re-adding an existing user never wipes
        their history.
        """
        if user not in self.users_to_movies:
            self.users_to_movies[user] = set()

    def add_movie(self, movie_id):
        """Register a movie node. Safe to call more than once.

        Note this only tracks the movie *inside the graph* (its edges).
        The human-readable details (title, genre) live in MovieCatalog,
        keyed by this same movie_id. Separating "the graph" from "the
        metadata" mirrors how real systems split a graph database from a
        content store.
        """
        if movie_id not in self.movies_to_users:
            self.movies_to_users[movie_id] = set()

    def add_interaction(self, user, movie_id):
        """Record that `user` watched `movie_id` (i.e. add a graph edge).

        We auto-create the user and movie nodes if they don't exist yet,
        so the caller doesn't have to remember to add them first. Then we
        update *both* adjacency lists to keep them in sync.
        """
        self.add_user(user)
        self.add_movie(movie_id)
        self.users_to_movies[user].add(movie_id)
        self.movies_to_users[movie_id].add(user)

    def get_watched(self, user):
        """Return the set of movie_ids a user watched.

        Returns an empty set for an unknown user (the "new user with no
        history" edge case) so callers can iterate without special-casing.
        """
        return self.users_to_movies.get(user, set())

    def all_users(self):
        """Return a list of every user currently in the graph."""
        return list(self.users_to_movies.keys())


# ---------------------------------------------------------------------------
# COMPONENT 2: FIND SIMILAR USERS (collaborative filtering)
# ---------------------------------------------------------------------------
def cosine_similarity(set_a, set_b):
    """Compute cosine similarity between two users' watch histories.

    Each user is conceptually a vector over the space of all movies:
    a 1 if they watched a movie, 0 if they didn't. Cosine similarity is
    the cosine of the angle between those two vectors:

        cosine = dot_product(A, B) / (||A|| * ||B||)

    Because our vectors are just 0s and 1s, the math simplifies beautifully:

        - dot_product(A, B) = number of movies BOTH watched (the overlap)
        - ||A|| = sqrt(number of movies A watched)
        - ||B|| = sqrt(number of movies B watched)

    The result ranges from 0.0 (no movies in common) to 1.0 (identical
    taste). We implement it by hand -- no sklearn -- so the formula is
    fully visible.
    """
    # Overlap = size of the intersection = the dot product for 0/1 vectors.
    overlap = len(set_a & set_b)

    # Edge case: if either user watched nothing, the vector has length 0
    # and the angle is undefined. We define similarity as 0 to avoid a
    # divide-by-zero.
    if overlap == 0 or len(set_a) == 0 or len(set_b) == 0:
        return 0.0

    magnitude = sqrt(len(set_a)) * sqrt(len(set_b))
    return overlap / magnitude


def find_similar_users(graph, target_user, top_n=3):
    """Return the `top_n` users whose taste is most similar to target_user.

    We compare the target against every other user using cosine_similarity,
    skip anyone with zero similarity, and return the highest scorers as a
    list of (user, score) tuples sorted from most to least similar.

    Edge cases handled:
      - target_user unknown or has no history -> returns [] (nothing to
        compare against, so collaborative filtering can't help yet).
      - empty graph -> returns [].
    """
    target_movies = graph.get_watched(target_user)
    if not target_movies:
        # New user with no history: we have no signal to find neighbors.
        return []

    scores = []
    for other_user in graph.all_users():
        if other_user == target_user:
            continue  # don't compare a user with themselves
        similarity = cosine_similarity(target_movies, graph.get_watched(other_user))
        if similarity > 0:
            scores.append((other_user, similarity))

    # Sort by similarity, highest first, and keep only the top N.
    scores.sort(key=lambda pair: pair[1], reverse=True)
    return scores[:top_n]


# ---------------------------------------------------------------------------
# COMPONENT 3: RANK RECOMMENDATIONS
# ---------------------------------------------------------------------------
def rank_recommendations(graph, target_user, similar_users, top_n=5):
    """Recommend movies the target hasn't seen, ranked by neighbor popularity.

    The idea: if people with similar taste enjoyed a movie you haven't
    watched, it's probably worth recommending. For each candidate movie we
    compute a score = the number of similar users who watched it. (We weight
    every similar user equally here; a fancier system would weight by each
    neighbor's similarity score.)

    Steps:
      1. Collect the set of movies the target already watched (to exclude).
      2. Walk through each similar user's history, tallying votes for movies
         the target hasn't seen.
      3. Sort by vote count and return the top N as (movie_id, score) tuples.

    Edge cases handled:
      - empty `similar_users` (e.g. brand-new user) -> returns [].
      - similar users only watched things the target already saw -> returns [].
    """
    already_watched = graph.get_watched(target_user)
    movie_votes = {}  # movie_id -> how many similar users watched it

    for user, _similarity in similar_users:
        for movie_id in graph.get_watched(user):
            if movie_id in already_watched:
                continue  # don't recommend something they've already seen
            movie_votes[movie_id] = movie_votes.get(movie_id, 0) + 1

    # Sort candidates by vote count, highest first.
    ranked = sorted(movie_votes.items(), key=lambda pair: pair[1], reverse=True)
    return ranked[:top_n]


# ---------------------------------------------------------------------------
# COMPONENT 4: GENERATE DESCRIPTIONS (simulated LLM output)
# ---------------------------------------------------------------------------
def generate_description(movie_title, score):
    """Produce a human-friendly recommendation blurb from a template.

    A real product might send the movie + context to an LLM and get back
    natural-sounding copy. Here we *simulate* that step with a fixed
    template, so the surrounding pipeline is identical to the real thing --
    only this function's internals would change if you swapped in a real
    model later.

    `score` is the number of similar users who watched the movie; we fold
    it into the sentence to make the reasoning transparent.
    """
    viewers = "viewer" if score == 1 else "viewers"
    return (
        f'"{movie_title}" - Recommended because users similar to you '
        f'watched this ({score} similar {viewers}).'
    )


# ---------------------------------------------------------------------------
# COMPONENT 5: FAST RETRIEVAL (binary search over a sorted catalog)
# ---------------------------------------------------------------------------
class MovieCatalog:
    """Stores movie details and retrieves them by id using binary search.

    The graph only knows movie *ids*. To show a title to the user we need
    the metadata, and we want that lookup to be fast even with millions of
    movies. We keep the movies in a list sorted by movie_id, which lets us
    use binary search: each comparison halves the search space, giving
    O(log n) lookups instead of O(n) for a linear scan.

    (A Python dict would also give fast lookups, but the assignment is to
    understand binary search -- so we do it explicitly here.)
    """

    def __init__(self):
        """Start with an empty catalog (a list we keep sorted by id)."""
        self.movies = []  # list of dicts: {"id": int, "title": str, "genre": str}

    def add_movie(self, movie_id, title, genre):
        """Insert a movie and keep the list sorted by movie_id.

        We re-sort after every insert for simplicity. With many inserts
        you'd instead insert at the correct position, but sorting keeps
        this readable and the search code below correct regardless.
        """
        self.movies.append({"id": movie_id, "title": title, "genre": genre})
        self.movies.sort(key=lambda m: m["id"])

    def get_movie(self, movie_id):
        """Return the movie dict for `movie_id`, or None if not found.

        This is binary search implemented by hand (no bisect library):
        we keep two pointers, `low` and `high`, marking the slice of the
        list still worth searching. Each step looks at the middle element
        and discards the half that can't contain our target.

        Returns None for an id that isn't in the catalog (the "movie not
        found" edge case).
        """
        low = 0
        high = len(self.movies) - 1

        while low <= high:
            mid = (low + high) // 2
            mid_id = self.movies[mid]["id"]

            if mid_id == movie_id:
                return self.movies[mid]      # found it
            elif mid_id < movie_id:
                low = mid + 1                # target is in the right half
            else:
                high = mid - 1               # target is in the left half

        return None  # searched everything, not present

    def get_title(self, movie_id):
        """Convenience helper: return a movie's title, or a fallback string."""
        movie = self.get_movie(movie_id)
        return movie["title"] if movie else f"<unknown movie #{movie_id}>"


# ---------------------------------------------------------------------------
# DEMO: all five components working together
# ---------------------------------------------------------------------------
def main():
    """Wire the five components together on sample data and print each step.

    The flow mirrors a real recommendation request:
        build graph -> find neighbors -> rank movies ->
        look up titles (binary search) -> generate blurbs.
    """
    print("=" * 70)
    print("  RECOMMENDATION SYSTEM DEMO")
    print("=" * 70)

    # --- Set up the movie catalog (Component 5) --------------------------
    # We give each movie a numeric id; the catalog stays sorted by it.
    movie_data = [
        (1, "Inception", "Sci-Fi"),
        (2, "Interstellar", "Sci-Fi"),
        (3, "The Dark Knight", "Action"),
        (4, "Avengers", "Action"),
        (5, "Joker", "Drama"),
        (6, "Titanic", "Romance"),
        (7, "Matrix", "Sci-Fi"),
        (8, "Parasite", "Thriller"),
        (9, "Dune", "Sci-Fi"),
        (10, "Oppenheimer", "Drama"),
    ]
    catalog = MovieCatalog()
    for movie_id, title, genre in movie_data:
        catalog.add_movie(movie_id, title, genre)

    # --- Build the user-item graph (Component 1) -------------------------
    # Each user's list reflects a rough "taste": sci-fi fans, action fans, etc.
    graph = UserItemGraph()
    watch_history = {
        "Alice":   [1, 2, 7, 9],      # sci-fi lover
        "Bob":     [1, 2, 9, 10],     # sci-fi + drama
        "Charlie": [3, 4, 5],         # action + drama
        "Diana":   [3, 4, 6],         # action + romance
        "Eve":     [1, 7, 8, 10],     # sci-fi + thriller + drama
    }
    for user, movie_ids in watch_history.items():
        for movie_id in movie_ids:
            graph.add_interaction(user, movie_id)

    print("\n[STEP 1] User-Item Graph (who watched what)")
    print("-" * 70)
    for user in graph.all_users():
        titles = [catalog.get_title(mid) for mid in sorted(graph.get_watched(user))]
        print(f"  {user:<8}: {', '.join(titles)}")

    # --- Pick a target user and find similar users (Component 2) ---------
    target = "Alice"
    print(f"\n[STEP 2] Find users similar to '{target}' (cosine similarity)")
    print("-" * 70)
    neighbors = find_similar_users(graph, target, top_n=3)
    if not neighbors:
        print(f"  No similar users found for {target}.")
    for user, score in neighbors:
        print(f"  {user:<8}: similarity = {score:.3f}")

    # --- Rank recommendations (Component 3) ------------------------------
    print(f"\n[STEP 3] Rank movie recommendations for '{target}'")
    print("-" * 70)
    recommendations = rank_recommendations(graph, target, neighbors, top_n=5)
    if not recommendations:
        print("  No new recommendations (target has seen everything similar users watched).")
    for movie_id, votes in recommendations:
        print(f"  movie #{movie_id} ({catalog.get_title(movie_id)}): {votes} similar viewer(s)")

    # --- Generate descriptions + fast retrieval (Components 4 & 5) -------
    print(f"\n[STEP 4 & 5] Final recommendations for '{target}'")
    print("  (titles fetched via binary search, blurbs via template)")
    print("-" * 70)
    for movie_id, votes in recommendations:
        # Component 5: binary search to fetch the title for this id.
        title = catalog.get_title(movie_id)
        # Component 4: simulate an LLM-generated explanation.
        print("  " + generate_description(title, votes))

    # --- Edge case demonstrations ----------------------------------------
    print("\n[EDGE CASES]")
    print("-" * 70)

    # (a) Brand-new user with no watch history.
    graph.add_user("Frank")  # Frank exists but watched nothing
    frank_neighbors = find_similar_users(graph, "Frank", top_n=3)
    print(f"  New user 'Frank' (no history) -> similar users: {frank_neighbors}")
    print(f"  New user 'Frank' -> recommendations: "
          f"{rank_recommendations(graph, 'Frank', frank_neighbors)}")

    # (b) Movie id that doesn't exist in the catalog.
    print(f"  Lookup of non-existent movie #999 -> {catalog.get_movie(999)}")

    # (c) Searching for similar users in a completely empty graph.
    empty_graph = UserItemGraph()
    print(f"  Empty graph -> similar users for 'Nobody': "
          f"{find_similar_users(empty_graph, 'Nobody')}")

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
