"""Stripe webhook handler.

Endpoint:
  POST /api/webhooks/stripe — handle Stripe payment events

Verifies webhook signature, then processes relevant events:
  - checkout.session.completed → activate subscription (set plan to PRO)
  - customer.subscription.updated → update plan tier
  - customer.subscription.deleted → downgrade to FREE
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import structlog
from fastapi import APIRouter, HTTPException, Header, Request, status
from sqlalchemy import select

from api.config import settings
from api.deps import DB
from api.models.server import Server, ServerPlan

logger = structlog.get_logger()

router = APIRouter()

# Stripe price_id → ServerPlan mapping
PRICE_PLAN_MAP: dict[str, ServerPlan] = {
    "price_pro_monthly": ServerPlan.PRO,
    "price_pro_yearly": ServerPlan.PRO,
    "price_enterprise_monthly": ServerPlan.ENTERPRISE,
    "price_enterprise_yearly": ServerPlan.ENTERPRISE,
}


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> dict:
    """Verify Stripe webhook signature (v1 scheme)."""
    if not sig_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature")

    elements = dict(item.split("=", 1) for item in sig_header.split(",") if "=" in item)
    timestamp = elements.get("t")
    signature = elements.get("v1")

    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature format")

    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Timestamp too old")

    signed_payload = f"{timestamp}.{payload.decode()}"
    expected = hmac.new(
        secret.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    return json.loads(payload)


async def _update_server_plan(db, discord_id: str, plan: ServerPlan):
    """Find server by discord_id and update its plan."""
    if not discord_id:
        logger.warning("stripe_no_server_id")
        return
    result = await db.execute(select(Server).where(Server.discord_id == discord_id))
    server = result.scalar_one_or_none()
    if server:
        old_plan = server.plan
        server.plan = plan
        logger.info("server_plan_updated", server=discord_id, old=old_plan.value, new=plan.value)
    else:
        logger.warning("stripe_server_not_found", discord_id=discord_id)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: DB,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """Handle incoming Stripe webhook events."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured",
        )

    payload = await request.body()
    event = _verify_stripe_signature(payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET)

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    logger.info("stripe_event", type=event_type, id=event.get("id"))

    if event_type == "checkout.session.completed":
        server_discord_id = data.get("metadata", {}).get("server_id")
        await _update_server_plan(db, server_discord_id, ServerPlan.PRO)

    elif event_type == "customer.subscription.updated":
        server_discord_id = data.get("metadata", {}).get("server_id")
        price_id = (
            data.get("items", {}).get("data", [{}])[0]
            .get("price", {}).get("id", "")
        )
        plan = PRICE_PLAN_MAP.get(price_id, ServerPlan.PRO)
        await _update_server_plan(db, server_discord_id, plan)

    elif event_type == "customer.subscription.deleted":
        server_discord_id = data.get("metadata", {}).get("server_id")
        await _update_server_plan(db, server_discord_id, ServerPlan.FREE)

    elif event_type == "invoice.payment_failed":
        logger.warning("payment_failed", customer=data.get("customer"))

    return {"received": True}
