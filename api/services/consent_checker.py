"""Consent checker — filters messages based on user consent status.

Queries the consent_records table and removes messages from users
who have not consented (or revoked consent) before pipeline processing.

This is a GDPR requirement: no data processing without explicit consent.
"""

from __future__ import annotations

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings

logger = structlog.get_logger()

# Sync engine for Celery workers (no async event loop)
_sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_engine = create_engine(_sync_url, pool_pre_ping=True, pool_size=5)


def get_consented_users(server_id: str) -> set[str]:
    """Get set of author_hashes that have active kb_consent for a server.

    Args:
        server_id: External server ID (looked up via servers.external_id).

    Returns:
        Set of user_hash strings with active consent.
    """
    try:
        with Session(_engine) as db:
            rows = db.execute(
                text("""
                    SELECT cr.user_hash
                    FROM consent_records cr
                    JOIN servers s ON cr.server_id = s.id
                    WHERE s.external_id = :server_id
                      AND cr.kb_consent = true
                      AND cr.revoked_at IS NULL
                """),
                {"server_id": server_id},
            ).fetchall()
        return {row[0] for row in rows}
    except Exception as e:
        logger.error("consent_check_failed", error=str(e))
        # On DB error, return empty set (fail-safe: no processing without consent)
        return set()


def filter_consented_messages(
    messages: list[dict],
    server_id: str,
) -> tuple[list[dict], int]:
    """Filter messages to only include those from consented users.

    Args:
        messages: List of message dicts with 'author_hash' field.
        server_id: Discord server ID for consent lookup.

    Returns:
        Tuple of (filtered_messages, excluded_count).
    """
    consented_users = get_consented_users(server_id)

    if not consented_users:
        # No consented users at all — could mean:
        # 1. No one consented yet (common for new servers)
        # 2. DB error (logged above)
        # In both cases, skip all messages (GDPR safe default)
        logger.warning(
            "no_consented_users",
            server_id=server_id,
            total_messages=len(messages),
        )
        return [], len(messages)

    filtered = []
    excluded = 0

    for msg in messages:
        author_hash = msg.get("author_hash", "")
        if author_hash in consented_users:
            filtered.append(msg)
        else:
            excluded += 1

    if excluded > 0:
        logger.info(
            "consent_filtered",
            server_id=server_id,
            passed=len(filtered),
            excluded=excluded,
        )

    return filtered, excluded
