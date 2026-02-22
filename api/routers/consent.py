"""Consent router — GDPR consent management.

Endpoints:
  POST   /api/consent              — record user consent
  GET    /api/consent/{user_hash}  — check consent status
  DELETE /api/consent/{user_hash}  — revoke consent + cascade purge
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from api.deps import DB
from api.models.consent import ConsentRecord
from api.schemas.consent import ConsentCreate, ConsentResponse, ConsentStatus

logger = structlog.get_logger()

router = APIRouter()


@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def create_consent(body: ConsentCreate, db: DB):
    """Record a user's consent preferences for a server.

    If a consent record already exists for this user+server, update it.
    """
    # Check if consent already exists
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_hash == body.user_hash,
            ConsentRecord.server_id == body.server_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.kb_consent = body.kb_consent
        existing.ai_consent = body.ai_consent
        existing.revoked_at = None  # Re-granting clears revocation
        existing.granted_at = datetime.now(timezone.utc)
        logger.info("consent_updated", user_hash=body.user_hash[:8], server=body.server_id)
        return ConsentResponse.model_validate(existing)

    record = ConsentRecord(
        user_hash=body.user_hash,
        server_id=body.server_id,
        kb_consent=body.kb_consent,
        ai_consent=body.ai_consent,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info("consent_created", user_hash=body.user_hash[:8], server=body.server_id)
    return ConsentResponse.model_validate(record)


@router.get("/consent/{user_hash}", response_model=ConsentStatus)
async def get_consent(user_hash: str, db: DB):
    """Check consent status for a user across all servers."""
    result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_hash == user_hash)
    )
    consents = result.scalars().all()

    return ConsentStatus(
        user_hash=user_hash,
        consents=[ConsentResponse.model_validate(c) for c in consents],
    )


@router.delete("/consent/{user_hash}", status_code=status.HTTP_200_OK)
async def revoke_consent(user_hash: str, db: DB, server_id: int | None = None):
    """Revoke consent for a user. Marks records as revoked.

    If server_id is provided, revokes only for that server.
    Otherwise, revokes all consents for the user.

    Downstream effects (handled by Celery tasks):
    - Messages from this user are marked as "revoked"
    - Pending dataset exports are updated
    - Affected articles are re-generated without this user's contributions
    """
    query = select(ConsentRecord).where(ConsentRecord.user_hash == user_hash)
    if server_id:
        query = query.where(ConsentRecord.server_id == server_id)

    result = await db.execute(query)
    consents = result.scalars().all()

    if not consents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No consent records found for this user",
        )

    now = datetime.now(timezone.utc)
    revoked_count = 0
    for consent in consents:
        consent.kb_consent = False
        consent.ai_consent = False
        consent.revoked_at = now
        revoked_count += 1

    logger.info(
        "consent_revoked",
        user_hash=user_hash[:8],
        server_id=server_id,
        count=revoked_count,
    )

    return {"revoked": revoked_count, "user_hash": user_hash}
