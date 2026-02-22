"""Tests for the Redis Stream Producer."""

from __future__ import annotations

from datetime import datetime

import pytest

from bot.stream_producer import BATCH_SIZE, BATCH_WINDOW_SECONDS, StreamProducer


class TestStreamProducer:
    def test_hash_user_id_deterministic(self):
        h1 = StreamProducer.hash_user_id(123456789)
        h2 = StreamProducer.hash_user_id(123456789)
        assert h1 == h2

    def test_hash_user_id_unique(self):
        h1 = StreamProducer.hash_user_id(123)
        h2 = StreamProducer.hash_user_id(456)
        assert h1 != h2

    def test_hash_user_id_sha256(self):
        h = StreamProducer.hash_user_id(123)
        assert len(h) == 64  # SHA-256 hex

    def test_hash_accepts_int_and_str(self):
        h1 = StreamProducer.hash_user_id(123)
        h2 = StreamProducer.hash_user_id("123")
        assert h1 == h2

    @pytest.mark.asyncio
    async def test_publish_message(self, mock_redis):
        producer = StreamProducer("redis://localhost")
        producer.redis = mock_redis

        triggered = await producer.publish(
            server_id="srv1",
            channel_id="ch1",
            message_id="msg1",
            author_id=12345,
            content="test message",
            timestamp=datetime(2026, 2, 22, 14, 0),
        )

        assert triggered is False  # First message, batch not reached
        mock_redis.xadd.assert_called_once()
        mock_redis.incr.assert_called_once()

        # Verify XADD args
        call_args = mock_redis.xadd.call_args
        stream_key = call_args[0][0]
        data = call_args[0][1]
        assert stream_key == "messages:srv1:ch1"
        assert data["author_hash"] == StreamProducer.hash_user_id(12345)
        assert data["content"] == "test message"
        assert data["has_code"] == "0"

    @pytest.mark.asyncio
    async def test_publish_detects_code(self, mock_redis):
        producer = StreamProducer("redis://localhost")
        producer.redis = mock_redis

        await producer.publish(
            server_id="srv1", channel_id="ch1", message_id="msg1",
            author_id=1, content="```python\nprint('hello')\n```",
            timestamp=datetime(2026, 2, 22, 14, 0),
        )

        data = mock_redis.xadd.call_args[0][1]
        assert data["has_code"] == "1"

    @pytest.mark.asyncio
    async def test_publish_hashes_mentions(self, mock_redis):
        producer = StreamProducer("redis://localhost")
        producer.redis = mock_redis

        await producer.publish(
            server_id="srv1", channel_id="ch1", message_id="msg1",
            author_id=1, content="@user help",
            timestamp=datetime(2026, 2, 22, 14, 0),
            mentions=["111", "222"],
        )

        data = mock_redis.xadd.call_args[0][1]
        # Mentions should be hashed
        parts = data["mentions"].split(",")
        assert len(parts) == 2
        assert all(len(p) == 64 for p in parts)  # SHA-256

    @pytest.mark.asyncio
    async def test_batch_triggers_at_threshold(self, mock_redis):
        from unittest.mock import patch, MagicMock

        producer = StreamProducer("redis://localhost")
        producer.redis = mock_redis
        mock_redis.incr.return_value = BATCH_SIZE  # Hit threshold
        mock_redis.xrange.return_value = [
            ("1-0", {"id": "m1", "author_hash": "h1", "content": "c1", "timestamp": "t1", "reply_to": "", "mentions": ""}),
        ]

        # Mock Celery task to avoid real Redis connection
        mock_task = MagicMock()
        with patch("bot.stream_producer.process_message_batch", mock_task, create=True):
            with patch("api.tasks.process_messages.process_message_batch") as mock_celery:
                mock_celery.delay = MagicMock()

                triggered = await producer.publish(
                    server_id="srv1", channel_id="ch1", message_id="msg50",
                    author_id=1, content="trigger",
                    timestamp=datetime(2026, 2, 22, 14, 0),
                )

        assert triggered is True
        mock_redis.xrange.assert_called_once()
        mock_redis.xdel.assert_called_once()
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_connected_raises(self):
        producer = StreamProducer("redis://localhost")
        # No connect() called
        with pytest.raises(RuntimeError, match="not connected"):
            await producer.publish(
                server_id="s", channel_id="c", message_id="m",
                author_id=1, content="x",
                timestamp=datetime(2026, 2, 22, 14, 0),
            )

    def test_constants(self):
        assert BATCH_SIZE == 50
        assert BATCH_WINDOW_SECONDS == 300
