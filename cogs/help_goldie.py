import discord
from discord.ext import commands
from difflib import get_close_matches

class HelpGoldie(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Shows all available commands dynamically."""
        embed = discord.Embed(
            title="🟡 Goldie Command List",
            description="Here are the available commands for Goldie:",
            color=discord.Color.gold()
        )
        
        # This automatically finds all commands you've added to your cogs
        cmds = [f"`{c.name}`" for c in self.bot.commands if not c.hidden]
        
        embed.add_field(name="Commands", value=", ".join(cmds) or "No commands found.", inline=False)
        embed.add_field(name="Usage", value=f"Type `{self.bot.command_prefix}[command]` to use them.", inline=False)
        embed.set_footer(text="Goldie Economy System")
        
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Guids the user if they make a spelling mistake."""
        if isinstance(error, commands.CommandNotFound):
            # Get the name of the command they TRIED to type
            cmd_tried = ctx.invoked_with
            # Get a list of all VALID command names
            all_commands = [c.name for c in self.bot.commands if not c.hidden]
            
            # Find the closest match
            matches = get_close_matches(cmd_tried, all_commands, n=1, cutoff=0.6)
            
            if matches:
                msg = f"❌ **Command not found.** Did you mean `{ctx.prefix}{matches[0]}`?"
            else:
                msg = f"❌ **Command not found.** Type `{ctx.prefix}help` for a list of commands."
            
            await ctx.send(msg)
        
        # Don't forget to handle other errors so the bot doesn't crash
        elif isinstance(error, commands.CheckFailure):
            pass # Verification gate handles this
        else:
            print(f"Error: {error}")

async def setup(bot):
    await bot.add_cog(HelpGoldie(bot))