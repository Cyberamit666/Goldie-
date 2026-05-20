import discord
from discord.ext import commands
import random
import re

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_amount(self, amount_str, balance):
        """Helper to convert 1k, 0.5k, etc., into integers."""
        amount_str = amount_str.lower().strip()
        if amount_str == "all":
            return balance
        
        # Regex to find numbers and the 'k' suffix
        match = re.match(r"([\d.]+)([k]?)", amount_str)
        if not match:
            return None
        
        num, suffix = match.groups()
        try:
            val = float(num)
            if suffix == "k":
                val *= 1000
            return int(val)
        except ValueError:
            return None

    @commands.command(name="cf", aliases=["coinflip"])
    async def coinflip(self, ctx, amount: str, side: str = None):
        """Usage: go cf <amount> <heads/tails>"""
        
        # 1. Validation: Basic checks
        if side is None or side.lower() not in ["heads", "tails", "h", "t"]:
            return await ctx.send("❌ Usage: `go cf <amount> <heads/tails>`")
        
        # Normalize side
        user_choice = "heads" if side.lower() in ["heads", "h"] else "tails"

        # 2. Get Balance & Parse Bet
        async with self.bot.db.execute("SELECT balance FROM players WHERE uid = ?", (ctx.author.id,)) as cursor:
            row = await cursor.fetchone()
            current_balance = row[0] if row else 0

        bet = self.parse_amount(amount, current_balance)

        if bet is None:
            return await ctx.send("❌ Please enter a valid number (e.g., 100, 1.5k, all).")

        if bet <= 0:
            return await ctx.send("❌ You can't bet nothing!")
        
        # 3. Maximum Bet Logic (300k)
        if bet > 300000:
            return await ctx.send("❌ The maximum bet is **💰 300,000** coins!")
        
        if bet > current_balance:
            return await ctx.send(f"❌ You don't have enough coins! Balance: **{current_balance}**")

        # 4. The Game Logic
        result = random.choice(["heads", "tails"])
        win = user_choice == result
        
        if win:
            new_balance = current_balance + bet
            status = "💎 STATUS: **FILTHY RICH**"
            outcome_text = f"**💰 WIN!** | **{ctx.author.name}** picked **{user_choice}** and doubled their **{bet:,}**!"
            color = discord.Color.green()
        else:
            new_balance = current_balance - bet
            status = "📉 STATUS: **DOWN BAD**"
            outcome_text = f"**💔 LOST** | **{ctx.author.name}** picked **{user_choice}** and lost **{bet:,}**."
            color = discord.Color.red()

        # 5. Update Database
        await self.bot.db.execute("UPDATE players SET balance = ? WHERE uid = ?", (new_balance, ctx.author.id))
        await self.bot.db.commit()

        # 6. Response (Option C Style)
        embed = discord.Embed(description=f"{outcome_text}\n{status}", color=color)
        embed.set_footer(text=f"New Balance: {new_balance:,}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))