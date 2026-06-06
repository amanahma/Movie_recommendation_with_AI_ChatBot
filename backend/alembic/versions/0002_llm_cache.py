"""add llm_cache table

Revision ID: 0002_llm_cache
Revises: 0001_initial
Create Date: 2026-06-05

Adds the llm_cache table used to memoize LLM responses by a hash of their
input, so we never pay for (or wait on) the same generation twice.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_llm_cache"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the llm_cache table."""
    op.create_table(
        "llm_cache",
        # SHA-256 hex digest of the input -> 64 chars. Primary key so
        # identical inputs collapse to a single cached row.
        sa.Column("hash_of_input", sa.String(length=64), primary_key=True),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop the llm_cache table."""
    op.drop_table("llm_cache")
