"""Message Listener cog — captures messages from monitored channels.

Also handles on_guild_join: when bot is added to a new server,
automatically registers the server and all text channels in the DB.
"""

from __future__ import annotations

import os

import discord
import structlog
from discord.ext import commands
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from bot.stream_producer import StreamProducer

logger = structlog.get_logger()


def _get_sync_engine():
    """Get a sync DB engine for guild registration."""
    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://neuroweave:neuroweave@localhost:5432/neuroweave",
    )
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return create_engine(sync_url, pool_pre_ping=True)


class MessageListener(commands.Cog):
    """Listens to messages in monitored channels and publishes to Redis Streams."""

    def __init__(self, bot: commands.Bot, producer: StreamProducer):
        self.bot = bot
        self.producer = producer
        self._monitored_channels: set[str] = set()

    def set_monitored_channels(self, channel_ids: set[str]):
        """Update the set of monitored channel IDs."""
        self._monitored_channels = channel_ids
        logger.info("monitored_channels_updated", count=len(channel_ids))

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Auto-register server and text channels when bot is added to a new server."""
        logger.info("guild_joined", guild=guild.name, guild_id=guild.id, channels=len(guild.text_channels))

        try:
            engine = _get_sync_engine()
            with Session(engine) as db:
                # Check if server already registered
                existing = db.execute(
                    text("SELECT id FROM servers WHERE discord_id = :did"),
                    {"did": str(guild.id)},
                ).fetchone()

                if existing:
                    server_id = existing[0]
                    logger.info("guild_already_registered", guild=guild.name, server_id=server_id)
                else:
                    # Insert new server
                    db.execute(
                        text("""
                            INSERT INTO servers (discord_id, name, icon_url, member_count, settings, plan, created_at, updated_at)
                            VALUES (:did, :name, :icon, :members, '{}', 'FREE', now(), now())
                        """),
                        {
                            "did": str(guild.id),
                            "name": guild.name,
                            "icon": str(guild.icon.url) if guild.icon else None,
                            "members": guild.member_count or 0,
                        },
                    )
                    db.flush()
                    row = db.execute(
                        text("SELECT id FROM servers WHERE discord_id = :did"),
                        {"did": str(guild.id)},
                    ).fetchone()
                    server_id = row[0]
                    logger.info("guild_registered", guild=guild.name, server_id=server_id)

                # Register all text channels (monitored by default)
                registered = 0
                for channel in guild.text_channels:
                    existing_ch = db.execute(
                        text("SELECT id FROM channels WHERE discord_id = :did"),
                        {"did": str(channel.id)},
                    ).fetchone()

                    if not existing_ch:
                        db.execute(
                            text("""
                                INSERT INTO channels (server_id, discord_id, name, is_monitored, created_at, updated_at)
                                VALUES (:sid, :did, :name, true, now(), now())
                            """),
                            {"sid": server_id, "did": str(channel.id), "name": channel.name},
                        )
                        registered += 1

                db.commit()
                logger.info("guild_channels_registered", guild=guild.name, registered=registered, total=len(guild.text_channels))

            engine.dispose()

            # Refresh monitored channels immediately
            from bot.channel_sync import fetch_monitored_channels_api

            new_channels = await fetch_monitored_channels_api()
            self.set_monitored_channels(new_channels)

        except Exception as e:
            logger.error("guild_join_registration_failed", guild=guild.name, error=str(e))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Log when bot is removed from a server."""
        logger.info("guild_removed", guild=guild.name, guild_id=guild.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming messages."""
        if message.author.bot:
            return
        if not message.guild:
            return

        channel_id = str(message.channel.id)
        if channel_id not in self._monitored_channels:
            return

        server_id = str(message.guild.id)

        reply_to = None
        if message.reference and message.reference.message_id:
            reply_to = str(message.reference.message_id)

        mentions = [str(u.id) for u in message.mentions]

        try:
            batch_triggered = await self.producer.publish(
                server_id=server_id,
                channel_id=channel_id,
                message_id=str(message.id),
                author_id=message.author.id,
                content=message.content,
                timestamp=message.created_at,
                reply_to=reply_to,
                mentions=mentions,
            )

            if batch_triggered:
                logger.info("batch_triggered", server=server_id, channel=channel_id)
        except Exception as e:
            logger.error("message_publish_failed", channel=channel_id, error=str(e))


async def setup(bot: commands.Bot):
    """Called by bot.load_extension(). Producer must be set on bot instance."""
    producer = getattr(bot, "stream_producer", None)
    if producer is None:
        raise RuntimeError("bot.stream_producer must be set before loading listener cog")
    await bot.add_cog(MessageListener(bot, producer))
