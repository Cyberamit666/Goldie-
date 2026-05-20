from __future__ import annotations

import asyncio
import datetime
import os
import time
from collections import defaultdict

import discord
from discord.ext import commands

from core.db_manager import DatabaseManager
from core.verification import check_user_access, RulesView

# ── Anti-spam config ──────────────────────────────────────────────────────────
_SPAM_WINDOW     = 5.0   # seconds
_SPAM_MAX_MSG    = 6     # max messages per window before mute
_SPAM_MUTE_SECS  = 10.0  # how long to suppress responses after spam


class GameEngine(commands.Bot):
    def __init__(self, config) -> None:
        self.cfg = config
        self.dbs: DatabaseManager | None = None
        self.accepted_cache: set[int] = set()
        self.appeal_channel_id: int = config.APPEAL_CHANNEL_ID

        # Security: per-user message timestamps for anti-spam
        self._msg_times: dict[int, list[float]] = defaultdict(list)
        self._spam_muted: dict[int, float] = {}   # uid → mute_until monotonic

        intents = discord.Intents.all()
        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )

        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.add_check(check_user_access)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def setup_hook(self) -> None:
        self.dbs = DatabaseManager(self.cfg.DATA_DIR)
        await self.dbs.initialize()
        await self.dbs.migrate_legacy()

        # Pre-warm accepted-users cache
        async with self.dbs.players.execute(
            "SELECT uid FROM players WHERE accepted = 1"
        ) as cur:
            rows = await cur.fetchall()
        self.accepted_cache = {row[0] for row in rows}

        # Register persistent views so buttons survive restarts
        self.add_view(RulesView())

        # Auto-load every cog/*.py (skip dunders and sub-packages)
        for filename in sorted(os.listdir(self.cfg.COGS_DIR)):
            if filename.endswith(".py") and not filename.startswith("_"):
                ext = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(ext)
                    print(f"  ✅  {ext}")
                except Exception as exc:
                    print(f"  ❌  {ext}: {exc}")

        # Owner / moderation sub-package + slash command sync
        try:
            await self.load_extension("cogs.bot_moderation.main")
            await self.tree.sync()
            print("✅  Slash commands synced.")
        except Exception as exc:
            print(f"❌  bot_moderation: {exc}")

    async def on_ready(self) -> None:
        print("─" * 45)
        print(f"  Bot    : {self.user} ({self.user.id})")
        print(f"  Guilds : {len(self.guilds)}")
        print(f"  Cached : {len(self.accepted_cache)} verified users")
        print("─" * 45)

    # ── Message handler with anti-spam guard ──────────────────────────────────

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        uid = message.author.id
        now = time.monotonic()

        # Check if currently muted
        mute_until = self._spam_muted.get(uid, 0.0)
        if now < mute_until:
            return  # silently drop while muted

        # Slide the window
        times = self._msg_times[uid]
        times.append(now)
        # Remove entries older than the window
        cutoff = now - _SPAM_WINDOW
        self._msg_times[uid] = [t for t in times if t > cutoff]

        if len(self._msg_times[uid]) > _SPAM_MAX_MSG:
            self._spam_muted[uid] = now + _SPAM_MUTE_SECS
            self._msg_times[uid].clear()
            try:
                await message.channel.send(
                    f"⚠️ {message.author.mention} — slow down! You've been muted for "
                    f"{int(_SPAM_MUTE_SECS)}s.",
                    delete_after=_SPAM_MUTE_SECS,
                )
            except Exception:
                pass
            return

        await self.process_commands(message)

    # ── Error event — log unexpected gateway errors ───────────────────────────

    async def on_error(self, event: str, *args, **kwargs) -> None:
        import traceback
        print(f"[Gateway Error] event={event}")
        traceback.print_exc()

    # ── Graceful shutdown ─────────────────────────────────────────────────────

    async def close(self) -> None:
        if self.dbs:
            await self.dbs.close()
        await super().close()
