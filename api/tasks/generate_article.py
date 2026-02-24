"""Celery task: store a compiled article in PostgreSQL with pgvector embedding.

Called by process_message_batch when a thread passes the quality gate.
Generates a 384-dim embedding for the article summary and stores
everything in the articles table.
"""

from __future__ import annotations

import structlog

from api.celery_app import app

logger = structlog.get_logger()


@app.task(
    name="api.tasks.generate_article.store_article",
    max_retries=3,
    default_retry_delay=30,
)
def store_article(
    article_data: dict,
    channel_id: str,
    server_id: str,
    quality_score: float,
    source_type: str = "discord",
):
    """Store a compiled article in PostgreSQL with embedding.

    Args:
        article_data: CompiledArticle dict from the compiler node.
        channel_id: External channel ID (Discord channel ID or GitHub category node_id).
        server_id: External server ID (Discord guild ID or owner/repo).
        quality_score: Quality gate score.
        source_type: Source platform — "discord", "github", "discourse".
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from api.config import settings
    from api.models.article import Article
    from api.models.channel import Channel
    from api.models.thread import Thread, ThreadStatus

    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
    engine = create_engine(sync_url)

    try:
        with Session(engine) as session:
            # Find channel by external_id (source-agnostic)
            channel = session.execute(
                select(Channel).where(Channel.external_id == channel_id)
            ).scalar_one_or_none()

            if not channel:
                logger.warning("channel_not_found", channel_id=channel_id, source=source_type)
                return

            # Create thread record
            thread = Thread(
                channel_id=channel.id,
                status=ThreadStatus.RESOLVED,
                cluster_metadata={"source": source_type},
            )
            session.add(thread)
            session.flush()

            # Generate embedding for semantic search
            embedding = None
            try:
                from api.services.embeddings import encode

                summary_text = (
                    f"{article_data['thread_summary']} "
                    f"{article_data['symptom']} "
                    f"{article_data['solution']}"
                )
                embedding = encode(summary_text).tolist()
            except Exception as e:
                logger.warning("embedding_generation_failed", error=str(e))

            # Create article
            article = Article(
                thread_id=thread.id,
                article_type=article_data.get("article_type", "troubleshooting"),
                source_type=source_type,
                source_url=article_data.get("source_url"),
                symptom=article_data["symptom"],
                diagnosis=article_data["diagnosis"],
                solution=article_data["solution"],
                code_snippet=article_data.get("code_snippet"),
                language=article_data.get("language", "general"),
                framework=article_data.get("framework"),
                tags=article_data.get("tags", []),
                confidence=article_data["confidence"],
                thread_summary=article_data["thread_summary"],
                quality_score=quality_score,
                embedding=embedding,
            )
            session.add(article)
            session.commit()

            logger.info(
                "article_stored",
                article_id=article.id,
                source=source_type,
                article_type=article_data.get("article_type", "troubleshooting"),
                summary=article_data["thread_summary"][:80],
                quality=quality_score,
            )

    except Exception as e:
        logger.error("article_store_failed", error=str(e))
        raise
    finally:
        engine.dispose()
