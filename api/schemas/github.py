"""Pydantic schemas for GitHub Repo endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GitHubRepoCreate(BaseModel):
    owner: str
    repo: str
    category_filters: list[str] | None = None


class GitHubRepoResponse(BaseModel):
    id: int
    external_id: str
    name: str
    source_type: str
    source_url: str | None = None
    plan: str
    categories: list[dict] = []
    last_fetched_at: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GitHubSyncResponse(BaseModel):
    server_id: int
    status: str = "dispatched"
