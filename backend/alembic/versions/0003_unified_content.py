"""unified content: movies + series in one table

Revision ID: 0003_unified_content
Revises: 0002_llm_cache
Create Date: 2026-06-06

Migrates from a movies-only schema to a unified `content` table that holds
both movies and series (Netflix-style). The old `movies` table is kept as a
safety net (NOT dropped).

IMPORTANT DEVIATION FROM THE BRIEF'S SQL: the brief's INSERT omitted `id`,
which would give migrated rows brand-new content ids that no longer match
`interactions.movie_id`. That would silently break every existing
interaction once the column is repointed. So we carry the original `id`
across and then advance the content id sequence past it. This is required
for the 220 existing movies' interactions to keep working.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_unified_content"
down_revision: Union[str, None] = "0002_llm_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- a) new unified content table ----------------------------------
    op.create_table(
        "content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=10), nullable=False),
        sa.Column("genre", sa.String(length=100), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("seasons", sa.Integer(), nullable=True),    # null for movies
        sa.Column("episodes", sa.Integer(), nullable=True),   # null for movies
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_type IN ('movie', 'series')",
            name="ck_content_content_type",
        ),
    )
    op.create_index("ix_content_content_type", "content", ["content_type"])
    op.create_index("ix_content_genre", "content", ["genre"])
    op.create_index("ix_content_rating", "content", ["rating"])

    # --- b) migrate existing movies (PRESERVING id) --------------------
    op.execute(
        """
        INSERT INTO content (id, title, content_type, genre, rating, description, year)
        SELECT id, title, 'movie', genre, rating, description, year
        FROM movies
        """
    )
    # Advance the content id sequence past the migrated rows so future
    # inserts (e.g. series) don't collide with the carried-over ids.
    op.execute(
        "SELECT setval(pg_get_serial_sequence('content', 'id'), "
        "COALESCE((SELECT MAX(id) FROM content), 1))"
    )

    # --- c) repoint interactions: movie_id -> content_id ---------------
    # Drop the old FK first (it references movie_id), then rename the
    # column + its index, then add the new FK to content.
    op.drop_constraint("interactions_movie_id_fkey", "interactions", type_="foreignkey")
    op.alter_column("interactions", "movie_id", new_column_name="content_id")
    op.execute("ALTER INDEX ix_interactions_movie_id RENAME TO ix_interactions_content_id")
    op.create_foreign_key(
        "interactions_content_id_fkey",
        "interactions",
        "content",
        ["content_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # d) similarity_cache and e) llm_cache: no changes needed.
    # f) movies table is intentionally kept as a safety net.


def downgrade() -> None:
    # Reverse the interactions repoint.
    op.drop_constraint("interactions_content_id_fkey", "interactions", type_="foreignkey")
    op.execute("ALTER INDEX ix_interactions_content_id RENAME TO ix_interactions_movie_id")
    op.alter_column("interactions", "content_id", new_column_name="movie_id")
    op.create_foreign_key(
        "interactions_movie_id_fkey",
        "interactions",
        "movies",
        ["movie_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("ix_content_rating", table_name="content")
    op.drop_index("ix_content_genre", table_name="content")
    op.drop_index("ix_content_content_type", table_name="content")
    op.drop_table("content")
