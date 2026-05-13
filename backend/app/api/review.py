from datetime import datetime, timezone
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.auth.jwt_handler import get_current_user, get_github_token
from app.db.base import get_db
from app.models.schemas import (
    ReviewGenerateRequest,
    ReviewGenerateResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    ViabilityAssessment,
    CommentAnalysisItem,
)
from app.services import db_service
from app.services.github_service import GithubService
from app.services.rocketride_service import RocketrideService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=ReviewGenerateResponse)
async def generate_review(
    request: ReviewGenerateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    github_token: str = Depends(get_github_token),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI review: ticket eval + viability + comment analysis + personalized opinion."""
    owner, repo_name = request.repo.split("/", 1)
    github = GithubService(github_token)
    svc = RocketrideService()

    # Fetch PR data from DB
    pr = await db_service.get_pr(db, repo=request.repo, number=request.pr_number)
    if not pr:
        raise HTTPException(status_code=404, detail="PR not found — analyze it first")

    # Fetch current diff, comments, and linked ticket from GitHub
    diff = await github.get_pr_diff(owner, repo_name, request.pr_number)
    comments = await github.get_pr_comments(owner, repo_name, request.pr_number)
    ticket = await github.get_linked_issue(owner, repo_name, request.pr_number)

    # Step 1: Analyze existing comments vs current code
    comment_analysis = await svc.analyze_comments(pr, comments, diff)

    # Step 2: Evaluate the linked ticket/issue
    ticket_eval = await svc.evaluate_ticket(pr, ticket, diff)

    # Step 3: Assess viability against engineering criteria
    viability = await svc.assess_viability(pr, comments, diff)

    # Step 4: Generate personalized review opinion
    review = await svc.generate_review(pr, viability, comment_analysis, ticket_eval)

    # Merge risk signals: escalate if ticket or review flags risk
    needs_human = (
        review.get("needs_human_review", False)
        or ticket_eval.get("needs_human_review", False)
    )
    risk_level = review.get("risk_level", "low")
    if ticket_eval.get("risk_level") in ("high", "critical"):
        risk_level = ticket_eval["risk_level"]

    human_reasons = []
    if review.get("human_review_reason"):
        human_reasons.append(review["human_review_reason"])
    if ticket_eval.get("human_review_reason"):
        human_reasons.append(ticket_eval["human_review_reason"])

    return ReviewGenerateResponse(
        body=review.get("body", ""),
        event=review.get("event", "COMMENT"),
        viability=ViabilityAssessment(**viability),
        comment_analysis=[
            CommentAnalysisItem(**c)
            for c in comment_analysis
            if all(k in c for k in ("author", "body", "status", "explanation"))
        ],
        ticket_eval=ticket_eval,
        risk_level=risk_level,
        needs_human_review=needs_human,
        human_review_reason=" | ".join(human_reasons) if human_reasons else "",
    )


@router.post("/submit", response_model=ReviewSubmitResponse)
async def submit_review(
    request: ReviewSubmitRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    github_token: str = Depends(get_github_token),
    db: AsyncSession = Depends(get_db),
):
    """Submit a review to GitHub and store the action."""
    owner, repo_name = request.repo.split("/", 1)
    github = GithubService(github_token)

    try:
        result = await github.create_pr_review(
            owner, repo_name, request.pr_number, request.body, request.event
        )
    except Exception as e:
        logger.error(f"Failed to submit review: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"GitHub API error: {str(e)}")

    github_review_id = result.get("id", 0)
    fallback = result.get("fallback", "")

    await db_service.create_review_action(db, {
        "pr_number": request.pr_number,
        "repo": request.repo,
        "event": request.event,
        "body": request.body,
        "github_review_id": github_review_id,
        "submitted_by": user.get("login", ""),
    })

    return ReviewSubmitResponse(
        github_review_id=github_review_id,
        pr_number=request.pr_number,
        event=request.event,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        fallback=fallback,
    )


@router.get("/history/{pr_number}")
async def get_review_history(
    pr_number: int,
    repo: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get review history for a PR."""
    actions = await db_service.get_review_actions(db, repo=repo, pr_number=pr_number)
    return {"reviews": actions}


@router.post("/close-duplicate")
async def close_duplicate_pr(
    pr_number: int,
    repo: str,
    primary_pr: int,
    user: Dict[str, Any] = Depends(get_current_user),
    github_token: str = Depends(get_github_token),
):
    """Close a duplicate PR with a comment referencing the primary PR."""
    owner, repo_name = repo.split("/", 1)
    github = GithubService(github_token)

    comment = (
        f"Closing this PR as it overlaps with #{primary_pr}, which has been identified "
        f"as the primary PR for this work. Please review and contribute to #{primary_pr} instead.\n\n"
        f"*This action was performed by PR Analyzer.*"
    )

    success = await github.close_pr_with_comment(owner, repo_name, pr_number, comment)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to close PR on GitHub")

    return {"closed": True, "prNumber": pr_number, "primaryPR": primary_pr}
