"""GitHub repo management router.

Endpoints:
  POST   /api/github/repos           — add a GitHub repo as knowledge source
  GET    /api/github/repos           — list GitHub repo sources
  POST   /api/github/repos/{id}/sync — trigger immediate fetch
  DELETE /api/github/repos/{id}      — remove repo and all its data
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.deps import DB
from api.models.channel import Channel
from api.models.server import Server
from api.schemas.github import GitHubRepoCreate, GitHubRepoResponse, GitHubSyncResponse

logger = structlog.get_logger()

router = APIRouter()


@router.post("/github/repos", response_model=GitHubRepoResponse, status_code=status.HTTP_201_CREATED)
async def add_github_repo(body: GitHubRepoCreate, db: DB):
    """Add a GitHub repo as a knowledge source.

    Creates a server record (source_type=github) and channel records
    for each discussion category.
    """
    external_id = f"{body.owner}/{body.repo}"

    # Check if already registered
    existing = await db.execute(
        select(Server).where(Server.external_id == external_id, Server.source_type == "github")
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repo already registered")

    # Fetch categories from GitHub
    categories = []
    try:
        from api.config import settings
        from api.services.github_fetcher import GitHubDiscussionsFetcher

        if settings.GITHUB_TOKEN:
            import asyncio
            fetcher = GitHubDiscussionsFetcher(settings.GITHUB_TOKEN)
            categories = await fetcher.fetch_categories(body.owner, body.repo)
    except Exception as e:
        logger.warning("github_categories_fetch_failed", error=str(e))

    # Create server
    server = Server(
        source_type="github",
        external_id=external_id,
        name=f"{body.owner}/{body.repo}",
        source_url=f"https://github.com/{body.owner}/{body.repo}/discussions",
        source_metadata={"categories": categories, "owner": body.owner, "repo": body.repo},
    )
    db.add(server)
    await db.flush()

    # Create channel records for categories
    for cat in categories:
        is_monitored = True
        if body.category_filters:
            is_monitored = cat.get("name", "") in body.category_filters

        channel = Channel(
            server_id=server.id,
            external_id=cat["id"],
            name=cat.get("name", "Unknown"),
            is_monitored=is_monitored,
        )
        db.add(channel)

    # If no categories fetched, create a default "all" channel
    if not categories:
        channel = Channel(
            server_id=server.id,
            external_id="all",
            name="All Discussions",
            is_monitored=True,
        )
        db.add(channel)

    await db.flush()

    logger.info("github_repo_added", repo=external_id, categories=len(categories))

    return GitHubRepoResponse(
        id=server.id,
        external_id=server.external_id,
        name=server.name,
        source_type=server.source_type,
        source_url=server.source_url,
        plan=server.plan.value if hasattr(server.plan, 'value') else str(server.plan),
        categories=categories,
        created_at=server.created_at,
    )


@router.get("/github/repos", response_model=list[GitHubRepoResponse])
async def list_github_repos(db: DB):
    """List all registered GitHub repo sources."""
    result = await db.execute(
        select(Server).where(Server.source_type == "github").order_by(Server.created_at.desc())
    )
    servers = result.scalars().all()

    return [
        GitHubRepoResponse(
            id=s.id,
            external_id=s.external_id,
            name=s.name,
            source_type=s.source_type,
            source_url=s.source_url,
            plan=s.plan.value if hasattr(s.plan, 'value') else str(s.plan),
            categories=s.source_metadata.get("categories", []) if s.source_metadata else [],
            last_fetched_at=s.source_metadata.get("last_fetched_at") if s.source_metadata else None,
            created_at=s.created_at,
        )
        for s in servers
    ]


@router.post("/github/repos/{server_id}/sync", response_model=GitHubSyncResponse)
async def sync_github_repo(server_id: int, db: DB):
    """Trigger immediate fetch of discussions for a GitHub repo."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()

    if not server or server.source_type != "github":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub repo not found")

    try:
        from api.tasks.fetch_github_discussions import fetch_and_process
        fetch_and_process.delay(server_id)
        logger.info("github_sync_triggered", repo=server.external_id)
    except Exception as e:
        logger.warning("github_sync_dispatch_failed", error=str(e))

    return GitHubSyncResponse(server_id=server_id, status="dispatched")


@router.delete("/github/repos/{server_id}", status_code=status.HTTP_200_OK)
async def delete_github_repo(server_id: int, db: DB):
    """Remove a GitHub repo and cascade delete all its data."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()

    if not server or server.source_type != "github":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub repo not found")

    repo_name = server.external_id
    await db.delete(server)
    logger.info("github_repo_deleted", repo=repo_name)

    return {"deleted": repo_name}
