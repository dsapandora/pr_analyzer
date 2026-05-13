import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.auth.jwt_handler import get_current_user, get_github_token
from app.db.base import AsyncSessionLocal
from app.models.schemas import AnalyzeRequest, JobStatus
from app.services.github_service import GithubService
from app.services.rocketride_service import RocketrideService
from app.services import db_service
from app.db.base import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


async def run_analysis(job_id: str, repo: str, github_token: str, user_id: int):
    """Background task: analyze all open PRs in a repository."""
    async with AsyncSessionLocal() as db:
        await db_service.update_job(db, job_id, status="running", message="Fetching pull requests from GitHub...")

        try:
            github = GithubService(github_token)
            rocketride = RocketrideService()

            owner, repo_name = repo.split("/", 1)
            pr_list = await github.get_repo_prs(owner, repo_name)
            total = len(pr_list)

            open_numbers = [pr["number"] for pr in pr_list]
            removed = await db_service.delete_closed_prs(db, repo, open_numbers)
            if removed:
                logger.info(f"Removed {removed} closed/merged PRs from {repo}")

            await db_service.update_job(db, job_id, total=total, message=f"Analyzing {total} pull requests...")

            success_count = 0
            for i, pr_data in enumerate(pr_list):
                await db_service.update_job(
                    db, job_id,
                    processed=i,
                    progress=int((i / max(total, 1)) * 100),
                    message=f"Analyzing PR #{pr_data['number']}: {pr_data['title'][:50]}...",
                )

                try:
                    diff = await github.get_pr_diff(owner, repo_name, pr_data["number"])
                    files = await github.get_pr_files(owner, repo_name, pr_data["number"])
                    review_status, reviewers = await github.get_pr_review_status(owner, repo_name, pr_data["number"])

                    analysis = await rocketride.analyze_pr({
                        "number": pr_data["number"],
                        "title": pr_data["title"],
                        "description": pr_data.get("body", "") or "",
                        "diff": diff[:4000],
                        "files": [f["filename"] for f in files],
                        "repo": repo,
                    })

                    # similar_prs comes from the LLM via RAG context in Qdrant
                    similar_prs = analysis.get("similar_prs", [])

                    await db_service.upsert_pr(db, {
                        "github_id": pr_data["id"],
                        "number": pr_data["number"],
                        "repo": repo,
                        "title": pr_data["title"],
                        "description": pr_data.get("body", "") or "",
                        "author": pr_data["user"]["login"],
                        "authorAvatar": pr_data["user"].get("avatar_url", ""),
                        "url": pr_data["html_url"],
                        "topics": analysis.get("topics", ["other"]),
                        "score": analysis.get("score", 50),
                        "recommendation": analysis.get("recommendation", "keep"),
                        "summary": analysis.get("summary", ""),
                        "reasoning": analysis.get("reasoning", ""),
                        "similarPRs": similar_prs,
                        "filesChanged": [f["filename"] for f in files],
                        "additions": pr_data.get("additions", 0),
                        "deletions": pr_data.get("deletions", 0),
                        "status": "analyzed",
                        "reviewStatus": review_status,
                        "reviewers": reviewers,
                        "createdAt": pr_data["created_at"],
                    })
                    success_count += 1

                except Exception as pr_error:
                    logger.warning(f"Failed to analyze PR #{pr_data['number']}: {pr_error}")
                    await db_service.upsert_pr(db, {
                        "github_id": pr_data.get("id"),
                        "number": pr_data["number"],
                        "repo": repo,
                        "title": pr_data["title"],
                        "description": pr_data.get("body", "") or "",
                        "author": pr_data["user"]["login"],
                        "authorAvatar": pr_data["user"].get("avatar_url", ""),
                        "url": pr_data["html_url"],
                        "topics": [],
                        "score": 0,
                        "recommendation": "keep",
                        "filesChanged": [],
                        "additions": pr_data.get("additions", 0),
                        "deletions": pr_data.get("deletions", 0),
                        "status": "error",
                        "createdAt": pr_data["created_at"],
                    })

            await db_service.update_job(
                db, job_id,
                status="completed",
                progress=100,
                processed=total,
                message=f"Done! Analyzed {success_count}/{total} PRs successfully.",
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Analysis job {job_id} failed: {e}", exc_info=True)
            await db_service.update_job(
                db, job_id,
                status="error",
                message=f"Analysis failed: {str(e)}",
                completed_at=datetime.now(timezone.utc),
            )


@router.post("")
async def trigger_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user),
    github_token: str = Depends(get_github_token),
    db: AsyncSession = Depends(get_db),
):
    if "/" not in request.repo:
        raise HTTPException(status_code=400, detail="repo must be in format: owner/repo")

    job_id = str(uuid.uuid4())
    user_id = user.get("db_id")

    job = await db_service.create_job(db, job_id=job_id, repo=request.repo, user_id=user_id)
    background_tasks.add_task(run_analysis, job_id, request.repo, github_token, user_id)

    return {
        "jobId": job_id,
        "status": "pending",
        "progress": 0,
        "total": 0,
        "processed": 0,
        "message": "Analysis started",
        "started_at": job.started_at.isoformat(),
    }


@router.get("/status/{job_id}")
async def get_analysis_status(
    job_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "jobId": job_id,
        "status": job.status,
        "progress": job.progress,
        "total": job.total,
        "processed": job.processed,
        "message": job.message,
        "started_at": job.started_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
