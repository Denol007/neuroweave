"""Celery task: fetch GitHub Discussions and process through pipeline.

Periodic task that runs every 15 minutes for each registered GitHub repo.
Each discussion is converted to messages and sent through the extraction pipeline.
"""

from __future__ import annotations

import asyncio

import structlog

from api.celery_app import app

logger = structlog.get_logger()


@app.task(
    name="api.tasks.fetch_github_discussions.fetch_and_process",
    max_retries=2,
    default_retry_delay=300,
)
def fetch_and_process(server_id: int):
    """Fetch new discussions for a GitHub repo and process them.

    Args:
        server_id: Internal DB server ID (not external_id).
    """
    from sqlalchemy import create_engine, select, text
    from sqlalchemy.orm import Session

    from api.config import settings
    from api.models.server import Server
    from api.models.channel import Channel
    from api.services.github_fetcher import GitHubDiscussionsFetcher

    if not settings.GITHUB_TOKEN:
        logger.warning("github_token_not_set")
        return

    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url)

    try:
        with Session(engine) as db:
            server = db.execute(select(Server).where(Server.id == server_id)).scalar_one_or_none()
            if not server or server.source_type != "github":
                logger.warning("not_a_github_server", server_id=server_id)
                return

            external_id = server.external_id  # "owner/repo"
            parts = external_id.split("/")
            if len(parts) != 2:
                logger.error("invalid_github_external_id", external_id=external_id)
                return

            owner, repo = parts

            # Get monitored category IDs
            monitored_channels = db.execute(
                select(Channel).where(Channel.server_id == server_id, Channel.is_monitored.is_(True))
            ).scalars().all()
            category_ids = [ch.external_id for ch in monitored_channels]

        # Fetch discussions
        fetcher = GitHubDiscussionsFetcher(settings.GITHUB_TOKEN)

        async def _fetch():
            all_discussions = []
            if category_ids:
                for cat_id in category_ids:
                    discussions = await fetcher.fetch_discussions(owner, repo, category_id=cat_id, limit=10)
                    all_discussions.extend(discussions)
            else:
                all_discussions = await fetcher.fetch_discussions(owner, repo, limit=20)
            return all_discussions

        discussions = asyncio.run(_fetch())

        logger.info("github_fetch_complete", repo=external_id, discussions=len(discussions))

        # Process each discussion through pipeline
        from api.tasks.process_messages import process_message_batch

        processed = 0
        for discussion in discussions:
            messages = fetcher.discussion_to_messages(discussion)
            if len(messages) < 2:
                continue  # Skip single-message discussions (no answers/comments)

            # Find matching category channel
            category = discussion.get("category", {})
            channel_id = category.get("id", "uncategorized")

            process_message_batch.delay(
                channel_id=channel_id,
                server_id=external_id,
                messages=messages,
                source_type="github",
            )
            processed += 1

        logger.info("github_discussions_dispatched", repo=external_id, processed=processed)

        # Update last_fetched_at in server metadata
        with Session(engine) as db:
            db.execute(
                text("UPDATE servers SET source_metadata = source_metadata || :meta WHERE id = :sid"),
                {"meta": '{"last_fetched_at": "' + asyncio.run(asyncio.coroutine(lambda: "now")()) + '"}' if False else '{}', "sid": server_id},
            )
            from datetime import datetime, timezone
            db.execute(
                text("UPDATE servers SET source_metadata = jsonb_set(COALESCE(source_metadata, '{}'), '{last_fetched_at}', to_jsonb(:ts::text)) WHERE id = :sid"),
                {"ts": datetime.now(timezone.utc).isoformat(), "sid": server_id},
            )
            db.commit()

    except Exception as e:
        logger.error("github_fetch_failed", server_id=server_id, error=str(e))
        raise
    finally:
        engine.dispose()


@app.task(name="api.tasks.fetch_github_discussions.fetch_all_github_repos")
def fetch_all_github_repos():
    """Periodic task: fetch discussions for all registered GitHub repos."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from api.config import settings

    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url)

    try:
        with Session(engine) as db:
            from api.models.server import Server
            servers = db.execute(
                select(Server).where(Server.source_type == "github")
            ).scalars().all()

            for server in servers:
                fetch_and_process.delay(server.id)
                logger.info("github_fetch_scheduled", server=server.external_id)

    finally:
        engine.dispose()
