from __future__ import annotations

import datetime
import discord

from core.utils import win_rate, fmt_signed


# ── Appeal system ─────────────────────────────────────────────────────────────

class AppealView(discord.ui.View):
    def __init__(self, bot, target_id: int) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.target_id = target_id

    @discord.ui.button(
        label="📝 Submit Unban Appeal",
        style=discord.ButtonStyle.blurple,
        custom_id="goldie_appeal_v2",
    )
    async def appeal(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        async with self.bot.dbs.bans.execute(
            "SELECT 1 FROM ban_appeals WHERE uid = ? AND status = 'pending'",
            (self.target_id,),
        ) as cur:
            if await cur.fetchone():
                return await interaction.response.send_message(
                    "⚠️ You already have a pending appeal. Please wait for staff review.",
                    ephemeral=True,
                )
        await interaction.response.send_modal(AppealModal(self.bot, self.target_id))


class AppealModal(discord.ui.Modal, title="Unban Appeal"):
    reason = discord.ui.TextInput(
        label="Appeal Reason",
        placeholder="Explain why you should be unbanned…",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    def __init__(self, bot, target_id: int) -> None:
        super().__init__()
        self.bot = bot
        self.target_id = target_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)

        await self.bot.dbs.bans.execute(
            "INSERT INTO ban_appeals (uid, reason, appeal_time, status) VALUES (?, ?, ?, 'pending')",
            (self.target_id, self.reason.value, now.isoformat()),
        )
        await self.bot.dbs.bans.commit()

        # Notify staff channel
        ch_id = getattr(self.bot, "appeal_channel_id", None)
        if ch_id:
            channel = self.bot.get_channel(ch_id)
            if channel:
                embed = discord.Embed(
                    title="🔔 New Ban Appeal",
                    color=discord.Color.orange(),
                    timestamp=now,
                )
                embed.add_field(name="User ID",     value=f"`{self.target_id}`",                                    inline=True)
                embed.add_field(name="Submitted By", value=f"{interaction.user} (`{interaction.user.id}`)", inline=True)
                embed.add_field(name="Reason",       value=self.reason.value,                                       inline=False)
                view = AppealActionView(self.bot, self.target_id)
                await channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            "✅ Your appeal has been submitted. Staff will review it shortly.",
            ephemeral=True,
        )


class AppealActionView(discord.ui.View):
    """Sent to staff channel so they can approve/deny without typing commands."""

    def __init__(self, bot, target_id: int) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.target_id = target_id

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.bot.dbs.bans.execute("DELETE FROM bans WHERE uid = ?", (self.target_id,))
        await self.bot.dbs.bans.execute(
            "UPDATE ban_appeals SET status='approved' WHERE uid = ? AND status='pending'",
            (self.target_id,),
        )
        await self.bot.dbs.bans.commit()

        try:
            user = await self.bot.fetch_user(self.target_id)
            dm = discord.Embed(
                title="✅ Ban Appeal Approved",
                description="Your appeal has been reviewed and approved. You may now use the bot again.",
                color=discord.Color.green(),
            )
            await user.send(embed=dm)
        except Exception:
            pass

        await interaction.response.send_message(
            f"✅ User `{self.target_id}` has been unbanned and notified.", ephemeral=True
        )
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.bot.dbs.bans.execute(
            "UPDATE ban_appeals SET status='denied' WHERE uid = ? AND status='pending'",
            (self.target_id,),
        )
        await self.bot.dbs.bans.commit()

        try:
            user = await self.bot.fetch_user(self.target_id)
            dm = discord.Embed(
                title="❌ Ban Appeal Denied",
                description="Your appeal has been reviewed and denied. The ban remains in place.",
                color=discord.Color.red(),
            )
            await user.send(embed=dm)
        except Exception:
            pass

        await interaction.response.send_message(
            f"❌ Appeal for `{self.target_id}` has been denied.", ephemeral=True
        )
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)


# ── Ban management modals / views ─────────────────────────────────────────────

class BanReasonModal(discord.ui.Modal, title="Specify Ban Reason"):
    reason = discord.ui.TextInput(
        label="Reason for Ban",
        placeholder="e.g. Exploiting economy glitches…",
        style=discord.TextStyle.paragraph,
        required=True,
    )

    def __init__(self, bot, target_id: int, refresh_view) -> None:
        super().__init__()
        self.bot = bot
        self.target_id = target_id
        self.refresh_view = refresh_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        await self.bot.dbs.bans.execute(
            "INSERT OR REPLACE INTO bans (uid, reason, banned_by, banned_at) VALUES (?, ?, ?, ?)",
            (self.target_id, self.reason.value, interaction.user.id, now),
        )
        await self.bot.dbs.bans.commit()

        # Remove from verified cache
        self.bot.accepted_cache.discard(self.target_id)

        # DM the banned user
        try:
            user = await self.bot.fetch_user(self.target_id)
            dm = discord.Embed(
                title="⛔ Bot Ban Notice",
                description=(
                    "You have been **banned** from the Goldie economy bot.\n\n"
                    f"**Reason:** {self.reason.value}\n\n"
                    "If you believe this is a mistake, click the button below to appeal."
                ),
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            await user.send(embed=dm, view=AppealView(self.bot, self.target_id))
        except Exception:
            pass

        # Optional guild ban
        try:
            member = await interaction.guild.fetch_member(self.target_id)
            if member:
                await interaction.guild.ban(
                    member,
                    reason=f"Bot-ban by {interaction.user}: {self.reason.value}",
                )
        except Exception:
            pass

        await interaction.response.send_message(
            f"✅ User `{self.target_id}` has been banned and notified.", ephemeral=True
        )


class SetBalanceModal(discord.ui.Modal, title="Update Player Balance"):
    amount = discord.ui.TextInput(
        label="New Balance",
        placeholder="Enter a numeric value…",
        required=True,
    )

    def __init__(self, bot, target_id: int) -> None:
        super().__init__()
        self.bot = bot
        self.target_id = target_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            new_bal = int(self.amount.value.replace(",", ""))
            if new_bal < 0:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                "❌ Balance must be a non-negative integer.", ephemeral=True
            )

        await self.bot.dbs.players.execute(
            "UPDATE players SET balance = ? WHERE uid = ?",
            (new_bal, self.target_id),
        )
        await self.bot.dbs.players.commit()
        await interaction.response.send_message(
            f"✅ Balance updated to `🪙 {new_bal:,}`.", ephemeral=True
        )


class SecurityView(discord.ui.View):
    """Ban / unban sub-panel reached from PlayerManagementView."""

    def __init__(self, bot, target_id: int, is_banned: bool, back_view) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.target_id = target_id
        self.is_banned = is_banned
        self.back_view = back_view
        self._build()

    def _build(self) -> None:
        self.clear_items()

        toggle = discord.ui.Button(
            label="Unban from Bot" if self.is_banned else "Ban from Bot",
            style=discord.ButtonStyle.success if self.is_banned else discord.ButtonStyle.danger,
        )
        toggle.callback = self._toggle_ban
        self.add_item(toggle)

        back = discord.ui.Button(label="◀ Back", style=discord.ButtonStyle.gray)
        back.callback = self._back
        self.add_item(back)

    async def _toggle_ban(self, interaction: discord.Interaction) -> None:
        async with self.bot.dbs.bans.execute(
            "SELECT 1 FROM bans WHERE uid = ?", (self.target_id,)
        ) as cur:
            currently_banned = bool(await cur.fetchone())

        if currently_banned:
            await self.bot.dbs.bans.execute(
                "DELETE FROM bans WHERE uid = ?", (self.target_id,)
            )
            await self.bot.dbs.bans.commit()
            await interaction.response.send_message(
                f"✅ User `{self.target_id}` has been **unbanned**.", ephemeral=True
            )
            self.is_banned = False
            self._build()
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.send_modal(
                BanReasonModal(self.bot, self.target_id, self)
            )

    async def _back(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(view=self.back_view)


class PlayerManagementView(discord.ui.View):
    def __init__(self, bot, target_id: int) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.target_id = target_id

    @discord.ui.button(label="💰 Set Balance", style=discord.ButtonStyle.secondary)
    async def set_balance(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(SetBalanceModal(self.bot, self.target_id))

    @discord.ui.button(label="🛡️ Security", style=discord.ButtonStyle.danger)
    async def security(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        async with self.bot.dbs.bans.execute(
            "SELECT 1 FROM bans WHERE uid = ?", (self.target_id,)
        ) as cur:
            is_banned = bool(await cur.fetchone())
        view = SecurityView(self.bot, self.target_id, is_banned, back_view=self)
        await interaction.response.edit_message(
            content="### 🛡️ Security Management", view=view
        )

    @discord.ui.button(label="🗑️ Remove User", style=discord.ButtonStyle.danger)
    async def remove_user(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.bot.dbs.players.execute(
            "DELETE FROM players WHERE uid = ?", (self.target_id,)
        )
        await self.bot.dbs.players.commit()
        self.bot.accepted_cache.discard(self.target_id)
        await interaction.response.edit_message(
            content=f"✅ Player `{self.target_id}` has been permanently removed.",
            embed=None,
            view=None,
        )


# ── Core search function ──────────────────────────────────────────────────────

async def execute_player_search(ctx, uid: int) -> None:
    """Build and send a full player intelligence report."""
    bot = ctx.bot

    # Fetch player record
    async with bot.dbs.players.execute(
        """SELECT balance, accepted, total_games, total_wins, total_losses,
                  total_wagered, total_profit, joined_bot
           FROM players WHERE uid = ?""",
        (uid,),
    ) as cur:
        row = await cur.fetchone()

    async def send(content=None, embed=None, view=None, ephemeral=True):
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(
                    content=content, embed=embed, view=view, ephemeral=ephemeral
                )
            else:
                await ctx.interaction.followup.send(
                    content=content, embed=embed, view=view, ephemeral=ephemeral
                )
        else:
            await ctx.send(content=content, embed=embed, view=view)

    if not row:
        return await send(content=f"❓ No database record found for UID `{uid}`.")

    balance, accepted, games, wins, losses, wagered, profit, joined_bot = row

    # Discord identity
    try:
        user = bot.get_user(uid) or await bot.fetch_user(uid)
        username  = str(user)
        avatar    = user.display_avatar.url
        discord_created = discord.utils.format_dt(user.created_at, style="R")
    except discord.NotFound:
        username  = f"Unknown User ({uid})"
        avatar    = None
        discord_created = "Unknown"

    # Mutual servers
    mutual_count = sum(1 for g in bot.guilds if g.get_member(uid))

    # Ban status
    async with bot.dbs.bans.execute(
        "SELECT reason, banned_by, banned_at FROM bans WHERE uid = ?", (uid,)
    ) as cur:
        ban_row = await cur.fetchone()

    # Pending appeal
    async with bot.dbs.bans.execute(
        "SELECT 1 FROM ban_appeals WHERE uid = ? AND status='pending'", (uid,)
    ) as cur:
        has_appeal = bool(await cur.fetchone())

    # Win rate
    wr = win_rate(wins, games)

    # Today's activity
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    async with bot.dbs.economy.execute(
        "SELECT COUNT(*), COALESCE(SUM(profit),0) FROM transactions WHERE uid = ? AND DATE(timestamp) = ?",
        (uid, today),
    ) as cur:
        today_row = await cur.fetchone()
    d_games, d_profit = today_row[0], today_row[1]

    # Leaderboard rank by balance
    async with bot.dbs.players.execute(
        "SELECT COUNT(*) FROM players WHERE balance > ? AND accepted = 1", (balance,)
    ) as cur:
        rank_row = await cur.fetchone()
    rank = (rank_row[0] + 1) if rank_row else "?"

    # Build embed
    status_line = "⛔ **BANNED**" if ban_row else ("✅ Verified" if accepted else "❌ Unverified")
    profit_color = discord.Color.green() if profit >= 0 else discord.Color.red()

    embed = discord.Embed(
        title="🔍 Player Intelligence Report",
        color=profit_color,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    if avatar:
        embed.set_thumbnail(url=avatar)

    embed.add_field(
        name="👤 Identity",
        value=(
            f"Username: **{username}**\n"
            f"ID: `{uid}`\n"
            f"Status: {status_line}\n"
            f"Discord Age: {discord_created}"
        ),
        inline=False,
    )

    if joined_bot:
        try:
            dt = datetime.datetime.fromisoformat(joined_bot)
            bot_join = discord.utils.format_dt(dt, style="D")
        except ValueError:
            bot_join = joined_bot
    else:
        bot_join = "Not registered"

    embed.add_field(
        name="💰 Economy",
        value=(
            f"Balance: `🪙 {balance:,}`\n"
            f"Net Profit: `{fmt_signed(profit)}`\n"
            f"Total Wagered: `🪙 {wagered:,}`\n"
            f"LB Rank: `#{rank}`"
        ),
        inline=True,
    )
    embed.add_field(
        name="🎮 Game Stats",
        value=(
            f"Games: `{games:,}`\n"
            f"Wins / Losses: `{wins:,}` / `{losses:,}`\n"
            f"Win Rate: `{wr:.1f}%`\n"
            f"Bot Join: {bot_join}"
        ),
        inline=True,
    )
    embed.add_field(
        name="🌐 Social",
        value=(
            f"Mutual Servers: `{mutual_count}`\n"
            f"Today's Games: `{d_games}`\n"
            f"Today's P&L: `{fmt_signed(d_profit)}`"
        ),
        inline=True,
    )

    if ban_row:
        ban_reason, banned_by, banned_at = ban_row
        try:
            dt = datetime.datetime.fromisoformat(banned_at)
            ban_time = discord.utils.format_dt(dt, style="R")
        except ValueError:
            ban_time = banned_at
        embed.add_field(
            name="⛔ Ban Info",
            value=(
                f"Reason: {ban_reason}\n"
                f"Banned By: `{banned_by}`\n"
                f"When: {ban_time}\n"
                f"Pending Appeal: `{'Yes' if has_appeal else 'No'}`"
            ),
            inline=False,
        )

    embed.set_footer(text=f"Searched by {ctx.author}")

    view = PlayerManagementView(bot, uid)
    await send(embed=embed, view=view)
