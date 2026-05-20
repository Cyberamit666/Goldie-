from __future__ import annotations

import datetime
from typing import Optional

import discord

from core.rules import get_rules_embed, send_welcome_dm


# ── Persistent Rules Gate View ────────────────────────────────────────────────

class RulesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅  Accept & Start",
        style=discord.ButtonStyle.success,
        custom_id="goldie_gate_v11",
    )
    async def accept(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        uid = interaction.user.id
        bot = interaction.client

        if uid in bot.accepted_cache:
            return await interaction.response.send_message(
                "⚠️ You have already accepted the rules!", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        username = str(interaction.user)
        starter = bot.cfg.STARTER_BALANCE

        await bot.dbs.players.execute(
            """
            INSERT INTO players (uid, username, balance, accepted, joined_bot)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(uid) DO UPDATE SET
                accepted   = 1,
                username   = excluded.username,
                joined_bot = COALESCE(joined_bot, excluded.joined_bot)
            """,
            (uid, username, starter, now),
        )
        await bot.dbs.players.commit()

        bot.accepted_cache.add(uid)

        try:
            await interaction.message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

        await send_welcome_dm(interaction.user)
        await interaction.followup.send(
            "✅ Verified! Check your DMs for your welcome package.", ephemeral=True
        )


# ── Gate functions ────────────────────────────────────────────────────────────

async def ban_gate(ctx) -> Optional[bool]:
    """Gate 0 — Block users in the bans table."""
    async with ctx.bot.dbs.bans.execute(
        "SELECT reason FROM bans WHERE uid = ?", (ctx.author.id,)
    ) as cur:
        row = await cur.fetchone()

    if row:
        reason = row[0] or "No reason provided."
        embed = discord.Embed(
            title="⛔ Access Denied",
            description=(
                f"You are **banned** from using this bot.\n"
                f"**Reason:** {reason}\n\n"
                "If you believe this is a mistake, contact staff."
            ),
            color=discord.Color.red(),
        )
        try:
            await ctx.send(embed=embed, delete_after=15)
        except Exception:
            pass
        return False
    return None


async def channel_gate(ctx) -> Optional[bool]:
    """Gate 1 — Ensure the command is in an authorised channel."""
    async with ctx.bot.dbs.logs.execute(
        "SELECT 1 FROM channel_logs WHERE guild_id = ?", (ctx.guild.id,)
    ) as cur:
        setup_exists = await cur.fetchone()

    if not setup_exists:
        if ctx.author.guild_permissions.administrator:
            cmd = ctx.bot.get_command("setup_channel")
            if cmd:
                await ctx.invoke(cmd)
        else:
            await ctx.send(
                "⚙️ **Setup Required** — Ask an administrator to run `go setup_channel`.",
                delete_after=10,
            )
        return False

    async with ctx.bot.dbs.logs.execute(
        "SELECT 1 FROM channel_logs WHERE guild_id = ? AND channel_id = ?",
        (ctx.guild.id, ctx.channel.id),
    ) as cur:
        if not await cur.fetchone():
            return False

    return None


async def verification_gate(ctx) -> Optional[bool]:
    """Gate 2 — Require rules acceptance before proceeding."""
    uid = ctx.author.id

    if uid in ctx.bot.accepted_cache:
        return True

    async with ctx.bot.dbs.players.execute(
        "SELECT accepted FROM players WHERE uid = ?", (uid,)
    ) as cur:
        row = await cur.fetchone()

    if row and row[0] == 1:
        ctx.bot.accepted_cache.add(uid)
        return True

    view = RulesView()
    await ctx.send(embed=get_rules_embed(ctx.author), view=view)
    return False


# ── Global check ──────────────────────────────────────────────────────────────

async def check_user_access(ctx) -> bool:
    """Applied to every prefix command via bot.add_check()."""
    if ctx.author.bot:
        return True

    # Bot owner bypasses all gates
    if await ctx.bot.is_owner(ctx.author):
        return True

    # Admins can always reach setup_channel
    if (
        ctx.command
        and ctx.command.name == "setup_channel"
        and ctx.author.guild_permissions.administrator
    ):
        return True

    for gate in (ban_gate, channel_gate, verification_gate):
        result = await gate(ctx)
        if result is True:
            return True
        if result is False:
            return False

    return True
