from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import logging

from app.auth.jwt_handler import get_current_user
from app.db.base import get_db
from app.services import db_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_prs(
    repo: str = Query(..., description="Full repo name: owner/repo"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prs = await db_service.get_prs(db, repo=repo, topic=topic, limit=limit, offset=offset)
    return {"prs": prs, "total": len(prs), "repo": repo}


@router.get("/topics")
async def list_topics(
    repo: str = Query(..., description="Full repo name: owner/repo"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    topics = await db_service.get_topics(db, repo=repo)
    return {"topics": topics, "repo": repo}


@router.get("/stats")
async def get_stats(
    repo: str = Query(..., description="Full repo name: owner/repo"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await db_service.get_stats(db, repo=repo)
    return stats


@router.get("/{pr_number}")
async def get_pr(
    pr_number: int,
    repo: str = Query(..., description="Full repo name: owner/repo"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pr = await db_service.get_pr(db, repo=repo, number=pr_number)
    if not pr:
        raise HTTPException(status_code=404, detail=f"PR #{pr_number} not found")

    # Enrich with related PR details
    similar_numbers = pr.get("similarPRs", [])
    related_prs = await db_service.get_related_prs(db, repo=repo, pr_numbers=similar_numbers)

    # Determine which PR is "primary" (highest score among the group)
    current_score = pr.get("score", 0)
    all_scores = [(pr.get("number"), current_score)] + [
        (r.get("number"), r.get("score", 0)) for r in related_prs
    ]
    primary_number = max(all_scores, key=lambda x: x[1])[0] if all_scores else pr.get("number")

    for r in related_prs:
        r["isPrimary"] = r.get("number") == primary_number
    pr["isPrimary"] = pr.get("number") == primary_number

    return {"pr": pr, "relatedPRs": related_prs, "primaryPR": primary_number}
