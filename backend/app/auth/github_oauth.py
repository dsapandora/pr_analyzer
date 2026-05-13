import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
import logging

from app.config import settings
from app.auth.jwt_handler import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_SCOPE = "read:user user:email repo"


@router.get("/github/login")
async def github_login():
    """Redirect user to GitHub OAuth page."""
    params = {
        "client_id": settings.github_client_id,
        "scope": GITHUB_SCOPE,
        "redirect_uri": f"{settings.rocketride_url}/auth/github/callback"
        if not settings.github_client_id
        else None,
    }
    # Build clean params
    clean_params = "&".join(
        f"{k}={v}" for k, v in params.items() if v is not None
    )
    url = f"{GITHUB_AUTHORIZE_URL}?client_id={settings.github_client_id}&scope={GITHUB_SCOPE}"
    return RedirectResponse(url=url)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(..., description="OAuth code from GitHub"),
    state: str = Query(None),
):
    """Handle GitHub OAuth callback, exchange code for token, issue JWT."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")

    # Exchange code for GitHub access token
    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(
                GITHUB_TOKEN_URL,
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
                timeout=15.0,
            )
            token_data = token_response.json()
        except Exception as e:
            logger.error(f"Failed to exchange GitHub code: {e}")
            raise HTTPException(status_code=502, detail="Failed to exchange GitHub code")

    if "error" in token_data:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub OAuth error: {token_data.get('error_description', token_data['error'])}",
        )

    github_token = token_data.get("access_token")
    if not github_token:
        raise HTTPException(status_code=400, detail="No access token received from GitHub")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        try:
            user_response = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            user_data = user_response.json()
        except Exception as e:
            logger.error(f"Failed to fetch GitHub user info: {e}")
            raise HTTPException(status_code=502, detail="Failed to fetch user info from GitHub")

    # Create our JWT
    jwt_payload = {
        "sub": str(user_data.get("id")),
        "login": user_data.get("login"),
        "name": user_data.get("name") or user_data.get("login"),
        "email": user_data.get("email"),
        "avatar_url": user_data.get("avatar_url"),
        "github_token": github_token,
    }

    access_token = create_access_token(jwt_payload)

    # Redirect to frontend with token
    frontend_url = "http://localhost:3000"
    if hasattr(settings, "frontend_url"):
        frontend_url = settings.frontend_url

    return RedirectResponse(url=f"{frontend_url}/?token={access_token}")


@router.get("/me")
async def get_current_user_info(
    credentials: str = None,
):
    """Return current user info (for debugging)."""
    return {"message": "Use JWT token to access user info"}
