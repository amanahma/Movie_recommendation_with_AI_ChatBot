"""
Database engine + session setup.

This module owns the SQLAlchemy `engine` (the actual connection pool to
PostgreSQL) and a `SessionLocal` factory for creating short-lived sessions.
FastAPI routes get a session via the `get_db` dependency, which guarantees
each request opens and closes its own session cleanly.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import settings

# The engine manages a pool of connections to PostgreSQL. Created once and
# reused for the whole app lifetime. `pool_pre_ping` checks a connection is
# still alive before handing it out, avoiding "stale connection" errors.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# A factory that produces new Session objects bound to our engine.
# autoflush/autocommit are off so we control exactly when data is written.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    """Yield a database session for one request, then always close it.

    Used as a FastAPI dependency (`db: Session = Depends(get_db)`). The
    try/finally ensures the connection returns to the pool even if the
    request handler raises.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
