"""
Chat route: a conversational recommendation interface.

The authenticated user sends a free-form message ("suggest me something
like Inception") and gets back movie suggestions grounded in the catalog
and their watch history. The heavy lifting (and failure handling) lives in
llm_service.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models import User
from routes.dependencies import get_current_user
from schemas.chat import ChatRequest, ChatResponse
from services import llm_service

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reply to a conversational recommendation request.

    The user id comes from the JWT, so the assistant always reasons about
    the caller's own watch history. Never raises on LLM failure -- the
    service returns a safe fallback message instead.
    """
    reply = llm_service.chat_with_recommendations(db, current_user.id, payload.message)
    return ChatResponse(reply=reply)
