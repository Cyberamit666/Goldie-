import discord
from discord.ext import commands

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        Triggered when Goldie joins a new server.
        Sends a sleek, black professional embed to the owner.
        """
        owner = guild.owner
        if owner:
            # Color 0x000001 creates the 'stealth' black aesthetic
            embed = discord.Embed(
                title=f"<a:emoji_19:1503628162754543666> GOLDIE ADDED TO `{guild.name}`",
                description=(
                    f"Goldie is now online at **{guild.name}**\n\n"
                    "```\n"
                    "The user registration framework has been successfully deployed. Every new user will be prompted to authorize the server's rules, before interacting with the system.\n"
                    "```\n"
                    "***For a better experience, we recommend designating a specific channel for all Goldie interactions!***\n\n"
                    "<a:emoji_20:1503628242010243113>` *NEED HELP?:* ***Just Type*** __go help__ *** for all available interactions ***\n\n"
                    "Thank you <a:emoji_19:1503628162754543666>"
                ),
                color=0x000001
            )

            # Adds the server's PFP to the top right
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            embed.set_footer(text="Logged in and secured. | Thanks for choosing Goldie")
            
            try:
                await owner.send(embed=embed)
                # Success log for Termux
                print(f"✅ Professional welcome sent to {owner.name}")
            except discord.Forbidden:
                print(f"❌ Could not DM {owner.name}. DMs are restricted.")

async def setup(bot):
    await bot.add_cog(Events(bot))