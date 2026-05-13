from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from app.auth.jwt_handler import get_current_user
from app.db.base import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services import db_service
from app.services.rocketride_service import RocketrideService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat_about_pr(
    request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a chat message and get an AI response with PR context from Qdrant."""
    try:
        # Fetch PR context from MariaDB (optional — enriches the question)
        pr_context = None
        if request.pr_number:
            pr = await db_service.get_pr(db, repo=request.repo, number=request.pr_number)
            if pr:
                pr_context = {
                    "number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "topics": pr.get("topics", []),
                    "score": pr.get("score", 0),
                    "recommendation": pr.get("recommendation", "keep"),
                }

        history = [{"role": m.role, "content": m.content} for m in request.history]

        svc = RocketrideService()
        response_text = await svc.chat_about_pr(
            message=request.message,
            history=history,
            pr_context=pr_context,
        )

        return ChatResponse(message=response_text, pr_number=request.pr_number or 0)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chat service error: {str(e)}")
