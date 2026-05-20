import discord
import asyncio
from core.rules import get_rules_embed, send_welcome_dm

class RulesView(discord.ui.View):
    def __init__(self, message=None):
        super().__init__(timeout=None)
        self.message = message

    async def start_auto_delete(self):
        """Task to automatically delete the message after 2 minutes if no action is taken."""
        await asyncio.sleep(120)
        try:
            if self.message:
                await self.message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    @discord.ui.button(label="Accept & Start", style=discord.ButtonStyle.green, custom_id="gate_v10")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in interaction.client.accepted_cache:
            return await interaction.response.send_message("⚠️ You have already accepted the rules!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        await interaction.client.db.execute(
            "INSERT OR IGNORE INTO players (uid, accepted, balance) VALUES (?, 1, 1000)",
            (interaction.user.id,)
        )
        await interaction.client.db.commit()
        
        interaction.client.accepted_cache.add(interaction.user.id)
        
        try:
            await interaction.message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        
        await send_welcome_dm(interaction.user)
        await interaction.followup.send("✅ Verified! Check your DMs.", ephemeral=True)

async def ban_gate(ctx):
    """Gate 0: Checks if the user is banned from the bot system."""
    async with ctx.bot.db.execute("SELECT 1 FROM players_ban WHERE uid = ?", (ctx.author.id,)) as cursor:
        if await cursor.fetchone():
            await ctx.send("❌ **Access Denied:** You have been banned from using this bot.", delete_after=10)
            return False
    return None

async def channel_gate(ctx):
    """Gate 1: Checks for authorized channels."""
    async with ctx.bot.log_db.execute(
        "SELECT 1 FROM channel_logs WHERE guild_id = ?", (ctx.guild.id,)
    ) as cursor:
        setup_exists = await cursor.fetchone()

    if not setup_exists:
        if ctx.author.guild_permissions.administrator:
            await ctx.invoke(ctx.bot.get_command('setup_channel'))
        else:
            await ctx.send("<a:emoji_20:1503628242010243113>**SETUP REQUIRED!:** ``Please contact a server Administrator to set-up interaction channels``.")
        return False

    async with ctx.bot.log_db.execute(
        "SELECT 1 FROM channel_logs WHERE guild_id = ? AND channel_id = ?", 
        (ctx.guild.id, ctx.channel.id)
    ) as cursor:
        if not await cursor.fetchone():
            return False
    return None

async def verification_gate(ctx):
    """Gate 2: Checks for rules acceptance."""
    if ctx.author.id in ctx.bot.accepted_cache: return True
    async with ctx.bot.db.execute("SELECT accepted FROM players WHERE uid = ?", (ctx.author.id,)) as cursor:
        row = await cursor.fetchone()
        if row and row[0] == 1:
            ctx.bot.accepted_cache.add(ctx.author.id)
            return True
    
    view = RulesView()
    msg = await ctx.send(embed=get_rules_embed(ctx.author), view=view)
    view.message = msg
    ctx.bot.loop.create_task(view.start_auto_delete())
    return False

async def check_user_access(ctx):
    """Global check for all bot commands."""
    if ctx.author.bot: return True
    
    # OWNER BYPASS
    if await ctx.bot.is_owner(ctx.author):
        return True

    if hasattr(ctx, "interaction") and ctx.interaction:
        if ctx.interaction.data.get("custom_id") == "gate_v10":
            return True

    if ctx.command and ctx.command.name == "setup_channel" and ctx.author.guild_permissions.administrator:
        return True

    # Process all gates (Ban -> Channel -> Verification)
    for gate in [ban_gate, channel_gate, verification_gate]:
        result = await gate(ctx)
        if result is True: return True
        if result is False: return False
    return True