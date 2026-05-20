from __future__ import annotations

import datetime
import time
import discord


async def execute_stats(ctx) -> None:
    """Render a detailed bot diagnostics embed."""
    bot = ctx.bot
    now = datetime.datetime.now(datetime.timezone.utc)

    # DB latency
    t0 = time.perf_counter()
    async with bot.dbs.players.execute("SELECT 1") as cur:
        await cur.fetchone()
    db_ms = round((time.perf_counter() - t0) * 1000, 2)

    # API / WS latency
    api_ms = round(bot.latency * 1000, 2)

    # Response time
    if hasattr(ctx, "interaction") and ctx.interaction:
        created = ctx.interaction.created_at
    else:
        created = getattr(ctx.message, "created_at", now)
    resp_ms = round((now - created).total_seconds() * 1000, 2)

    # Uptime
    delta = now - bot.start_time
    days, rem  = divmod(int(delta.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{days}d {hours}h {mins}m {secs}s"

    # Counts
    guild_count  = len(bot.guilds)
    member_count = sum(g.member_count or 0 for g in bot.guilds)

    async with bot.dbs.players.execute("SELECT COUNT(*) FROM players WHERE accepted=1") as cur:
        verified_count = (await cur.fetchone())[0]

    async with bot.dbs.players.execute("SELECT COUNT(*) FROM players") as cur:
        total_players = (await cur.fetchone())[0]

    async with bot.dbs.bans.execute("SELECT COUNT(*) FROM bans") as cur:
        ban_count = (await cur.fetchone())[0]

    async with bot.dbs.economy.execute("SELECT COUNT(*), COALESCE(SUM(bet),0) FROM transactions") as cur:
        tx_row = await cur.fetchone()
    tx_count  = tx_row[0]
    tx_wagered = tx_row[1]

    embed = discord.Embed(
        title="📡 Goldie System Diagnostics",
        color=discord.Color.gold(),
        timestamp=now,
    )
    embed.add_field(
        name="⚡ Performance",
        value=(
            f"API Latency : `{api_ms} ms`\n"
            f"DB Latency  : `{db_ms} ms`\n"
            f"Resp Time   : `{resp_ms} ms`\n"
            f"Status      : `🟢 Online`"
        ),
        inline=True,
    )
    embed.add_field(
        name="🌐 Network",
        value=(
            f"Servers : `{guild_count}`\n"
            f"Members : `{member_count:,}`\n"
            f"Uptime  : `{uptime_str}`\n"
            f"Shard   : `{bot.shard_id or 0}`"
        ),
        inline=True,
    )
    embed.add_field(
        name="🗄️ Database",
        value=(
            f"Total Players  : `{total_players:,}`\n"
            f"Verified       : `{verified_count:,}`\n"
            f"Active Bans    : `{ban_count}`\n"
            f"Transactions   : `{tx_count:,}`\n"
            f"Total Wagered  : `🪙 {tx_wagered:,}`"
        ),
        inline=False,
    )
    embed.set_footer(text=f"Requested by {ctx.author}")

    if hasattr(ctx, "interaction") and ctx.interaction:
        await ctx.interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx.send(embed=embed)
