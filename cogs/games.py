from __future__ import annotations

import datetime
import random
import discord
from discord.ext import commands

from core.utils import (
    parse_amount,
    check_cooldown,
    set_cooldown,
    is_processing,
    set_processing,
    clear_processing,
)


class Games(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    # ── Coinflip ──────────────────────────────────────────────────────────────

    @commands.command(name="cf", aliases=["coinflip", "flip"])
    async def coinflip(self, ctx, amount: str, side: str = None) -> None:
        """Flip a coin for coins. Usage: go cf <amount> <heads/tails>"""
        uid = ctx.author.id
        max_bet = self.bot.cfg.MAX_BET
        cooldown = self.bot.cfg.CF_COOLDOWN

        # Anti-duplicate lock
        if is_processing(uid, "cf"):
            return await ctx.send(
                "⏳ Your previous flip is still being processed!", delete_after=5
            )

        # Rate limit
        remaining = check_cooldown(uid, "cf", cooldown)
        if remaining > 0:
            return await ctx.send(
                f"⏱️ Please wait **{remaining:.1f}s** before flipping again.",
                delete_after=5,
            )

        # Side validation
        if not side or side.lower() not in ("heads", "tails", "h", "t"):
            return await ctx.send("❌ Usage: `go cf <amount> <heads/tails>`")

        user_choice = "heads" if side.lower() in ("heads", "h") else "tails"

        # Fetch balance
        async with self.bot.dbs.players.execute(
            "SELECT balance FROM players WHERE uid = ?", (uid,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return await ctx.send("❌ Account not found.")

        current_balance = row[0]

        # Parse amount
        bet = parse_amount(amount, current_balance)
        if bet is None:
            return await ctx.send(
                "❌ Invalid amount. Try a number, `1k`, `2.5k`, `all`, or `half`."
            )
        if bet <= 0:
            return await ctx.send("❌ Bet must be greater than zero.")
        if bet > max_bet:
            return await ctx.send(
                f"❌ Maximum bet is `🪙 {max_bet:,}`."
            )
        if bet > current_balance:
            return await ctx.send(
                f"❌ Insufficient balance. You have `🪙 {current_balance:,}`."
            )

        # Lock + set cooldown
        set_processing(uid, "cf")
        set_cooldown(uid, "cf")

        try:
            result = random.choice(("heads", "tails"))
            won = user_choice == result
            profit = bet if won else -bet
            new_balance = current_balance + profit
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Atomic stat update
            await self.bot.dbs.players.execute(
                """UPDATE players SET
                       balance       = ?,
                       total_games   = total_games   + 1,
                       total_wins    = total_wins    + ?,
                       total_losses  = total_losses  + ?,
                       total_wagered = total_wagered + ?,
                       total_profit  = total_profit  + ?
                   WHERE uid = ?""",
                (
                    new_balance,
                    1 if won else 0,
                    0 if won else 1,
                    bet,
                    profit,
                    uid,
                ),
            )
            await self.bot.dbs.players.commit()

            # Transaction log
            await self.bot.dbs.economy.execute(
                "INSERT INTO transactions (uid, game, bet, profit, timestamp) VALUES (?, ?, ?, ?, ?)",
                (uid, "coinflip", bet, profit, now),
            )
            await self.bot.dbs.economy.commit()

            # Update username in case it changed
            await self.bot.dbs.players.execute(
                "UPDATE players SET username = ? WHERE uid = ?",
                (str(ctx.author), uid),
            )
            await self.bot.dbs.players.commit()

            # Build embed response
            if won:
                color = discord.Color.green()
                title = "💎 WIN!"
                desc = (
                    f"**{ctx.author.display_name}** picked **{user_choice}** "
                    f"— coin landed **{result}**!\n💵 STATUS: **FILTHY RICH**"
                )
            else:
                color = discord.Color.red()
                title = "💔 LOST"
                desc = (
                    f"**{ctx.author.display_name}** picked **{user_choice}** "
                    f"— coin landed **{result}**.\n📉 STATUS: **DOWN BAD**"
                )

            sign = "+" if won else "-"
            embed = discord.Embed(title=title, description=desc, color=color)
            embed.add_field(name="Bet",         value=f"`🪙 {bet:,}`",               inline=True)
            embed.add_field(name="Result",      value=f"`{sign}🪙 {bet:,}`",         inline=True)
            embed.add_field(name="New Balance", value=f"`🪙 {new_balance:,}`",       inline=True)
            embed.set_footer(text="Goldie Economy • go profit for daily stats")

            await ctx.send(embed=embed)

        except Exception as exc:
            print(f"[coinflip error] {exc}")
            await ctx.send("❌ Something went wrong. Please try again.", delete_after=8)
        finally:
            clear_processing(uid, "cf")


async def setup(bot) -> None:
    await bot.add_cog(Games(bot))
