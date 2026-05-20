from __future__ import annotations

import datetime
import discord
from discord.ext import commands

from core.utils import fmt_signed, win_rate


class ProfitView(discord.ui.View):
    def __init__(self, bot, uid: int, mode: str = "daily") -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.uid = uid
        self.mode = mode
        self._rebuild()

    def _rebuild(self) -> None:
        self.clear_items()

        daily_btn = discord.ui.Button(
            label="📅 Daily",
            style=discord.ButtonStyle.success
            if self.mode == "daily"
            else discord.ButtonStyle.secondary,
            row=0,
        )
        daily_btn.callback = self._set_daily
        self.add_item(daily_btn)

        weekly_btn = discord.ui.Button(
            label="🗓️ Weekly",
            style=discord.ButtonStyle.success
            if self.mode == "weekly"
            else discord.ButtonStyle.secondary,
            row=0,
        )
        weekly_btn.callback = self._set_weekly
        self.add_item(weekly_btn)

    # ── Button callbacks ──────────────────────────────────────────────────────

    async def _set_daily(self, interaction: discord.Interaction) -> None:
        self.mode = "daily"
        self._rebuild()
        embed = await self._build_embed(interaction.client)
        await interaction.response.edit_message(embed=embed, view=self)

    async def _set_weekly(self, interaction: discord.Interaction) -> None:
        self.mode = "weekly"
        self._rebuild()
        embed = await self._build_embed(interaction.client)
        await interaction.response.edit_message(embed=embed, view=self)

    # ── Embed builder ─────────────────────────────────────────────────────────

    async def _build_embed(self, bot) -> discord.Embed:
        now = datetime.datetime.now(datetime.timezone.utc)

        if self.mode == "daily":
            label = "Today"
            date_filter = f"DATE(timestamp) = '{now.strftime('%Y-%m-%d')}'"
        else:
            week_start = (now - datetime.timedelta(days=now.weekday())).strftime("%Y-%m-%d")
            label = "This Week"
            date_filter = f"DATE(timestamp) >= '{week_start}'"

        async with bot.dbs.economy.execute(
            f"""SELECT
                    COUNT(*)                                           AS games,
                    COALESCE(SUM(bet), 0)                              AS wagered,
                    COALESCE(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END), 0) AS wins,
                    COALESCE(SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END), 0) AS losses,
                    COALESCE(SUM(profit), 0)                           AS net
               FROM transactions
               WHERE uid = ? AND {date_filter}""",
            (self.uid,),
        ) as cur:
            row = await cur.fetchone()

        games   = row[0] or 0
        wagered = row[1] or 0
        wins    = row[2] or 0
        losses  = row[3] or 0
        net     = row[4] or 0
        wr      = win_rate(wins, games)
        color   = discord.Color.green() if net >= 0 else discord.Color.red()

        user = bot.get_user(self.uid)
        name = user.display_name if user else f"User {self.uid}"

        icon = "📅" if self.mode == "daily" else "🗓️"
        embed = discord.Embed(
            title=f"{icon} {name}'s {label} P&L",
            color=color,
        )
        embed.add_field(name="🎮 Games Played",  value=f"`{games}`",            inline=True)
        embed.add_field(name="✅ Wins",           value=f"`{wins}`",             inline=True)
        embed.add_field(name="❌ Losses",         value=f"`{losses}`",           inline=True)
        embed.add_field(name="💸 Wagered",        value=f"`🪙 {wagered:,}`",    inline=True)
        embed.add_field(name="🎯 Win Rate",       value=f"`{wr:.1f}%`",         inline=True)
        embed.add_field(
            name="📊 Net Profit / Loss",
            value=f"```\n{fmt_signed(net)} coins\n```",
            inline=False,
        )
        embed.set_footer(
            text=f"Goldie Economy • {'Daily' if self.mode == 'daily' else 'Weekly'} View"
        )
        return embed


class Profit(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(name="profit", aliases=["pnl", "earnings", "daily"])
    async def profit(self, ctx, member: discord.Member = None) -> None:
        """Check your daily/weekly profit and loss. Usage: go profit [@user]"""
        target = member or ctx.author

        view = ProfitView(self.bot, target.id)
        embed = await view._build_embed(self.bot)
        await ctx.send(embed=embed, view=view)


async def setup(bot) -> None:
    await bot.add_cog(Profit(bot))
