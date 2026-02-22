"""Pydantic schemas for Dataset Export endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DatasetExportRequest(BaseModel):
    server_id: int
    format: str = "jsonl"
    min_quality: float = 0.7
    language: str | None = None


class DatasetExportResponse(BaseModel):
    id: int
    server_id: int
    format: str
    record_count: int
    file_size_bytes: int
    c2pa_manifest_hash: str | None = None
    consent_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    items: list[DatasetExportResponse]
    total: int
