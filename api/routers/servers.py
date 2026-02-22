"""Servers router — server listing, channel management, stats.

Endpoints:
  GET  /api/servers                    — list public servers
  POST /api/servers/{id}/channels      — set monitored channels
  GET  /api/servers/{id}/stats         — server analytics
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from api.deps import DB, CurrentUser
from api.models.article import Article
from api.models.channel import Channel
from api.models.message import Message
from api.models.server import Server
from api.models.thread import Thread, ThreadStatus
from api.schemas.server import ChannelUpdate, ServerResponse, ServerStats

logger = structlog.get_logger()

router = APIRouter()


@router.get("/servers", response_model=list[ServerResponse])
async def list_servers(db: DB):
    """List all servers with knowledge bases."""
    result = await db.execute(
        select(Server).order_by(Server.created_at.desc())
    )
    servers = result.scalars().all()
    return [ServerResponse.model_validate(s) for s in servers]


@router.post("/servers/{server_id}/channels")
async def set_monitored_channels(
    server_id: int,
    body: ChannelUpdate,
    db: DB,
    user: CurrentUser,
):
    """Set which channels are monitored for knowledge extraction."""
    # Verify server exists
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

    updated = 0
    for discord_id in body.channel_discord_ids:
        result = await db.execute(
            select(Channel).where(
                Channel.server_id == server_id,
                Channel.discord_id == discord_id,
            )
        )
        channel = result.scalar_one_or_none()
        if channel:
            channel.is_monitored = body.is_monitored
            updated += 1

    logger.info(
        "channels_updated",
        server_id=server_id,
        updated=updated,
        monitored=body.is_monitored,
    )
    return {"updated": updated, "is_monitored": body.is_monitored}


@router.get("/servers/{server_id}/stats", response_model=ServerStats)
async def get_server_stats(server_id: int, db: DB):
    """Get analytics for a server."""
    # Verify server
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

    # Channel IDs for this server
    ch_result = await db.execute(
        select(Channel.id).where(Channel.server_id == server_id)
    )
    channel_ids = [r[0] for r in ch_result.all()]

    if not channel_ids:
        return ServerStats(
            server_id=server_id, server_name=server.name,
            total_articles=0, total_threads=0, total_messages=0,
            noise_filtered=0, avg_quality_score=0.0,
            top_languages=[], top_tags=[],
        )

    # Counts
    msg_count = (await db.execute(
        select(func.count()).where(Message.channel_id.in_(channel_ids))
    )).scalar() or 0

    thread_count = (await db.execute(
        select(func.count()).where(Thread.channel_id.in_(channel_ids))
    )).scalar() or 0

    noise_count = (await db.execute(
        select(func.count()).where(
            Thread.channel_id.in_(channel_ids),
            Thread.status == ThreadStatus.NOISE,
        )
    )).scalar() or 0

    # Article stats
    article_query = (
        select(Article)
        .join(Thread, Thread.id == Article.thread_id)
        .where(Thread.channel_id.in_(channel_ids))
    )
    articles = (await db.execute(article_query)).scalars().all()

    total_articles = len(articles)
    avg_quality = sum(a.quality_score for a in articles) / total_articles if total_articles else 0.0

    # Top languages
    lang_counts: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    for a in articles:
        lang_counts[a.language] = lang_counts.get(a.language, 0) + 1
        for t in a.tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    top_languages = sorted(
        [{"language": k, "count": v} for k, v in lang_counts.items()],
        key=lambda x: x["count"], reverse=True,
    )[:10]

    top_tags = sorted(
        [{"tag": k, "count": v} for k, v in tag_counts.items()],
        key=lambda x: x["count"], reverse=True,
    )[:10]

    return ServerStats(
        server_id=server_id,
        server_name=server.name,
        total_articles=total_articles,
        total_threads=thread_count,
        total_messages=msg_count,
        noise_filtered=noise_count,
        avg_quality_score=round(avg_quality, 3),
        top_languages=top_languages,
        top_tags=top_tags,
    )
