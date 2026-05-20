from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

from cogs.bot_moderation.stats import execute_stats
from cogs.bot_moderation.admin_tools import execute_player_search


class BotModeration(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    # ── /bot_stats ────────────────────────────────────────────────────────────

    @app_commands.command(
        name="bot_stats",
        description="View detailed bot diagnostics. (Owner only)",
    )
    async def owner_stats(self, interaction: discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message(
                "❌ Access Denied.", ephemeral=True
            )
        ctx = await self.bot.get_context(interaction)
        await execute_stats(ctx)

    # ── /search_player ────────────────────────────────────────────────────────

    @app_commands.command(
        name="search_player",
        description="Look up full stats and manage any player by UID. (Owner only)",
    )
    @app_commands.describe(uid="The Discord User ID to search for")
    async def search_player(
        self, interaction: discord.Interaction, uid: str
    ) -> None:
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message(
                "❌ Access Denied.", ephemeral=True
            )
        try:
            target_id = int(uid)
        except ValueError:
            return await interaction.response.send_message(
                "❌ UID must be a numeric Discord ID.", ephemeral=True
            )

        ctx = await self.bot.get_context(interaction)
        await execute_player_search(ctx, target_id)


async def setup(bot) -> None:
    await bot.add_cog(BotModeration(bot))
