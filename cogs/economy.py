from __future__ import annotations

import datetime
import discord
from discord.ext import commands

from core.utils import win_rate, fmt_signed


class Economy(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    # ── Balance ───────────────────────────────────────────────────────────────

    @commands.command(name="bal", aliases=["balance", "wallet", "coins"])
    async def balance(self, ctx, member: discord.Member = None) -> None:
        """Check your balance and quick stats. Usage: go bal [@user]"""
        target = member or ctx.author

        async with self.bot.dbs.players.execute(
            """SELECT balance, total_games, total_wins, total_losses,
                      total_wagered, total_profit
               FROM players WHERE uid = ?""",
            (target.id,),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            msg = (
                "❌ You don't have an account yet — accept the rules first!"
                if target == ctx.author
                else f"❌ {target.mention} doesn't have an account."
            )
            return await ctx.send(msg)

        balance, games, wins, losses, wagered, profit = row
        wr = win_rate(wins, games)
        profit_color = discord.Color.green() if profit >= 0 else discord.Color.red()

        embed = discord.Embed(
            title=f"{'👤' if target == ctx.author else '🔍'} {target.display_name}'s Wallet",
            color=profit_color,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💰 Balance",     value=f"`🪙 {balance:,}`",           inline=True)
        embed.add_field(name="📈 Net Profit",  value=f"`{fmt_signed(profit)}`",     inline=True)
        embed.add_field(name="🎯 Win Rate",    value=f"`{wr:.1f}%`",               inline=True)
        embed.add_field(name="🎮 Games",       value=f"`{games:,}`",               inline=True)
        embed.add_field(name="✅ Wins",        value=f"`{wins:,}`",                inline=True)
        embed.add_field(name="❌ Losses",      value=f"`{losses:,}`",              inline=True)
        embed.set_footer(text="Use `go profit` for daily/weekly breakdown • Goldie Economy")

        await ctx.send(embed=embed)

    # ── Profile ───────────────────────────────────────────────────────────────

    @commands.command(name="profile", aliases=["stats", "me", "card"])
    async def profile(self, ctx, member: discord.Member = None) -> None:
        """View a full player profile with all stats. Usage: go profile [@user]"""
        target = member or ctx.author

        async with self.bot.dbs.players.execute(
            """SELECT balance, total_games, total_wins, total_losses,
                      total_wagered, total_profit, joined_bot
               FROM players WHERE uid = ?""",
            (target.id,),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return await ctx.send(f"❌ No profile found for {target.mention}.")

        balance, games, wins, losses, wagered, profit, joined_bot = row
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.strftime("%Y-%m-%d")

        # Today's stats from economy.db
        async with self.bot.dbs.economy.execute(
            """SELECT COUNT(*), SUM(bet),
                      SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END),
                      SUM(profit)
               FROM transactions WHERE uid = ? AND DATE(timestamp) = ?""",
            (target.id, today),
        ) as cur:
            d = await cur.fetchone()
        d_games, d_wagered, d_wins, d_profit = (d[0] or 0, d[1] or 0, d[2] or 0, d[3] or 0)

        # Rank by balance
        async with self.bot.dbs.players.execute(
            "SELECT COUNT(*) FROM players WHERE balance > ? AND accepted = 1",
            (balance,),
        ) as cur:
            rank_row = await cur.fetchone()
        rank = (rank_row[0] + 1) if rank_row else "?"

        wr = win_rate(wins, games)
        profit_color = discord.Color.green() if profit >= 0 else discord.Color.red()

        embed = discord.Embed(
            title=f"📊 {target.display_name}'s Profile",
            color=profit_color,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(
            name="💰 Economy",
            value=(
                f"Balance: `🪙 {balance:,}`\n"
                f"Net Profit: `{fmt_signed(profit)}`\n"
                f"Total Wagered: `🪙 {wagered:,}`\n"
                f"Leaderboard Rank: `#{rank}`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎮 Game Stats",
            value=(
                f"Total Games: `{games:,}`\n"
                f"Wins / Losses: `{wins:,}` / `{losses:,}`\n"
                f"Win Rate: `{wr:.1f}%`"
            ),
            inline=True,
        )
        embed.add_field(
            name="📅 Today",
            value=(
                f"Games: `{d_games}`\n"
                f"Wagered: `🪙 {d_wagered:,}`\n"
                f"Profit: `{fmt_signed(d_profit)}`"
            ),
            inline=True,
        )

        if joined_bot:
            try:
                dt = datetime.datetime.fromisoformat(joined_bot)
                embed.add_field(
                    name="📆 Member Since",
                    value=discord.utils.format_dt(dt, style="D"),
                    inline=False,
                )
            except ValueError:
                pass

        embed.set_footer(text="Goldie Economy System")
        await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Economy(bot))
