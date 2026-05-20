import discord
import datetime

# ==================== APPEAL SYSTEM ====================

class AppealView(discord.ui.View):
    def __init__(self, bot, target_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.target_id = target_id

    @discord.ui.button(label="Submit Unban Application", style=discord.ButtonStyle.blurple, custom_id="appeal_unban")
    async def appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if already submitted
        async with self.bot.db.execute("SELECT 1 FROM ban_appeals WHERE uid = ?", (self.target_id,)) as cursor:
            if await cursor.fetchone():
                return await interaction.response.send_message("<:emoji_26:1504070583145594942> You have already submitted an appeal. Please wait for staff review.", ephemeral=True)

        await interaction.response.send_modal(AppealModal(self.bot, self.target_id))


class AppealModal(discord.ui.Modal, title="Unban Application"):
    description = discord.ui.TextInput(
        label="<:emoji_22:1503659968296124536>Your Appeal Reason",
        placeholder="<:emoji_22:1503659968296124536>Explain why you should be unbanned...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    def __init__(self, bot, target_id: int):
        super().__init__()
        self.bot = bot
        self.target_id = target_id

    async def on_submit(self, interaction: discord.Interaction):
        # Save appeal
        await self.bot.db.execute(
            "INSERT INTO ban_appeals (uid, reason, appeal_time) VALUES (?, ?, ?)",
            (self.target_id, self.description.value, datetime.datetime.now(datetime.timezone.utc).isoformat())
        )
        await self.bot.db.commit()

        # Send to staff channel
        channel_id = getattr(self.bot, 'appeal_channel_id', None)
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="🔔 New Ban Appeal",
                    color=discord.Color.orange(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.add_field(name="User ID", value=f"`{self.target_id}`", inline=True)
                embed.add_field(name="Submitted By", value=f"{interaction.user} ({interaction.user.id})", inline=True)
                embed.add_field(name="Reason", value=self.description.value, inline=False)
                await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Your appeal has been submitted successfully!\nStaff will review it shortly.",
            ephemeral=True
        )


# ==================== MANAGEMENT VIEWS ====================

class ManagementDropdown(discord.ui.Select):
    def __init__(self, target_id, bot):
        self.target_id = target_id
        self.bot = bot
        options = [
            discord.SelectOption(label="Security & Bans", description="Toggle bot access for this user.", emoji="🛡️", value="ban_menu"),
            discord.SelectOption(label="Profile Analytics", description="View detailed user metadata.", emoji="📊", value="stats"),
        ]
        super().__init__(placeholder="Choose a management category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "ban_menu":
            async with self.bot.db.execute("SELECT 1 FROM players_ban WHERE uid = ?", (self.target_id,)) as cursor:
                is_banned = bool(await cursor.fetchone())
            
            view = MoreOptionsView(self.target_id, self.bot, self.view.parent_view, is_banned)
            await interaction.response.edit_message(content="### 🛡️ Security Management\nSelect an action below:", view=view)
        else:
            await interaction.response.send_message("📊 Analytic functions coming soon!", ephemeral=True)


class BanReasonModal(discord.ui.Modal, title="Specify Ban Reason"):
    reason = discord.ui.TextInput(
        label="<:emoji_22:1503659968296124536>Reason for Ban", 
        placeholder="e.g. Exploiting economy glitches...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self, target_id, bot, parent_view):
        super().__init__()
        self.target_id = target_id
        self.bot = bot
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        # Ban user
        await self.bot.db.execute("INSERT OR IGNORE INTO players_ban (uid) VALUES (?)", (self.target_id,))
        await self.bot.db.commit()

        try:
            user = await self.bot.fetch_user(self.target_id)
            dm_embed = discord.Embed(
                title="⛔ Bot Ban Notice",
                description=(
                    f"You have been banned from the bot system.\n\n"
                    f"**Reason:** {self.reason.value}\n\n"
                    "If you believe this is a mistake, you can use the button below to apply for an unban."
                ),
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await user.send(embed=dm_embed, view=AppealView(self.bot, self.target_id))
        except:
            pass

        # Optional server ban
        try:
            guild_user = await interaction.guild.fetch_member(self.target_id)
            if guild_user:
                await interaction.guild.ban(guild_user, reason=f"Bot-ban by {interaction.user}: {self.reason.value}")
        except:
            pass

        await interaction.response.send_message(f"✅ User `{self.target_id}` has been banned and notified.", ephemeral=True)
        
        # Refresh view
        new_view = MoreOptionsView(self.target_id, self.bot, self.parent_view, is_banned=True)
        await interaction.edit_original_response(view=new_view)


class MoreOptionsView(discord.ui.View):
    def __init__(self, target_id, bot, parent_view, is_banned=False):
        super().__init__(timeout=60)
        self.target_id = target_id
        self.bot = bot
        self.parent_view = parent_view
        self.is_banned = is_banned

        # Button is now properly defined in __init__
        self.toggle_ban_button = discord.ui.Button(
            label="Unban from Bot" if is_banned else "Ban from Bot",
            style=discord.ButtonStyle.success if is_banned else discord.ButtonStyle.danger
        )
        self.toggle_ban_button.callback = self.toggle_ban
        self.add_item(self.toggle_ban_button)

        # Back button
        back_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.gray)
        back_button.callback = self.back_button
        self.add_item(back_button)

    async def toggle_ban(self, interaction: discord.Interaction):
        async with self.bot.db.execute("SELECT 1 FROM players_ban WHERE uid = ?", (self.target_id,)) as cursor:
            already_banned = bool(await cursor.fetchone())

        if already_banned:
            # Unban
            await self.bot.db.execute("DELETE FROM players_ban WHERE uid = ?", (self.target_id,))
            await self.bot.db.commit()
            await interaction.response.send_message("✅ User has been **Unbanned** from the bot.", ephemeral=True)
            
            new_view = MoreOptionsView(self.target_id, self.bot, self.parent_view, is_banned=False)
            await interaction.edit_original_response(view=new_view)
        else:
            # Ban
            await interaction.response.send_modal(BanReasonModal(self.target_id, self.bot, self.parent_view))

    async def back_button(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=None, view=self.parent_view)


class PlayerManagementView(discord.ui.View):
    def __init__(self, target_id, bot):
        super().__init__(timeout=60)
        self.target_id = target_id
        self.bot = bot

    @discord.ui.button(label="Set Balance", style=discord.ButtonStyle.secondary)
    async def set_bal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetBalanceModal(self.target_id, self.bot))

    @discord.ui.button(label="Remove User", style=discord.ButtonStyle.danger)
    async def remove_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.execute("DELETE FROM players WHERE uid = ?", (self.target_id,))
        await self.bot.db.commit()
        if self.target_id in getattr(self.bot, 'accepted_cache', set()):
            self.bot.accepted_cache.discard(self.target_id)
        await interaction.response.edit_message(content=f"✅ Player `{self.target_id}` has been removed.", embed=None, view=None)

    @discord.ui.button(label="More...", style=discord.ButtonStyle.gray)
    async def more_options(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        view.parent_view = self
        view.add_item(ManagementDropdown(self.target_id, self.bot))
        
        back = discord.ui.Button(label="Back", style=discord.ButtonStyle.gray)
        async def back_callback(inter):
            await inter.response.edit_message(view=self)
        back.callback = back_callback
        view.add_item(back)

        await interaction.response.edit_message(view=view)


class SetBalanceModal(discord.ui.Modal, title="Update Player Balance"):
    amount = discord.ui.TextInput(label="New Balance", placeholder="Enter numeric value...", required=True)

    def __init__(self, target_id, bot):
        super().__init__()
        self.target_id = target_id
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_bal = int(self.amount.value)
            await self.bot.db.execute("UPDATE players SET balance = ? WHERE uid = ?", (new_bal, self.target_id))
            await self.bot.db.commit()
            await interaction.response.send_message(f"✅ Updated balance to `{new_bal:,}`", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("<:emoji_26:1504070583145594942> Error: Balance must be a number.", ephemeral=True)


# Keep your existing execute_player_search function (unchanged)
async def execute_player_search(ctx, uid: int):
    async with ctx.bot.db.execute("SELECT balance, accepted FROM players WHERE uid = ?", (uid,)) as cursor:
        row = await cursor.fetchone()

    if not row:
        msg = f"❓ No database record for: `{uid}`"
        return await ctx.interaction.response.send_message(msg, ephemeral=True) if ctx.interaction else await ctx.send(msg)

    balance, accepted = row
    
    try:
        user = ctx.bot.get_user(uid) or await ctx.bot.fetch_user(uid)
        username = f"{user.name}"
        avatar = user.display_avatar.url
        joined_discord = discord.utils.format_dt(user.created_at, style="R")
    except discord.NotFound:
        username = "Unknown User"
        avatar = None
        joined_discord = "Unknown"

    mutual_count = len([g for g in ctx.bot.guilds if g.get_member(uid)])

    embed = discord.Embed(title="🔍 Player Intelligence Report", color=discord.Color.blue())
    if avatar: embed.set_thumbnail(url=avatar)
    embed.add_field(name="Identity", value=f"**User:** {username}\n**ID:** `{uid}`", inline=False)
    embed.add_field(name="Economy", value=f"**Balance:** 🪙 `{balance:,}`\n**Verified:** {'✅' if accepted else '<:emoji_26:1504070583145594942>'}", inline=True)
    embed.add_field(name="Social", value=f"**Mutual Servers:** `{mutual_count}`\n**Joined Discord:** {joined_discord}", inline=True)

    view = PlayerManagementView(uid, ctx.bot)
    
    if ctx.interaction:
        await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx.send(embed=embed, view=view)