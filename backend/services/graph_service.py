"""
SERVICE 1: the in-memory user-item graph.

We mirror the `interactions` table as a bipartite graph held in memory so
the recommender can do fast set operations without hitting the database on
every similarity calculation. The graph is rebuilt from the DB on server
startup (never hardcoded), and kept in sync when new interactions arrive.

  users_to_content[user_id]   -> set of content_ids that user watched
  content_to_users[content_id]-> set of user_ids who watched that content

Both directions are stored so lookups either way are O(1). Since the
0003 unified-content migration, the "items" are content (movies + series),
not just movies.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Interaction, Content


class BipartiteGraph:
    """Two adjacency lists linking users and the content they watched."""

    def __init__(self):
        """Start empty; populated by build_graph() or add_interaction()."""
        self.users_to_content: dict[int, set[int]] = {}
        self.content_to_users: dict[int, set[int]] = {}

    def add_interaction(self, user_id: int, content_id: int) -> None:
        """Add a single user->content edge, updating both adjacency lists.

        setdefault creates the empty set the first time we see a given user
        or content item, so callers never have to pre-register nodes.
        """
        self.users_to_content.setdefault(user_id, set()).add(content_id)
        self.content_to_users.setdefault(content_id, set()).add(user_id)


# Module-level singleton. The whole app shares one graph instance, which
# startup populates and the interactions route keeps current.
_graph = BipartiteGraph()


def build_graph(db: Session) -> BipartiteGraph:
    """Rebuild the graph from every watched interaction in the database.

    Called on server startup. Reads interactions joined with content so only
    edges pointing at existing content are included, and only rows where
    `watched` is True (a merely-rated row isn't a "watched" edge). Replaces
    the module singleton's contents so existing references stay valid.
    """
    global _graph
    fresh = BipartiteGraph()

    rows = db.execute(
        select(Interaction.user_id, Interaction.content_id)
        .join(Content, Content.id == Interaction.content_id)
        .where(Interaction.watched.is_(True))
    ).all()

    for user_id, content_id in rows:
        fresh.add_interaction(user_id, content_id)

    _graph = fresh
    return _graph


def get_graph() -> BipartiteGraph:
    """Return the current shared graph instance."""
    return _graph


def add_interaction_to_graph(user_id: int, content_id: int) -> None:
    """Incrementally add ONE new edge to the live in-memory graph.

    Called from POST /interactions whenever a user marks content watched, so
    recommendations reflect the new watch immediately -- no server restart,
    and no full rebuild. O(1).
    """
    _graph.add_interaction(user_id, content_id)


def get_user_neighbors(user_id: int) -> set[int]:
    """Return the set of content_ids a user watched (their graph neighbors).

    In a bipartite user-content graph, a user node's neighbors are exactly
    the content items they're connected to. Returns an empty set for an
    unknown user (handles the "no watch history" edge case cleanly).
    """
    return _graph.users_to_content.get(user_id, set())


def get_content_watchers(content_id: int) -> set[int]:
    """Return the set of user_ids who watched a given content item.

    Returns an empty set if no one has watched it (or it's unknown).
    """
    return _graph.content_to_users.get(content_id, set())
