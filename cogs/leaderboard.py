from __future__ import annotations

import datetime
import discord
from discord.ext import commands

from core.utils import rank_emoji, fmt_signed

PER_PAGE = 10

LB_META = [
    ("💰 Cash",    "cash",   discord.ButtonStyle.success),
    ("🏆 Wins",    "wins",   discord.ButtonStyle.blurple),
    ("📈 Profit",  "profit", discord.ButtonStyle.success),
    ("📅 Daily",   "daily",  discord.ButtonStyle.secondary),
    ("🗓️ Weekly", "weekly", discord.ButtonStyle.secondary),
]


class LeaderboardView(discord.ui.View):
    def __init__(self, bot, author_id: int, lb_type: str = "cash", page: int = 0) -> None:
        super().__init__(timeout=120)
        self.bot = bot
        self.author_id = author_id
        self.lb_type = lb_type
        self.page = page
        self.total_pages = 1
        self._rebuild()

    # ── UI construction ───────────────────────────────────────────────────────

    def _rebuild(self) -> None:
        self.clear_items()

        # Type selector buttons (row 0)
        for label, ltype, _ in LB_META:
            btn = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.primary
                if ltype == self.lb_type
                else discord.ButtonStyle.secondary,
                row=0,
            )
            btn.callback = self._make_type_cb(ltype)
            self.add_item(btn)

        # Navigation buttons (row 1)
        prev_btn = discord.ui.Button(
            label="◀ Prev",
            style=discord.ButtonStyle.gray,
            row=1,
            disabled=self.page == 0,
        )
        prev_btn.callback = self._prev
        self.add_item(prev_btn)

        next_btn = discord.ui.Button(
            label="Next ▶",
            style=discord.ButtonStyle.gray,
            row=1,
            disabled=(self.page + 1) >= self.total_pages,
        )
        next_btn.callback = self._next
        self.add_item(next_btn)

    def _make_type_cb(self, ltype: str):
        async def cb(interaction: discord.Interaction) -> None:
            self.lb_type = ltype
            self.page = 0
            embed = await self._build_embed()
            self._rebuild()
            await interaction.response.edit_message(embed=embed, view=self)
        return cb

    async def _prev(self, interaction: discord.Interaction) -> None:
        self.page = max(0, self.page - 1)
        embed = await self._build_embed()
        self._rebuild()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _next(self, interaction: discord.Interaction) -> None:
        self.page += 1
        embed = await self._build_embed()
        self._rebuild()
        await interaction.response.edit_message(embed=embed, view=self)

    # ── Data fetching ─────────────────────────────────────────────────────────

    async def _fetch_usernames(self, uids: list[int]) -> dict[int, str]:
        if not uids:
            return {}
        ph = ",".join("?" * len(uids))
        async with self.bot.dbs.players.execute(
            f"SELECT uid, username FROM players WHERE uid IN ({ph})", uids
        ) as cur:
            rows = await cur.fetchall()
        return {uid: (name or f"User {uid}") for uid, name in rows}

    async def _count_players(self) -> int:
        async with self.bot.dbs.players.execute(
            "SELECT COUNT(*) FROM players WHERE accepted = 1"
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else 0

    async def _build_embed(self) -> discord.Embed:
        offset = self.page * PER_PAGE
        ltype = self.lb_type
        now = datetime.datetime.now(datetime.timezone.utc)

        if ltype == "cash":
            async with self.bot.dbs.players.execute(
                "SELECT uid, username, balance FROM players WHERE accepted=1 "
                "ORDER BY balance DESC LIMIT ? OFFSET ?",
                (PER_PAGE, offset),
            ) as cur:
                rows = await cur.fetchall()
            total = await self._count_players()
            self.total_pages = max(1, -(-total // PER_PAGE))
            lines = [
                f"{rank_emoji(offset + i + 1)} **{u or f'User {uid}'}** — 🪙 `{bal:,}`"
                for i, (uid, u, bal) in enumerate(rows)
            ]
            embed = discord.Embed(
                title="💰 Cash Leaderboard",
                description="\n".join(lines) or "No data yet.",
                color=discord.Color.gold(),
            )

        elif ltype == "wins":
            async with self.bot.dbs.players.execute(
                "SELECT uid, username, total_wins FROM players WHERE accepted=1 "
                "ORDER BY total_wins DESC LIMIT ? OFFSET ?",
                (PER_PAGE, offset),
            ) as cur:
                rows = await cur.fetchall()
            total = await self._count_players()
            self.total_pages = max(1, -(-total // PER_PAGE))
            lines = [
                f"{rank_emoji(offset + i + 1)} **{u or f'User {uid}'}** — 🏆 `{wins:,} wins`"
                for i, (uid, u, wins) in enumerate(rows)
            ]
            embed = discord.Embed(
                title="🏆 Wins Leaderboard",
                description="\n".join(lines) or "No data yet.",
                color=discord.Color.blue(),
            )

        elif ltype == "profit":
            async with self.bot.dbs.players.execute(
                "SELECT uid, username, total_profit FROM players WHERE accepted=1 "
                "ORDER BY total_profit DESC LIMIT ? OFFSET ?",
                (PER_PAGE, offset),
            ) as cur:
                rows = await cur.fetchall()
            total = await self._count_players()
            self.total_pages = max(1, -(-total // PER_PAGE))
            lines = [
                f"{rank_emoji(offset + i + 1)} **{u or f'User {uid}'}** — `{fmt_signed(p)}`"
                for i, (uid, u, p) in enumerate(rows)
            ]
            embed = discord.Embed(
                title="📈 All-Time Profit Leaderboard",
                description="\n".join(lines) or "No data yet.",
                color=discord.Color.green(),
            )

        else:
            # daily / weekly — query from economy.db then look up names
            if ltype == "daily":
                date_filter = f"DATE(timestamp) = '{now.strftime('%Y-%m-%d')}'"
                title = "📅 Daily Profit Leaderboard"
                color = discord.Color.orange()
            else:
                week_start = (now - datetime.timedelta(days=now.weekday())).strftime("%Y-%m-%d")
                date_filter = f"DATE(timestamp) >= '{week_start}'"
                title = "🗓️ Weekly Profit Leaderboard"
                color = discord.Color.purple()

            async with self.bot.dbs.economy.execute(
                f"SELECT uid, SUM(profit) AS net FROM transactions "
                f"WHERE {date_filter} GROUP BY uid ORDER BY net DESC LIMIT ? OFFSET ?",
                (PER_PAGE, offset),
            ) as cur:
                rows = await cur.fetchall()

            async with self.bot.dbs.economy.execute(
                f"SELECT COUNT(DISTINCT uid) FROM transactions WHERE {date_filter}"
            ) as cur:
                t_row = await cur.fetchone()
            total = t_row[0] if t_row else 0
            self.total_pages = max(1, -(-total // PER_PAGE))

            uids = [r[0] for r in rows]
            names = await self._fetch_usernames(uids)
            lines = [
                f"{rank_emoji(offset + i + 1)} **{names.get(uid, f'User {uid}')}** — `{fmt_signed(net)}`"
                for i, (uid, net) in enumerate(rows)
            ]
            embed = discord.Embed(
                title=title, description="\n".join(lines) or "No data yet.", color=color
            )

        embed.set_footer(text=f"Page {self.page + 1}/{self.total_pages} • Goldie Economy")
        return embed


class LeaderboardCog(commands.Cog, name="Leaderboard"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(name="lb", aliases=["leaderboard", "top", "rank"])
    async def leaderboard(self, ctx) -> None:
        """View ranked leaderboards: cash, wins, profit, daily, weekly."""
        view = LeaderboardView(self.bot, ctx.author.id)
        embed = await view._build_embed()
        view._rebuild()
        await ctx.send(embed=embed, view=view)


async def setup(bot) -> None:
    await bot.add_cog(LeaderboardCog(bot))
