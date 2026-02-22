"""Bot test fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_redis():
    """Mock Redis client for StreamProducer."""
    redis = AsyncMock()
    redis.xadd = AsyncMock(return_value="1234-0")
    redis.incr = AsyncMock(return_value=1)
    redis.xrange = AsyncMock(return_value=[])
    redis.xdel = AsyncMock()
    redis.delete = AsyncMock()
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def mock_message():
    """Mock Discord message."""
    msg = MagicMock()
    msg.author.bot = False
    msg.author.id = 123456789
    msg.guild = MagicMock()
    msg.guild.id = 987654321
    msg.channel = MagicMock()
    msg.channel.id = 111222333
    msg.id = 444555666
    msg.content = "How do I fix this error?\n```\nTypeError: x is not a function\n```"
    msg.created_at = MagicMock()
    msg.created_at.isoformat = MagicMock(return_value="2026-02-22T14:00:00")
    msg.reference = None
    msg.mentions = []
    return msg
