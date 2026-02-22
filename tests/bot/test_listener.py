"""Tests for the MessageListener cog."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.cogs.listener import MessageListener
from bot.stream_producer import StreamProducer


class TestMessageListener:
    def setup_method(self):
        self.bot = MagicMock()
        self.producer = MagicMock(spec=StreamProducer)
        self.producer.publish = AsyncMock(return_value=False)
        self.listener = MessageListener(self.bot, self.producer)
        self.listener.set_monitored_channels({"111222333"})

    @pytest.mark.asyncio
    async def test_ignores_bot_messages(self, mock_message):
        mock_message.author.bot = True
        await self.listener.on_message(mock_message)
        self.producer.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_dms(self, mock_message):
        mock_message.guild = None
        await self.listener.on_message(mock_message)
        self.producer.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_unmonitored_channels(self, mock_message):
        mock_message.channel.id = 999999999  # Not in monitored set
        await self.listener.on_message(mock_message)
        self.producer.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_publishes_monitored_message(self, mock_message):
        await self.listener.on_message(mock_message)
        self.producer.publish.assert_called_once()

        call_kwargs = self.producer.publish.call_args
        assert call_kwargs.kwargs["server_id"] == str(mock_message.guild.id)
        assert call_kwargs.kwargs["channel_id"] == str(mock_message.channel.id)
        assert call_kwargs.kwargs["author_id"] == mock_message.author.id
        assert call_kwargs.kwargs["content"] == mock_message.content

    @pytest.mark.asyncio
    async def test_extracts_reply_to(self, mock_message):
        mock_message.reference = MagicMock()
        mock_message.reference.message_id = 777888999
        await self.listener.on_message(mock_message)

        call_kwargs = self.producer.publish.call_args
        assert call_kwargs.kwargs["reply_to"] == "777888999"

    @pytest.mark.asyncio
    async def test_extracts_mentions(self, mock_message):
        mention1 = MagicMock()
        mention1.id = 111
        mention2 = MagicMock()
        mention2.id = 222
        mock_message.mentions = [mention1, mention2]

        await self.listener.on_message(mock_message)

        call_kwargs = self.producer.publish.call_args
        assert call_kwargs.kwargs["mentions"] == ["111", "222"]

    @pytest.mark.asyncio
    async def test_handles_publish_error(self, mock_message):
        self.producer.publish.side_effect = Exception("Redis down")
        # Should not raise — error is caught internally
        await self.listener.on_message(mock_message)

    def test_set_monitored_channels(self):
        self.listener.set_monitored_channels({"aaa", "bbb", "ccc"})
        assert self.listener._monitored_channels == {"aaa", "bbb", "ccc"}
