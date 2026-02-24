"""Celery task: process a batch of messages through the extraction pipeline.

Triggered by Redis Stream consumer (Discord) or GitHub fetcher.

Flow:
    messages → consent check → PII anonymize → LangGraph pipeline → store_article
"""

from __future__ import annotations

import time

import structlog

from api.celery_app import app

logger = structlog.get_logger()


@app.task(
    bind=True,
    name="api.tasks.process_messages.process_message_batch",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_message_batch(
    self,
    channel_id: str,
    server_id: str,
    messages: list[dict],
    source_type: str = "discord",
):
    """Process a batch of messages through the extraction pipeline.

    Args:
        channel_id: External channel ID (Discord channel or GitHub category).
        server_id: External server ID (Discord guild or owner/repo).
        messages: List of message dicts with keys:
            id, author_hash, content, timestamp, reply_to, mentions
        source_type: Source platform — "discord", "github", "discourse".
    """
    logger.info(
        "processing_batch",
        channel=channel_id,
        server=server_id,
        source=source_type,
        count=len(messages),
    )

    start = time.monotonic()

    try:
        from api.services.anonymizer import anonymize
        from api.services.consent_checker import filter_consented_messages
        from api.services.extraction.graph import build_graph

        # GDPR: consent check (skip for public sources like GitHub)
        if source_type == "discord":
            messages, excluded = filter_consented_messages(messages, server_id)
            if not messages:
                logger.info("batch_skipped_no_consent", channel=channel_id, excluded=excluded)
                return {"classification": "SKIPPED", "reason": "no_consented_messages"}
        # GitHub/Discourse: public data, no consent needed

        # PII anonymization
        for msg in messages:
            result = anonymize(msg.get("content", ""))
            msg["content"] = result.text

        graph = build_graph(use_mongodb=True)

        initial_state = {
            "messages": messages,
            "threads": [],
            "source_type": source_type,
            "skip_disentangle": source_type != "discord",
            "classification": "",
            "article_type": "",
            "evaluation": None,
            "compiled_article": None,
            "quality_score": 0.0,
            "retry_count": 0,
            "current_thread_idx": 0,
            "server_id": server_id,
            "channel_id": channel_id,
            "error": None,
        }

        config = {
            "configurable": {
                "thread_id": f"batch_{source_type}_{channel_id}_{int(time.time())}",
            }
        }

        result = graph.invoke(initial_state, config=config)

        duration_ms = (time.monotonic() - start) * 1000

        classification = result.get("classification", "")
        quality = result.get("quality_score", 0)

        logger.info(
            "batch_complete",
            channel=channel_id,
            source=source_type,
            classification=classification,
            quality=quality,
            duration_ms=round(duration_ms),
        )

        # Store successful articles
        if quality >= 0.7 and result.get("compiled_article"):
            from api.tasks.generate_article import store_article

            store_article.delay(
                article_data=result["compiled_article"],
                channel_id=channel_id,
                server_id=server_id,
                quality_score=quality,
                source_type=source_type,
            )

        return {
            "classification": classification,
            "quality_score": quality,
            "duration_ms": round(duration_ms),
        }

    except Exception as exc:
        logger.error("batch_failed", channel=channel_id, error=str(exc))
        raise self.retry(exc=exc)
