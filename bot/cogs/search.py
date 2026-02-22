"""/nw-ask slash command — search the knowledge base from Discord.

Queries the NeuroWeave API and returns results as a rich Discord embed
with code blocks and article links. All responses are ephemeral.
"""

from __future__ import annotations

import os

import discord
import httpx
import structlog
from discord import app_commands
from discord.ext import commands

from bot.cogs.consent import _resolve_server_id

logger = structlog.get_logger()

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
WEB_BASE = os.environ.get("WEB_BASE_URL", "http://localhost:3000")


class SearchCog(commands.Cog):
    """Knowledge base search slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="nw-ask", description="Search the NeuroWeave knowledge base")
    @app_commands.describe(query="What are you looking for?", language="Filter by language (optional)")
    async def nw_ask(
        self,
        interaction: discord.Interaction,
        query: str,
        language: str | None = None,
    ):
        """Search the knowledge base and return top results."""
        await interaction.response.defer(ephemeral=True)

        # Build search params
        params: dict = {"q": query, "limit": 5}
        if language:
            params["language"] = language
        if interaction.guild:
            # Resolve Discord guild ID → internal DB server ID
            internal_id = await _resolve_server_id(interaction.guild.id)
            if internal_id:
                params["server"] = str(internal_id)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{API_BASE}/api/search", params=params)

            if resp.status_code != 200:
                await interaction.followup.send(
                    "Search failed. The API might be temporarily unavailable.",
                    ephemeral=True,
                )
                return

            data = resp.json()
            results = data.get("results", [])

            if not results:
                embed = discord.Embed(
                    title="\U0001f50d No results found",
                    description=f'No articles match **"{query}"**.\nTry a different search term.',
                    color=0x71717A,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Build results embed
            embed = discord.Embed(
                title=f'\U0001f50d Results for "{query}"',
                description=f"Found **{data.get('total', len(results))}** articles",
                color=0x6366F1,
            )

            for i, result in enumerate(results[:5], 1):
                article = result.get("article", {})
                score = result.get("score", 0)
                summary = article.get("thread_summary", "No summary")
                lang = article.get("language", "?")
                tags = article.get("tags", [])
                article_id = article.get("id", 0)
                confidence = article.get("confidence", 0)

                tag_str = " ".join(f"`{t}`" for t in tags[:4])
                article_url = f"{WEB_BASE}/articles/{article_id}"

                embed.add_field(
                    name=f"{i}. {summary}",
                    value=(
                        f"**Language:** `{lang}` | **Score:** {score:.2f} | "
                        f"**Confidence:** {confidence:.0%}\n"
                        f"{tag_str}\n"
                        f"[\U0001f517 View full article]({article_url})"
                    ),
                    inline=False,
                )

            embed.set_footer(text="NeuroWeave Knowledge Base | /nw-ask <query>")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except httpx.TimeoutException:
            await interaction.followup.send("Search timed out. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error("search_command_failed", error=str(e))
            await interaction.followup.send("Something went wrong. Please try again.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SearchCog(bot))
