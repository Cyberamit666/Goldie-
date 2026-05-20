from __future__ import annotations

import datetime
import os

import discord
from discord.ext import commands

from core.db_manager import DatabaseManager
from core.verification import check_user_access, RulesView


class GameEngine(commands.Bot):
    def __init__(self, config) -> None:
        self.cfg = config
        self.dbs: DatabaseManager | None = None
        self.accepted_cache: set[int] = set()
        self.appeal_channel_id: int = config.APPEAL_CHANNEL_ID

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
        # Initialise all databases
        self.dbs = DatabaseManager(self.cfg.DATA_DIR)
        await self.dbs.initialize()
        await self.dbs.migrate_legacy()

        # Pre-warm accepted cache
        async with self.dbs.players.execute(
            "SELECT uid FROM players WHERE accepted = 1"
        ) as cur:
            rows = await cur.fetchall()
        self.accepted_cache = {row[0] for row in rows}

        # Register persistent views (survive bot restarts)
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

        # Load owner / moderation sub-package and sync slash commands
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

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self) -> None:
        if self.dbs:
            await self.dbs.close()
        await super().close()
