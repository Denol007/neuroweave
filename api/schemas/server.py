"""Pydantic schemas for Server endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ServerResponse(BaseModel):
    id: int
    source_type: str = "discord"
    external_id: str = ""
    discord_id: str | None = None
    name: str
    icon_url: str | None = None
    source_url: str | None = None
    member_count: int = 0
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ServerStats(BaseModel):
    server_id: int
    server_name: str
    source_type: str = "discord"
    total_articles: int
    total_threads: int
    total_messages: int
    noise_filtered: int
    avg_quality_score: float
    top_languages: list[dict]
    top_tags: list[dict]


class ChannelUpdate(BaseModel):
    channel_discord_ids: list[str]
    is_monitored: bool = True
