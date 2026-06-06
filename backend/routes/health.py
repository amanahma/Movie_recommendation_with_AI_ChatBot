"""A trivial health-check route to confirm the API and DB are reachable."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db

# A router groups related endpoints; we include it into the app in main.py.
router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Report API liveness and whether the database responds.

    Runs a cheap `SELECT 1` against PostgreSQL. If the DB is down the
    dependency/query raises and FastAPI returns a 500, which is the signal
    a load balancer or you want during setup.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
