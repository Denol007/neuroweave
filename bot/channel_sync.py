"""Channel sync — fetches monitored channels from the API or directly from DB.

Called on bot startup and periodically (every 5 min) to keep the
listener's monitored channel set in sync with the database.
"""

from __future__ import annotations

import os

import httpx
import structlog
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

logger = structlog.get_logger()

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")


async def fetch_monitored_channels_api() -> set[str]:
    """Fetch monitored channel discord_ids from the API.

    Falls back to direct DB query if API is unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all servers
            resp = await client.get(f"{API_BASE}/api/servers")
            if resp.status_code != 200:
                logger.warning("channel_sync_api_failed", status=resp.status_code)
                return await _fetch_from_db()

            servers = resp.json()
            # For now, we don't have a dedicated "list channels" endpoint
            # so we query DB directly
            return await _fetch_from_db()

    except Exception as e:
        logger.warning("channel_sync_api_error", error=str(e))
        return await _fetch_from_db()


async def _fetch_from_db() -> set[str]:
    """Direct DB query fallback for monitored channels."""
    try:
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://neuroweave:neuroweave@localhost:5432/neuroweave",
        )
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        engine = create_engine(sync_url, pool_pre_ping=True)

        with Session(engine) as db:
            rows = db.execute(
                text("SELECT discord_id FROM channels WHERE is_monitored = true")
            ).fetchall()

        engine.dispose()

        channel_ids = {row[0] for row in rows}
        logger.info("channel_sync_from_db", count=len(channel_ids))
        return channel_ids

    except Exception as e:
        logger.error("channel_sync_db_failed", error=str(e))
        return set()
