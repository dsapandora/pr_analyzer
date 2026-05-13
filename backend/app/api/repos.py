from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import logging

from app.auth.jwt_handler import get_current_user, get_github_token
from app.services.github_service import GithubService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_repos(
    user: Dict[str, Any] = Depends(get_current_user),
    github_token: str = Depends(get_github_token),
):
    """List GitHub repositories for the authenticated user."""
    try:
        service = GithubService(github_token)
        repos = await service.get_user_repos()
        return {"repos": repos, "total": len(repos)}
    except Exception as e:
        logger.error(f"Failed to list repos: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch repositories: {str(e)}")


@router.get("/search")
async def search_repo(
    q: str,
    github_token: str = Depends(get_github_token),
):
    """Fetch a specific public repo by 'owner/repo' name."""
    parts = q.strip().split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Format must be owner/repo")
    owner, repo = parts
    service = GithubService(github_token)
    result = await service.get_repo(owner, repo)
    if not result:
        raise HTTPException(status_code=404, detail="Repository not found")
    return result


@router.get("/{owner}/{repo}/prs/count")
async def get_pr_count(
    owner: str,
    repo: str,
    github_token: str = Depends(get_github_token),
):
    """Get the count of open PRs for a repository."""
    try:
        service = GithubService(github_token)
        count = await service.get_open_pr_count(owner, repo)
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to get PR count: {e}")
        raise HTTPException(status_code=502, detail=str(e))
