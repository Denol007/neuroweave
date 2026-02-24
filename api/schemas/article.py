"""Pydantic schemas for Article endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    id: int
    article_type: str = "troubleshooting"
    source_type: str = "discord"
    source_url: str | None = None
    symptom: str
    diagnosis: str
    solution: str
    code_snippet: str | None = None
    language: str
    framework: str | None = None
    tags: list[str]
    confidence: float
    thread_summary: str
    quality_score: float
    is_visible: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArticleBrief(BaseModel):
    """Compact article representation for lists."""

    id: int
    article_type: str = "troubleshooting"
    source_type: str = "discord"
    thread_summary: str
    language: str
    framework: str | None = None
    tags: list[str]
    confidence: float
    quality_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    items: list[ArticleBrief]
    total: int
    page: int
    page_size: int


class SearchResult(BaseModel):
    """Search result with relevance score."""

    article: ArticleBrief
    score: float = Field(description="Combined relevance score (0.0-1.0)")


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total: int
