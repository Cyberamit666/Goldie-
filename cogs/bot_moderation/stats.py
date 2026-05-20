import discord
import time
import datetime

async def execute_stats(ctx):
    # 1. Database Latency
    start_db = time.perf_counter()
    async with ctx.bot.db.execute("SELECT 1") as cursor:
        await cursor.fetchone()
    db_latency = round((time.perf_counter() - start_db) * 1000, 2)

    # 2. API Latency & Latency
    api_latency = round(ctx.bot.latency * 1000, 2)

    # 3. Response Time Calculation
    if hasattr(ctx, "interaction") and ctx.interaction:
        start_time = ctx.interaction.created_at
    else:
        start_time = ctx.message.created_at if ctx.message else datetime.datetime.now(datetime.timezone.utc)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    resp_time = round((now - start_time).total_seconds() * 1000, 2)

    # 4. Uptime Calculation
    delta = now - ctx.bot.start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

    # 5. Accurate Counts
    server_count = len(ctx.bot.guilds)
    member_count = sum(g.member_count for g in ctx.bot.guilds if g.member_count)
    
    # Querying the database for users who have accepted the rules
    async with ctx.bot.db.execute("SELECT COUNT(*) FROM players") as cursor:
        row = await cursor.fetchone()
        user_count = row[0] if row else 0

    stats_msg = (
        f"> API Latency : `{api_latency}ms`\n"
        f"> Database Latency : `{db_latency}ms`\n"
        f"> Response Time : `{resp_time}ms`\n"
        f"> Latency : `{api_latency}ms`\n"
        f"> Status : `Online`\n"
        f"> Ratelimited : `No`\n"
        f"> Uptime : `{days}d, {hours}h, {minutes}m`\n"
        f"> Servers : `{server_count}`\n"
        f"> Members : `{member_count}`\n"
        f"> User count : `{user_count}`"
    )
    
    if hasattr(ctx, "interaction") and ctx.interaction:
        # Ensuring the owner-only stats are sent as a standard response or ephemeral as needed
        await ctx.interaction.response.send_message(stats_msg, ephemeral=False)
    else:
        await ctx.send(stats_msg)