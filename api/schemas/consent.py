"""Pydantic schemas for Consent endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConsentCreate(BaseModel):
    user_hash: str
    server_id: int
    kb_consent: bool = False
    ai_consent: bool = False


class ConsentResponse(BaseModel):
    id: int
    user_hash: str
    server_id: int
    kb_consent: bool
    ai_consent: bool
    granted_at: datetime
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConsentStatus(BaseModel):
    """Summary of user's consent across servers."""

    user_hash: str
    consents: list[ConsentResponse]
