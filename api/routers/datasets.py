"""Datasets router — export, list, download.

Endpoints:
  POST /api/datasets/export       — trigger dataset export (Celery task)
  GET  /api/datasets              — list exports
  GET  /api/datasets/{id}/download — download JSONL file
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from api.deps import DB, CurrentUser
from api.models.dataset_export import DatasetExport
from api.schemas.dataset import DatasetExportRequest, DatasetExportResponse, DatasetListResponse

logger = structlog.get_logger()

router = APIRouter()


@router.post("/datasets/export", response_model=DatasetExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_export(body: DatasetExportRequest, db: DB, user: CurrentUser):
    """Trigger a dataset export. Creates a record and dispatches a Celery task.

    The actual export (query articles, package JSONL, C2PA sign) happens
    asynchronously in a Celery worker.
    """
    # Create export record in "pending" state
    export = DatasetExport(
        server_id=body.server_id,
        format=body.format,
        record_count=0,
        file_path="",  # Filled by Celery task
        file_size_bytes=0,
        consent_verified=False,
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)

    # Dispatch Celery task (import here to avoid circular deps)
    try:
        from api.tasks.export_dataset import export_dataset

        export_dataset.delay(
            export_id=export.id,
            server_id=body.server_id,
            format=body.format,
            min_quality=body.min_quality,
            language=body.language,
        )
        logger.info("export_triggered", export_id=export.id, server_id=body.server_id)
    except Exception as e:
        logger.warning("celery_dispatch_failed", error=str(e))
        # Export record is still created; task can be retried manually

    return DatasetExportResponse.model_validate(export)


@router.get("/datasets", response_model=DatasetListResponse)
async def list_exports(
    db: DB,
    server_id: int | None = None,
):
    """List dataset exports, optionally filtered by server."""
    query = select(DatasetExport).order_by(DatasetExport.created_at.desc())
    if server_id:
        query = query.where(DatasetExport.server_id == server_id)

    result = await db.execute(query)
    exports = result.scalars().all()

    return DatasetListResponse(
        items=[DatasetExportResponse.model_validate(e) for e in exports],
        total=len(exports),
    )


@router.get("/datasets/{export_id}/download")
async def download_export(export_id: int, db: DB):
    """Download a completed dataset export file."""
    result = await db.execute(
        select(DatasetExport).where(DatasetExport.id == export_id)
    )
    export = result.scalar_one_or_none()

    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    if not export.file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export is still processing",
        )

    return FileResponse(
        path=export.file_path,
        filename=f"neuroweave_export_{export.id}.{export.format}",
        media_type="application/octet-stream",
    )
