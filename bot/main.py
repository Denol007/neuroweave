"""NeuroWeave Discord Bot entry point.

Usage:
    python -m bot.main

Requires:
    DISCORD_BOT_TOKEN — bot token from Discord Developer Portal
    REDIS_URL — Redis connection for stream publishing

Intents required:
    - message_content (privileged)
    - guilds
    - guild_messages
"""

from __future__ import annotations

import asyncio
import os
import sys

import discord
import structlog
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()  # Load .env file from project root

from bot.channel_sync import fetch_monitored_channels_api
from bot.stream_producer import StreamProducer

logger = structlog.get_logger()

CHANNEL_REFRESH_MINUTES = 5


def create_bot() -> commands.Bot:
    """Create and configure the Discord bot."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    bot = commands.Bot(
        command_prefix="!nw ",
        intents=intents,
        help_command=None,
    )

    return bot


async def _sync_channels(bot: commands.Bot):
    """Fetch monitored channels from DB and update the listener cog."""
    channel_ids = await fetch_monitored_channels_api()

    # Find the listener cog and update its channel set
    from bot.cogs.listener import MessageListener

    listener = bot.get_cog("MessageListener")
    if listener and isinstance(listener, MessageListener):
        listener.set_monitored_channels(channel_ids)
    else:
        logger.warning("listener_cog_not_found", available_cogs=list(bot.cogs.keys()))


async def main():
    bot = create_bot()

    # Read config
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    if not token:
        logger.error("DISCORD_BOT_TOKEN not set")
        sys.exit(1)

    # Initialize Redis Stream producer
    producer = StreamProducer(redis_url)
    await producer.connect()
    bot.stream_producer = producer

    # Periodic channel refresh task
    @tasks.loop(minutes=CHANNEL_REFRESH_MINUTES)
    async def refresh_channels():
        await _sync_channels(bot)

    @bot.event
    async def on_ready():
        logger.info("bot_ready", user=str(bot.user), guilds=len(bot.guilds))

        # Initial channel sync
        await _sync_channels(bot)

        # Start periodic refresh
        if not refresh_channels.is_running():
            refresh_channels.start()

        # Sync slash commands
        try:
            synced = await bot.tree.sync()
            logger.info("commands_synced", count=len(synced))
        except Exception as e:
            logger.error("command_sync_failed", error=str(e))

    # Load cogs
    await bot.load_extension("bot.cogs.listener")

    try:
        await bot.load_extension("bot.cogs.consent")
    except commands.ExtensionNotFound:
        logger.info("consent_cog_not_found_skipping")
    except Exception as e:
        logger.warning("consent_cog_load_failed", error=str(e))

    try:
        await bot.load_extension("bot.cogs.search")
    except commands.ExtensionNotFound:
        logger.info("search_cog_not_found_skipping")
    except Exception as e:
        logger.warning("search_cog_load_failed", error=str(e))

    # Run
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        pass
    finally:
        refresh_channels.cancel()
        await producer.close()
        await bot.close()
        logger.info("bot_shutdown")


if __name__ == "__main__":
    asyncio.run(main())
