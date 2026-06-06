"""
The declarative base every model inherits from.

It lives in its own tiny module to avoid circular imports: models import
`Base` from here, and Alembic also imports it to discover table metadata --
neither needs to import the engine/session machinery in `database.py`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root class for all ORM models.

    SQLAlchemy collects every subclass's table definition into
    `Base.metadata`, which is what Alembic inspects to generate and run
    migrations.
    """
    pass
