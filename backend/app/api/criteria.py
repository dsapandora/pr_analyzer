import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.auth.jwt_handler import get_current_user, get_github_token
from app.config import settings
from app.db.base import AsyncSessionLocal
from app.models.schemas import IngestCriteriaRequest
from app.services.github_service import GithubService
from app.services.rocketride_service import RocketrideService
from app.services import db_service
from app.db.base import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


async def run_ingestion(job_id: str, repo: str, authors: list[str], github_token: str):
    """Background task: fetch commits from authors and ingest into criteria pipeline."""
    async with AsyncSessionLocal() as db:
        await db_service.update_ingestion_job(
            db, job_id, status="running", message="Fetching commits from GitHub..."
        )
        try:
            github = GithubService(github_token)
            rocketride_svc = RocketrideService()

            owner, repo_name = repo.split("/", 1)
            commits = await github.get_commits_by_authors(owner, repo_name, authors)
            total = len(commits)

            await db_service.update_ingestion_job(
                db, job_id, total=total, message=f"Ingesting {total} commits into criteria pipeline..."
            )

            success_count = 0
            batch_size = 10
            for i in range(0, total, batch_size):
                batch = commits[i : i + batch_size]
                count = await rocketride_svc.ingest_commits(batch)
                success_count += count
                await db_service.update_ingestion_job(
                    db,
                    job_id,
                    processed=min(i + batch_size, total),
                    progress=int((min(i + batch_size, total) / max(total, 1)) * 100),
                    message=f"Ingested {success_count}/{min(i + batch_size, total)} commits...",
                )

            await db_service.update_ingestion_job(
                db,
                job_id,
                status="completed",
                progress=100,
                processed=total,
                message=f"Done! Ingested {success_count}/{total} commits successfully.",
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Ingestion job {job_id} failed: {e}", exc_info=True)
            await db_service.update_ingestion_job(
                db,
                job_id,
                status="error",
                message=f"Ingestion failed: {str(e)}",
                completed_at=datetime.now(timezone.utc),
            )


@router.post("/ingest")
async def trigger_ingestion(
    request: IngestCriteriaRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user),
    github_token: str = Depends(get_github_token),
    db: AsyncSession = Depends(get_db),
):
    repo = request.repo
    if "/" not in repo:
        raise HTTPException(status_code=400, detail="repo must be in format: owner/repo")

    authors = request.authors or settings.criteria_authors
    job_id = str(uuid.uuid4())
    user_id = user.get("db_id")

    job = await db_service.create_ingestion_job(db, job_id=job_id, repo=repo, user_id=user_id)
    background_tasks.add_task(run_ingestion, job_id, repo, authors, github_token)

    return {
        "jobId": job_id,
        "status": "pending",
        "progress": 0,
        "total": 0,
        "processed": 0,
        "message": f"Ingestion started for {len(authors)} authors",
        "startedAt": job.started_at.isoformat(),
    }


@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db_service.get_ingestion_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "jobId": job_id,
        "status": job.status,
        "progress": job.progress,
        "total": job.total,
        "processed": job.processed,
        "message": job.message,
        "startedAt": job.started_at.isoformat(),
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
    }
