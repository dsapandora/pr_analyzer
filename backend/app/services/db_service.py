import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalysisJob, IngestionJob, PullRequest, ReviewAction, User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def upsert_user(db: AsyncSession, github_id: int, login: str, name: Optional[str], avatar_url: Optional[str]) -> User:
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()
    if user:
        user.login = login
        user.name = name
        user.avatar_url = avatar_url
        user.last_login = datetime.now(timezone.utc)
    else:
        user = User(github_id=github_id, login=login, name=name, avatar_url=avatar_url)
        db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Analysis jobs
# ---------------------------------------------------------------------------

async def create_job(db: AsyncSession, job_id: str, repo: str, user_id: Optional[int] = None) -> AnalysisJob:
    job = AnalysisJob(id=job_id, repo=repo, user_id=user_id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_job(db: AsyncSession, job_id: str, **kwargs) -> None:
    await db.execute(update(AnalysisJob).where(AnalysisJob.id == job_id).values(**kwargs))
    await db.commit()


async def get_job(db: AsyncSession, job_id: str) -> Optional[AnalysisJob]:
    result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Pull requests
# ---------------------------------------------------------------------------

async def upsert_pr(db: AsyncSession, pr_data: Dict[str, Any]) -> PullRequest:
    """Insert or update a PR record."""
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.repo == pr_data["repo"],
            PullRequest.number == pr_data["number"],
        )
    )
    pr = result.scalar_one_or_none()

    if pr:
        for key, value in _extract_fields(pr_data).items():
            setattr(pr, key, value)
    else:
        pr = PullRequest(**_extract_fields(pr_data))
        db.add(pr)

    await db.commit()
    await db.refresh(pr)
    return pr


def _extract_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "github_id": data.get("github_id") or data.get("id"),
        "number": data["number"],
        "repo": data["repo"],
        "title": data.get("title", ""),
        "description": data.get("description") or data.get("body") or "",
        "author": data.get("author", ""),
        "author_avatar": data.get("authorAvatar") or data.get("author_avatar") or "",
        "url": data.get("url") or data.get("html_url") or "",
        "topics": data.get("topics", []),
        "score": data.get("score", 0),
        "recommendation": data.get("recommendation", "keep"),
        "summary": data.get("summary") or "",
        "reasoning": data.get("reasoning") or "",
        "similar_prs": data.get("similarPRs") or data.get("similar_prs") or [],
        "files_changed": data.get("filesChanged") or data.get("files_changed") or [],
        "additions": data.get("additions", 0),
        "deletions": data.get("deletions", 0),
        "status": data.get("status", "pending"),
        "review_status": data.get("reviewStatus") or data.get("review_status") or None,
        "reviewers": data.get("reviewers") or [],
        "github_created_at": data.get("createdAt") or data.get("created_at") or "",
        "analyzed_at": datetime.now(timezone.utc) if data.get("status") == "analyzed" else None,
    }


async def get_prs(
    db: AsyncSession,
    repo: str,
    topic: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    stmt = select(PullRequest).where(PullRequest.repo == repo)
    if topic:
        # JSON_CONTAINS for MariaDB
        stmt = stmt.where(func.json_contains(PullRequest.topics, f'"{topic}"'))
    stmt = stmt.order_by(PullRequest.score.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [_to_dict(pr) for pr in result.scalars().all()]


async def get_pr(db: AsyncSession, repo: str, number: int) -> Optional[Dict[str, Any]]:
    result = await db.execute(
        select(PullRequest).where(PullRequest.repo == repo, PullRequest.number == number)
    )
    pr = result.scalar_one_or_none()
    return _to_dict(pr) if pr else None


async def get_topics(db: AsyncSession, repo: str) -> List[str]:
    prs = await get_prs(db, repo, limit=500)
    topics: set = set()
    for pr in prs:
        for t in pr.get("topics", []):
            if t:
                topics.add(t)
    return sorted(topics)


async def get_stats(db: AsyncSession, repo: str) -> Dict[str, Any]:
    prs = await get_prs(db, repo, limit=500)
    total = len(prs)
    analyzed = sum(1 for p in prs if p.get("status") == "analyzed")
    duplicates = sum(1 for p in prs if len(p.get("similarPRs", [])) > 0)
    topic_set = set(t for p in prs for t in p.get("topics", []))
    recommended = {"merge": 0, "keep": 0, "discard": 0, "combine": 0}
    for p in prs:
        rec = p.get("recommendation", "keep")
        if rec in recommended:
            recommended[rec] += 1
    return {
        "total": total,
        "analyzed": analyzed,
        "duplicates": duplicates,
        "topics": len(topic_set),
        "recommended": recommended,
    }


async def delete_closed_prs(db: AsyncSession, repo: str, open_numbers: List[int]) -> int:
    """Delete PRs for a repo that are no longer in the open PR list (i.e. closed/merged)."""
    result = await db.execute(
        delete(PullRequest).where(
            PullRequest.repo == repo,
            PullRequest.number.not_in(open_numbers),
        )
    )
    await db.commit()
    return result.rowcount


async def update_similar_prs(db: AsyncSession, repo: str, number: int, similar: List[int]) -> None:
    await db.execute(
        update(PullRequest)
        .where(PullRequest.repo == repo, PullRequest.number == number)
        .values(similar_prs=similar)
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Ingestion jobs
# ---------------------------------------------------------------------------

async def create_ingestion_job(db: AsyncSession, job_id: str, repo: str, user_id: Optional[int] = None) -> IngestionJob:
    job = IngestionJob(id=job_id, repo=repo, user_id=user_id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_ingestion_job(db: AsyncSession, job_id: str, **kwargs) -> None:
    await db.execute(update(IngestionJob).where(IngestionJob.id == job_id).values(**kwargs))
    await db.commit()


async def get_ingestion_job(db: AsyncSession, job_id: str) -> Optional[IngestionJob]:
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Review actions
# ---------------------------------------------------------------------------

async def create_review_action(db: AsyncSession, data: Dict[str, Any]) -> ReviewAction:
    review = ReviewAction(
        pr_number=data["pr_number"],
        repo=data["repo"],
        event=data["event"],
        body=data["body"],
        viability_score=data.get("viability_score", 0),
        github_review_id=data.get("github_review_id"),
        submitted_by=data.get("submitted_by"),
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def get_review_actions(db: AsyncSession, repo: str, pr_number: int) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(ReviewAction)
        .where(ReviewAction.repo == repo, ReviewAction.pr_number == pr_number)
        .order_by(ReviewAction.submitted_at.desc())
    )
    return [
        {
            "id": r.id,
            "prNumber": r.pr_number,
            "repo": r.repo,
            "event": r.event,
            "body": r.body,
            "viabilityScore": r.viability_score,
            "githubReviewId": r.github_review_id,
            "submittedBy": r.submitted_by,
            "submittedAt": r.submitted_at.isoformat() if r.submitted_at else "",
        }
        for r in result.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Related PRs (enhanced)
# ---------------------------------------------------------------------------

async def get_related_prs(db: AsyncSession, repo: str, pr_numbers: List[int]) -> List[Dict[str, Any]]:
    """Fetch full info for a list of related PR numbers."""
    if not pr_numbers:
        return []
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.repo == repo,
            PullRequest.number.in_(pr_numbers),
        )
    )
    return [_to_dict(pr) for pr in result.scalars().all()]


def _to_dict(pr: PullRequest) -> Dict[str, Any]:
    return {
        "id": pr.id,
        "number": pr.number,
        "repo": pr.repo,
        "title": pr.title,
        "description": pr.description or "",
        "author": pr.author,
        "authorAvatar": pr.author_avatar or "",
        "url": pr.url or "",
        "topics": pr.topics or [],
        "score": pr.score,
        "recommendation": pr.recommendation,
        "summary": pr.summary or "",
        "reasoning": pr.reasoning or "",
        "similarPRs": pr.similar_prs or [],
        "filesChanged": pr.files_changed or [],
        "additions": pr.additions,
        "deletions": pr.deletions,
        "status": pr.status,
        "reviewStatus": pr.review_status or None,
        "reviewers": pr.reviewers or [],
        "createdAt": pr.github_created_at or "",
    }
