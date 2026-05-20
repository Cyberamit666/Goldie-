from __future__ import annotations

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        embed = discord.Embed(
            title=f"⚡ Goldie is now live in {guild.name}!",
            description=(
                "The economy system is now active on your server.\n\n"
                "**Quick Start:**\n"
                "> `go setup_channel` — Designate channels *(Admin only)*\n"
                "> `go help` — View all commands\n\n"
                "Every user will be prompted to accept rules before interacting, "
                "keeping your economy fair and secure."
            ),
            color=discord.Color.gold(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text="Thank you for choosing Goldie!")

        # Try the system channel first, fall back to owner DM
        sent = False
        if guild.system_channel and guild.system_channel.permissions_for(
            guild.me
        ).send_messages:
            try:
                await guild.system_channel.send(embed=embed)
                sent = True
            except Exception:
                pass

        if not sent and guild.owner:
            try:
                await guild.owner.send(embed=embed)
            except Exception:
                pass

        print(f"✅  Joined guild: {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        # Clean up channel config for the departed guild
        try:
            await self.bot.dbs.logs.execute(
                "DELETE FROM channel_logs WHERE guild_id = ?", (guild.id,)
            )
            await self.bot.dbs.logs.commit()
        except Exception:
            pass
        print(f"❌  Left guild: {guild.name} ({guild.id})")


async def setup(bot) -> None:
    await bot.add_cog(Events(bot))
