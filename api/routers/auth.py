"""Discord OAuth2 authentication router.

Flow:
1. GET /api/auth/discord → redirect to Discord OAuth2 authorize URL
2. User approves on Discord
3. GET /api/auth/discord/callback?code=... → exchange code for token → return JWT
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import jwt

from api.config import settings
from api.deps import ALGORITHM, CurrentUser

FRONTEND_URL = settings.CORS_ORIGINS.split(",")[0]  # http://localhost:3000

logger = structlog.get_logger()

router = APIRouter()

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_OAUTH_AUTHORIZE = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN = "https://discord.com/api/oauth2/token"
REDIRECT_URI = "http://localhost:8000/api/auth/discord/callback"

JWT_EXPIRY_HOURS = 168  # 7 days


def _create_jwt(user_data: dict) -> str:
    """Create a JWT token for the authenticated user."""
    payload = {
        "sub": user_data["id"],
        "discord_id": user_data["id"],
        "username": user_data.get("username", ""),
        "avatar": user_data.get("avatar"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=ALGORITHM)


@router.get("/discord")
async def discord_oauth_redirect():
    """Redirect to Discord OAuth2 authorization page."""
    if not settings.DISCORD_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discord OAuth2 not configured",
        )

    params = urlencode({
        "client_id": settings.DISCORD_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
    })
    return {"redirect_url": f"{DISCORD_OAUTH_AUTHORIZE}?{params}"}


@router.get("/discord/callback")
async def discord_oauth_callback(code: str):
    """Exchange OAuth2 code for Discord user data, return JWT.

    Args:
        code: The authorization code from Discord redirect.
    """
    if not settings.DISCORD_CLIENT_ID or not settings.DISCORD_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discord OAuth2 not configured",
        )

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            DISCORD_OAUTH_TOKEN,
            data={
                "client_id": settings.DISCORD_CLIENT_ID,
                "client_secret": settings.DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            logger.error("discord_token_exchange_failed", status=token_response.status_code)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange Discord code",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Fetch user profile
        user_response = await client.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch Discord user",
            )

        user_data = user_response.json()

        # Fetch user's guilds (servers)
        guilds_response = await client.get(
            f"{DISCORD_API_BASE}/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        guilds = []
        if guilds_response.status_code == 200:
            guilds = [g["id"] for g in guilds_response.json()]

    jwt_token = _create_jwt(user_data)

    logger.info("discord_auth_success", user=user_data.get("username"))

    # Redirect to frontend with token and user data
    user_json = json.dumps({
        "id": user_data["id"],
        "username": user_data.get("username"),
        "avatar": user_data.get("avatar"),
        "guilds": guilds,
    })
    params = urlencode({"token": jwt_token, "user": user_json})
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?{params}")


@router.get("/me")
async def get_me(user: CurrentUser):
    """Return current authenticated user info."""
    return {
        "discord_id": user.get("discord_id"),
        "username": user.get("username"),
    }
