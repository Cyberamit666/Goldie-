import discord
from discord.ext import commands
from discord import app_commands
from cogs.bot_moderation.stats import execute_stats
from cogs.bot_moderation.admin_tools import execute_player_search

class BotModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bot_stats", description="View bot system statistics.")
    async def owner_stats(self, interaction: discord.Interaction):
        """Standard diagnostic command."""
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
        
        ctx = await self.bot.get_context(interaction)
        await execute_stats(ctx)

    @app_commands.command(name="search_player", description="Search and manage a player by UID.")
    @app_commands.describe(uid="The Discord User ID to search for")
    async def search_player(self, interaction: discord.Interaction, uid: str):
        """Owner-only player management."""
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
        
        try:
            target_id = int(uid)
            ctx = await self.bot.get_context(interaction)
            await execute_player_search(ctx, target_id)
        except ValueError:
            await interaction.response.send_message("❌ Error: UID must be a numeric ID.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BotModeration(bot))