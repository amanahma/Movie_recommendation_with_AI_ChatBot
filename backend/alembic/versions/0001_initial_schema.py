"""initial schema: users, movies, interactions, similarity_cache

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-05

This is a hand-written initial migration (using Alembic's `op` API, not raw
SQL) that creates all four tables and their indexes. After standing up an
empty PostgreSQL database, run `alembic upgrade head` to apply it.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and indexes."""

    # --- users ----------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Unique + indexed lookups for login.
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- movies ---------------------------------------------------------
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("genre", sa.String(length=100), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
    )
    # Required index: recommending/filtering by genre is common.
    op.create_index("ix_movies_genre", "movies", ["genre"])

    # --- interactions ---------------------------------------------------
    op.create_table(
        "interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("watched", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
    )
    # Required indexes: the recommender queries by user and by movie constantly.
    op.create_index("ix_interactions_user_id", "interactions", ["user_id"])
    op.create_index("ix_interactions_movie_id", "interactions", ["movie_id"])

    # --- similarity_cache ----------------------------------------------
    op.create_table(
        "similarity_cache",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("similar_user_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["similar_user_id"], ["users.id"], ondelete="CASCADE"),
        # Composite primary key: one cached score per ordered user pair.
        sa.PrimaryKeyConstraint("user_id", "similar_user_id"),
    )


def downgrade() -> None:
    """Drop everything in reverse order (respecting foreign keys)."""
    op.drop_table("similarity_cache")
    op.drop_index("ix_interactions_movie_id", table_name="interactions")
    op.drop_index("ix_interactions_user_id", table_name="interactions")
    op.drop_table("interactions")
    op.drop_index("ix_movies_genre", table_name="movies")
    op.drop_table("movies")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
