import discord


def get_rules_embed(user: discord.User | discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="✨ Goldie System Rules",
        description=(
            f"### Welcome, {user.mention}!\n\n"
            "*Please read and accept the following rules before accessing the economy:*\n\n"
            "**1.** `Be respectful to all members.`\n"
            "**2.** `Do not exploit bot mechanics or glitches.`\n"
            "**3.** `Decisions made by bot owners are final.`\n\n"
            "> *By clicking the button below, you agree to all terms.*"
        ),
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="🎁 Starter Gift",
        value="`🪙 1,000 coins` will be added to your wallet immediately!",
        inline=False,
    )
    embed.set_footer(text="This prompt will be removed once you respond.")
    return embed


async def send_welcome_dm(user: discord.User | discord.Member) -> None:
    try:
        embed = discord.Embed(
            title="🎊 Welcome to Goldie Economy!",
            description=(
                "### Your account is now **Active**\n\n"
                "You can now participate in all economy activities.\n\n"
                "**Getting Started:**\n"
                "> `go bal` — Check your balance\n"
                "> `go cf` — Play coinflip\n"
                "> `go lb` — View leaderboards\n"
                "> `go profit` — Daily profit & loss\n"
                "> `go help` — All commands"
            ),
            color=discord.Color.green(),
        )
        await user.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass
