"""
Interactions route: record that the authenticated user watched content.

Besides writing the row to the database, we incrementally update the
in-memory graph and invalidate the user's similarity cache so
recommendations reflect the new watch immediately.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from models import User, Interaction
from routes.dependencies import get_current_user
from schemas.interaction import InteractionCreate, InteractionResponse
from services import catalog_service, graph_service, recommendation_service

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
def create_interaction(
    payload: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record an interaction for the current user.

    Steps:
      1. Validate the content exists (binary search in the catalog) -> 404.
      2. Insert the interaction row (user comes from the JWT, not the body).
      3. If watched, add the edge to the in-memory graph AND invalidate this
         user's similarity cache, so the next /recommendations call is fresh.
    """
    if catalog_service.get_content_by_id(payload.content_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content {payload.content_id} not found.",
        )

    interaction = Interaction(
        user_id=current_user.id,
        content_id=payload.content_id,
        watched=payload.watched,
        rating=payload.rating,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    # Only watched edges affect the graph and similarity.
    if payload.watched:
        graph_service.add_interaction_to_graph(current_user.id, payload.content_id)
        recommendation_service.invalidate_user_cache(db, current_user.id)

    return interaction
