"""Celery task: export articles as JSONL dataset with C2PA signing.

Triggered by POST /api/datasets/export. Queries articles matching
the criteria, packages them as JSONL, creates a C2PA manifest,
and updates the export record.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import structlog

from api.celery_app import app

logger = structlog.get_logger()

EXPORT_DIR = Path(os.environ.get("EXPORT_DIR", "/tmp/neuroweave_exports"))


@app.task(
    name="api.tasks.export_dataset.export_dataset",
    max_retries=2,
    default_retry_delay=120,
)
def export_dataset(
    export_id: int,
    server_id: int,
    format: str = "jsonl",
    min_quality: float = 0.7,
    language: str | None = None,
):
    """Export articles as a JSONL dataset with C2PA signing.

    Args:
        export_id: DatasetExport record ID to update.
        server_id: Server to export articles from.
        format: Export format (jsonl).
        min_quality: Minimum quality score filter.
        language: Optional language filter.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from api.config import settings
    from api.models.article import Article
    from api.models.channel import Channel
    from api.models.dataset_export import DatasetExport
    from api.models.thread import Thread
    from api.services.c2pa_signer import compute_content_hash, create_manifest, sign_manifest

    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
    engine = create_engine(sync_url)

    try:
        with Session(engine) as session:
            # Query articles
            query = (
                select(Article)
                .join(Thread, Thread.id == Article.thread_id)
                .join(Channel, Channel.id == Thread.channel_id)
                .where(Channel.server_id == server_id)
                .where(Article.quality_score >= min_quality)
                .where(Article.is_visible.is_(True))
            )
            if language:
                query = query.where(Article.language == language)

            articles = session.execute(query).scalars().all()

            if not articles:
                logger.warning("export_no_articles", export_id=export_id)
                return

            # Build JSONL content
            lines = []
            for article in articles:
                record = {
                    "id": f"art_{article.id}",
                    "source": f"{article.source_type}:{server_id}",
                    "knowledge": {
                        "symptom": article.symptom,
                        "diagnosis": article.diagnosis,
                        "solution": article.solution,
                        "code_snippet": article.code_snippet,
                        "language": article.language,
                        "framework": article.framework,
                        "tags": article.tags,
                        "confidence": article.confidence,
                        "thread_summary": article.thread_summary,
                    },
                    "metadata": {
                        "quality_score": article.quality_score,
                        "created_at": article.created_at.isoformat() if article.created_at else None,
                    },
                }
                lines.append(json.dumps(record, ensure_ascii=False))

            content = "\n".join(lines)
            content_bytes = content.encode("utf-8")

            # Write file
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            file_path = EXPORT_DIR / f"export_{export_id}.jsonl"
            file_path.write_bytes(content_bytes)

            # C2PA signing
            content_hash = compute_content_hash(content_bytes)
            manifest = create_manifest(
                export_id=export_id,
                record_count=len(articles),
                content_hash=content_hash,
                source_server=str(server_id),
            )
            manifest_hash = sign_manifest(manifest)

            # Write manifest alongside
            manifest_path = EXPORT_DIR / f"export_{export_id}.c2pa.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))

            # Update export record
            export = session.execute(
                select(DatasetExport).where(DatasetExport.id == export_id)
            ).scalar_one_or_none()

            if export:
                export.record_count = len(articles)
                export.file_path = str(file_path)
                export.file_size_bytes = len(content_bytes)
                export.c2pa_manifest_hash = manifest_hash
                export.consent_verified = True
                session.commit()

            logger.info(
                "export_complete",
                export_id=export_id,
                records=len(articles),
                size_bytes=len(content_bytes),
                manifest_hash=manifest_hash[:30],
            )

    except Exception as e:
        logger.error("export_failed", export_id=export_id, error=str(e))
        raise
    finally:
        engine.dispose()
