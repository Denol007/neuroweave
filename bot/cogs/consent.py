"""/privacy slash command — GDPR consent management via Discord UI.

Shows an ephemeral message with buttons for:
  - Knowledge Base consent (allow messages for internal FAQ)
  - AI Training consent (allow anonymized data licensing)
  - Revoke All (withdraw all consents)

All interactions are ephemeral (only visible to the invoking user).
"""

from __future__ import annotations

import hashlib
import os

import discord
import httpx
import structlog
from discord import app_commands
from discord.ext import commands

logger = structlog.get_logger()

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _hash_user_id(user_id: int) -> str:
    return hashlib.sha256(str(user_id).encode()).hexdigest()


async def _resolve_server_id(guild_discord_id: int) -> int | None:
    """Resolve Discord guild ID → internal DB server ID via API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE}/api/servers")
            if resp.status_code == 200:
                for server in resp.json():
                    if server.get("discord_id") == str(guild_discord_id):
                        return server["id"]
    except Exception as e:
        logger.error("resolve_server_id_failed", error=str(e))
    return None


class ConsentView(discord.ui.View):
    """Interactive consent buttons."""

    def __init__(self, user_hash: str, server_id: int):
        super().__init__(timeout=300)
        self.user_hash = user_hash
        self.server_id = server_id  # Internal DB server ID (not Discord snowflake)

    @discord.ui.button(label="Allow Knowledge Base", style=discord.ButtonStyle.green, emoji="\U0001f4da")
    async def kb_consent(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_consent(interaction, kb=True, ai=False, label="Knowledge Base")

    @discord.ui.button(label="Allow AI Training", style=discord.ButtonStyle.blurple, emoji="\U0001f916")
    async def ai_consent(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_consent(interaction, kb=False, ai=True, label="AI Training Data")

    @discord.ui.button(label="Allow Both", style=discord.ButtonStyle.green, emoji="\u2705")
    async def both_consent(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_consent(interaction, kb=True, ai=True, label="Knowledge Base + AI Training")

    @discord.ui.button(label="Revoke All", style=discord.ButtonStyle.red, emoji="\u274c")
    async def revoke(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{API_BASE}/api/consent/{self.user_hash}",
                    params={"server_id": self.server_id},
                )
            if resp.status_code == 200:
                await interaction.response.send_message(
                    "\u274c **All consents revoked.** Your messages will no longer be processed.\n"
                    "You can re-enable anytime with `/privacy`.",
                    ephemeral=True,
                )
            elif resp.status_code == 404:
                await interaction.response.send_message(
                    "No active consents found for this server.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Something went wrong. Please try again.", ephemeral=True
                )
        except Exception as e:
            logger.error("consent_revoke_failed", error=str(e))
            await interaction.response.send_message("Connection error. Please try again.", ephemeral=True)

    async def _set_consent(self, interaction: discord.Interaction, kb: bool, ai: bool, label: str):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{API_BASE}/api/consent",
                    json={
                        "user_hash": self.user_hash,
                        "server_id": self.server_id,
                        "kb_consent": kb,
                        "ai_consent": ai,
                    },
                )
            if resp.status_code in (200, 201):
                await interaction.response.send_message(
                    f"\u2705 **{label}** consent granted.\n"
                    f"Your messages in this server will be processed accordingly.\n"
                    f"Change anytime with `/privacy`.",
                    ephemeral=True,
                )
            else:
                logger.error("consent_set_api_error", status=resp.status_code, body=resp.text[:200])
                await interaction.response.send_message("Something went wrong. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error("consent_set_failed", error=str(e))
            await interaction.response.send_message("Connection error. Please try again.", ephemeral=True)


class ConsentCog(commands.Cog):
    """Consent management slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="privacy", description="Manage your NeuroWeave privacy and consent settings")
    async def privacy(self, interaction: discord.Interaction):
        """Show consent options as ephemeral message with buttons."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        user_hash = _hash_user_id(interaction.user.id)

        # Resolve Discord guild ID → internal DB server ID
        server_id = await _resolve_server_id(interaction.guild.id)
        if server_id is None:
            await interaction.response.send_message(
                "This server is not registered with NeuroWeave yet. Ask an admin to set it up.",
                ephemeral=True,
            )
            return

        # Check current consent status
        status_text = ""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{API_BASE}/api/consent/{user_hash}")
                if resp.status_code == 200:
                    data = resp.json()
                    consents = data.get("consents", [])
                    server_consent = next(
                        (c for c in consents if c.get("server_id") == server_id), None
                    )
                    if server_consent and not server_consent.get("revoked_at"):
                        kb = "\u2705" if server_consent.get("kb_consent") else "\u274c"
                        ai = "\u2705" if server_consent.get("ai_consent") else "\u274c"
                        status_text = f"\n\n**Current settings:**\n{kb} Knowledge Base\n{ai} AI Training Data"
        except Exception:
            pass

        embed = discord.Embed(
            title="\U0001f512 NeuroWeave Privacy Settings",
            description=(
                "This server uses NeuroWeave to build a knowledge base from "
                "technical discussions. Your messages may be processed.\n\n"
                "**Choose your preferences:**"
                f"{status_text}"
            ),
            color=0x6366F1,
        )
        embed.set_footer(text="All data is anonymized. Change settings anytime with /privacy")

        view = ConsentView(user_hash=user_hash, server_id=server_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConsentCog(bot))
