from __future__ import annotations

import datetime
import discord
from discord.ext import commands


class ChannelSelectView(discord.ui.View):
    def __init__(self, bot, current_ids: list[int]) -> None:
        super().__init__(timeout=120)
        self.bot = bot
        self._select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Select up to 3 channels…",
            min_values=1,
            max_values=3,
            default_values=[discord.Object(id=i) for i in current_ids],
        )
        self._select.callback = self._on_select
        self.add_item(self._select)

    async def _on_select(self, interaction: discord.Interaction) -> None:
        await self.bot.dbs.logs.execute(
            "DELETE FROM channel_logs WHERE guild_id = ?", (interaction.guild.id,)
        )
        for ch in self._select.values:
            await self.bot.dbs.logs.execute(
                "INSERT INTO channel_logs (guild_id, channel_id) VALUES (?, ?)",
                (interaction.guild.id, ch.id),
            )
        await self.bot.dbs.logs.commit()

        # Audit log
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        details = ", ".join(str(ch.id) for ch in self._select.values)
        await self.bot.dbs.logs.execute(
            "INSERT INTO action_logs (guild_id, action, actor_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (interaction.guild.id, "channel_setup", interaction.user.id, details, now),
        )
        await self.bot.dbs.logs.commit()

        mentions = ", ".join(f"<#{ch.id}>" for ch in self._select.values)
        embed = discord.Embed(
            title="✅ Channels Configured",
            description=f"Goldie will now respond in:\n{mentions}",
            color=discord.Color.green(),
        )
        embed.set_footer(text="You can re-run this command at any time to update.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Admin(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(name="setup_channel")
    @commands.has_permissions(administrator=True)
    async def setup_channel(self, ctx) -> None:
        """Configure which channels Goldie responds in. (Admin only)"""
        async with self.bot.dbs.logs.execute(
            "SELECT channel_id FROM channel_logs WHERE guild_id = ?", (ctx.guild.id,)
        ) as cur:
            current_ids = [row[0] for row in await cur.fetchall()]

        embed = discord.Embed(
            title="⚙️ Channel Setup",
            description=(
                "Select the text channels where Goldie will accept commands.\n"
                "You can choose **1–3** channels."
            ),
            color=discord.Color.gold(),
        )
        if current_ids:
            embed.add_field(
                name="Currently Active",
                value="\n".join(f"<#{cid}>" for cid in current_ids),
                inline=False,
            )

        view = ChannelSelectView(self.bot, current_ids)
        await ctx.send(embed=embed, view=view)

    @setup_channel.error
    async def setup_channel_error(self, ctx, error) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ You need **Administrator** permission to use this command.",
                delete_after=8,
            )


async def setup(bot) -> None:
    await bot.add_cog(Admin(bot))
