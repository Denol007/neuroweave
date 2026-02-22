"""Redis Streams producer for Discord messages.

Publishes messages to per-channel streams. When a batch threshold
is reached (50 messages or 5-minute window), triggers a Celery task
for extraction pipeline processing.

Stream key format: messages:{server_id}:{channel_id}
Consumer group: extraction_workers
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

BATCH_SIZE = 50
BATCH_WINDOW_SECONDS = 300  # 5 minutes


class StreamProducer:
    """Publishes Discord messages to Redis Streams and triggers batch processing."""

    def __init__(self, redis_url: str):
        self.redis: aioredis.Redis | None = None
        self.redis_url = redis_url
        self._batch_timers: dict[str, float] = {}

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("stream_producer_connected")

    async def close(self):
        if self.redis:
            await self.redis.aclose()

    @staticmethod
    def hash_user_id(discord_user_id: int | str) -> str:
        """SHA-256 hash a Discord user ID. Real IDs never leave the bot."""
        return hashlib.sha256(str(discord_user_id).encode()).hexdigest()

    def _stream_key(self, server_id: str, channel_id: str) -> str:
        return f"messages:{server_id}:{channel_id}"

    def _counter_key(self, server_id: str, channel_id: str) -> str:
        return f"batch_counter:{server_id}:{channel_id}"

    async def publish(
        self,
        server_id: str,
        channel_id: str,
        message_id: str,
        author_id: int | str,
        content: str,
        timestamp: datetime,
        reply_to: str | None = None,
        mentions: list[str] | None = None,
    ) -> bool:
        """Publish a message to the Redis Stream.

        Returns True if batch threshold was reached and processing was triggered.
        """
        if not self.redis:
            raise RuntimeError("StreamProducer not connected. Call connect() first.")

        stream_key = self._stream_key(server_id, channel_id)
        counter_key = self._counter_key(server_id, channel_id)

        # Hash the author ID — real Discord IDs never leave the bot
        author_hash = self.hash_user_id(author_id)

        # Hash mention IDs too
        mention_hashes = [self.hash_user_id(m) for m in (mentions or [])]

        # Publish to stream
        await self.redis.xadd(stream_key, {
            "id": message_id,
            "author_hash": author_hash,
            "content": content,
            "timestamp": timestamp.isoformat(),
            "reply_to": reply_to or "",
            "mentions": ",".join(mention_hashes),
            "has_code": "1" if "```" in content else "0",
        })

        # Increment batch counter
        count = await self.redis.incr(counter_key)

        # Initialize timer on first message
        timer_key = f"{server_id}:{channel_id}"
        if count == 1:
            self._batch_timers[timer_key] = time.time()

        # Check batch trigger conditions
        time_elapsed = time.time() - self._batch_timers.get(timer_key, time.time())
        should_trigger = count >= BATCH_SIZE or time_elapsed >= BATCH_WINDOW_SECONDS

        if should_trigger:
            await self._trigger_batch(server_id, channel_id, stream_key, counter_key)
            self._batch_timers.pop(timer_key, None)
            return True

        return False

    async def _trigger_batch(
        self,
        server_id: str,
        channel_id: str,
        stream_key: str,
        counter_key: str,
    ):
        """Read messages from stream and dispatch Celery task."""
        if not self.redis:
            return

        # Read all pending messages from stream
        raw_messages = await self.redis.xrange(stream_key)

        if not raw_messages:
            return

        # Convert to message dicts for Celery
        messages = []
        message_ids = []
        for msg_id, data in raw_messages:
            message_ids.append(msg_id)
            mentions = [m for m in data.get("mentions", "").split(",") if m]
            messages.append({
                "id": data.get("id", ""),
                "author_hash": data.get("author_hash", ""),
                "content": data.get("content", ""),
                "timestamp": data.get("timestamp", ""),
                "reply_to": data.get("reply_to") or None,
                "mentions": mentions,
            })

        # Dispatch Celery task
        try:
            from api.tasks.process_messages import process_message_batch

            process_message_batch.delay(
                channel_id=channel_id,
                server_id=server_id,
                messages=messages,
            )
            logger.info(
                "batch_dispatched",
                server=server_id,
                channel=channel_id,
                count=len(messages),
            )
        except Exception as e:
            logger.error("batch_dispatch_failed", error=str(e))
            return  # Don't delete messages if dispatch failed

        # Clean up: delete processed messages from stream
        if message_ids:
            await self.redis.xdel(stream_key, *message_ids)

        # Reset counter
        await self.redis.delete(counter_key)
