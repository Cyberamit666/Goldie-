import discord

def get_rules_embed(user):
    """Generates an enhanced rules embed with specific formatting."""
    embed = discord.Embed(
        title="✨ ___**Goldie System Rules**___ ✨",
        description=(
            f"### Welcome {user.mention}!\n\n"
            "*Before accessing the economy features, please read and accept the following conditions:*\n\n"
            "**1.** `Be respectful to all members.`\n"
            "**2.** `Do not exploit bot mechanics or glitches.`\n"
            "**3.** `Decisions made by the bot owners are final.`\n\n"
            "> _By clicking the button below, you agree to these terms._"
        ),
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🎁 **Starter Gift**", 
        value="`💰 1,000 coins` *will be added to your wallet immediately!*", 
        inline=False
    )
    embed.set_footer(text="⚠️ This menu will expire in 5 minutes.")
    return embed

async def send_welcome_dm(user):
    """Handles the DM part of the welcome process."""
    try:
        embed = discord.Embed(
            title="🎊 **Welcome to the Goldie Economy!**",
            description=(
                "### Your account is now ***Active***\n\n"
                "You can now participate in all activities. "
                "Use `go bal` to check your current balance."
            ),
            color=discord.Color.green()
        )
        await user.send(embed=embed)
    except discord.Forbidden:
        print(f"Log: Failed to DM {user}")