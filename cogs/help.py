from __future__ import annotations

import discord
from discord.ext import commands
from difflib import get_close_matches

# Category → command names mapping (controls the help display order)
CATEGORIES: dict[str, list[str]] = {
    "💰 Economy":    ["bal", "profile", "profit"],
    "🎮 Games":      ["cf"],
    "🏆 Rankings":   ["lb"],
    "⚙️ Setup":      ["setup_channel"],
}

SLASH_COMMANDS = ["`/bot_stats`", "`/search_player`"]


class HelpView(discord.ui.View):
    def __init__(self, bot, author_id: int) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="📋 Full Command List", style=discord.ButtonStyle.blurple)
    async def full_list(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        prefix = self.bot.command_prefix.strip()
        embed = discord.Embed(
            title="📋 Full Command Reference", color=discord.Color.gold()
        )

        for category, cmd_names in CATEGORIES.items():
            lines = []
            for name in cmd_names:
                cmd = self.bot.get_command(name)
                if cmd and not cmd.hidden:
                    desc = (cmd.help or cmd.brief or "No description.").split("\n")[0]
                    lines.append(f"`{prefix} {name}` — {desc}")
            if lines:
                embed.add_field(name=category, value="\n".join(lines), inline=False)

        embed.add_field(
            name="🔧 Slash Commands (Owner/Admin)",
            value="\n".join(SLASH_COMMANDS),
            inline=False,
        )
        embed.set_footer(text="Goldie Economy System")
        await interaction.response.edit_message(embed=embed, view=self)


class HelpGoldie(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(name="help", aliases=["h", "commands"])
    async def help_command(self, ctx) -> None:
        """Show all available commands."""
        prefix = self.bot.command_prefix.strip()

        embed = discord.Embed(
            title="🟡 Goldie — Command Center",
            description=(
                f"Use **`{prefix} <command>`** to interact.\n"
                "Click **Full Command List** for detailed descriptions."
            ),
            color=discord.Color.gold(),
        )

        for category, cmd_names in CATEGORIES.items():
            names = [f"`{n}`" for n in cmd_names if self.bot.get_command(n)]
            if names:
                embed.add_field(name=category, value="  ".join(names), inline=False)

        embed.add_field(
            name="🔧 Slash Commands",
            value="  ".join(SLASH_COMMANDS),
            inline=False,
        )
        embed.set_footer(text="Goldie Economy System • Tip: go profit for daily P&L")

        view = HelpView(self.bot, ctx.author.id)
        await ctx.send(embed=embed, view=view)

    # ── Error handler ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error) -> None:
        if isinstance(error, commands.CommandNotFound):
            tried = ctx.invoked_with
            all_cmds = [c.name for c in self.bot.commands if not c.hidden]
            matches = get_close_matches(tried, all_cmds, n=1, cutoff=0.55)
            prefix = self.bot.command_prefix.strip()
            if matches:
                msg = f"❓ Command not found. Did you mean `{prefix} {matches[0]}`?"
            else:
                msg = f"❓ Command not found. Type `{prefix} help` for all commands."
            await ctx.send(msg, delete_after=10)

        elif isinstance(error, commands.MissingRequiredArgument):
            prefix = self.bot.command_prefix.strip()
            await ctx.send(
                f"❌ Missing argument: `{error.param.name}`. "
                f"Type `{prefix} help` for usage info.",
                delete_after=10,
            )

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ You don't have permission to use this command.", delete_after=8
            )

        elif isinstance(error, commands.CheckFailure):
            pass  # Gates handle their own messaging

        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"❌ Bad input: `{error}`. Check your arguments and try again.",
                delete_after=8,
            )

        else:
            print(f"[Unhandled Error] {ctx.command}: {error}")


async def setup(bot) -> None:
    await bot.add_cog(HelpGoldie(bot))
