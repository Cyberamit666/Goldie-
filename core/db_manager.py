import os
import datetime
import aiosqlite


class DatabaseManager:
    """
    Manages four separate lightweight SQLite databases:
      - players.db  : accounts, balance, game stats
      - bans.db     : ban records and appeals
      - economy.db  : per-game transaction log
      - logs.db     : guild channel setup and action audit log
    """

    def __init__(self, data_dir: str = "./data") -> None:
        self.data_dir = data_dir
        self.players: aiosqlite.Connection | None = None
        self.bans: aiosqlite.Connection | None = None
        self.economy: aiosqlite.Connection | None = None
        self.logs: aiosqlite.Connection | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)

        self.players = await aiosqlite.connect(f"{self.data_dir}/players.db")
        self.bans    = await aiosqlite.connect(f"{self.data_dir}/bans.db")
        self.economy = await aiosqlite.connect(f"{self.data_dir}/economy.db")
        self.logs    = await aiosqlite.connect(f"{self.data_dir}/logs.db")

        await self._configure_all()
        await self._create_tables()

    async def migrate_legacy(self) -> None:
        """One-time migration from the original databases. Safe to call every boot."""
        await self._migrate_players_db()
        await self._migrate_channel_logs()

    async def _migrate_players_db(self, path: str = "database.db") -> None:
        if not os.path.exists(path):
            return
        print("🔄  Legacy database.db detected — migrating players & bans …")
        try:
            old = await aiosqlite.connect(path)

            async with old.execute("SELECT uid, accepted, balance FROM players") as cur:
                player_rows = await cur.fetchall()
            for uid, accepted, balance in player_rows:
                await self.players.execute(
                    "INSERT OR IGNORE INTO players (uid, balance, accepted) VALUES (?, ?, ?)",
                    (uid, balance, accepted),
                )
            await self.players.commit()

            try:
                async with old.execute("SELECT uid FROM players_ban") as cur:
                    ban_rows = await cur.fetchall()
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                for (uid,) in ban_rows:
                    await self.bans.execute(
                        "INSERT OR IGNORE INTO bans (uid, reason, banned_at) VALUES (?, ?, ?)",
                        (uid, "Migrated from legacy database", now),
                    )
                await self.bans.commit()
            except Exception:
                ban_rows = []

            await old.close()
            print(f"✅  Migrated {len(player_rows)} players, {len(ban_rows)} bans.")
        except Exception as exc:
            print(f"⚠️   Players migration warning: {exc}")

    async def _migrate_channel_logs(self, path: str = "log/setup_config.db") -> None:
        if not os.path.exists(path):
            return
        print("🔄  Legacy setup_config.db detected — migrating channel config …")
        try:
            old = await aiosqlite.connect(path)
            async with old.execute("SELECT guild_id, channel_id FROM channel_logs") as cur:
                rows = await cur.fetchall()
            for guild_id, channel_id in rows:
                await self.logs.execute(
                    "INSERT OR IGNORE INTO channel_logs (guild_id, channel_id) VALUES (?, ?)",
                    (guild_id, channel_id),
                )
            await self.logs.commit()
            await old.close()
            print(f"✅  Migrated {len(rows)} channel log entries.")
        except Exception as exc:
            print(f"⚠️   Channel logs migration warning: {exc}")

    async def close(self) -> None:
        for db in (self.players, self.bans, self.economy, self.logs):
            if db:
                try:
                    await db.close()
                except Exception:
                    pass

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _configure_all(self) -> None:
        """Apply performance + safety PRAGMAs to every database."""
        for db in (self.players, self.bans, self.economy, self.logs):
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA cache_size=2000")
            await db.execute("PRAGMA temp_store=MEMORY")
            await db.execute("PRAGMA foreign_keys=ON")

    async def _create_tables(self) -> None:

        # ── players.db ───────────────────────────────────────────────────────
        await self.players.execute("""
            CREATE TABLE IF NOT EXISTS players (
                uid           INTEGER PRIMARY KEY,
                username      TEXT    DEFAULT '',
                balance       INTEGER DEFAULT 0,
                accepted      INTEGER DEFAULT 0,
                joined_bot    TEXT    DEFAULT NULL,
                total_games   INTEGER DEFAULT 0,
                total_wins    INTEGER DEFAULT 0,
                total_losses  INTEGER DEFAULT 0,
                total_wagered INTEGER DEFAULT 0,
                total_profit  INTEGER DEFAULT 0
            )
        """)
        await self.players.commit()

        # ── bans.db ──────────────────────────────────────────────────────────
        await self.bans.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                uid       INTEGER PRIMARY KEY,
                reason    TEXT    DEFAULT 'No reason provided',
                banned_by INTEGER DEFAULT 0,
                banned_at TEXT    NOT NULL
            )
        """)
        await self.bans.execute("""
            CREATE TABLE IF NOT EXISTS ban_appeals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                uid         INTEGER NOT NULL,
                reason      TEXT    NOT NULL,
                appeal_time TEXT    NOT NULL,
                status      TEXT    DEFAULT 'pending'
            )
        """)
        await self.bans.commit()

        # ── economy.db ───────────────────────────────────────────────────────
        await self.economy.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                uid       INTEGER NOT NULL,
                game      TEXT    NOT NULL,
                bet       INTEGER NOT NULL,
                profit    INTEGER NOT NULL,
                timestamp TEXT    NOT NULL
            )
        """)
        await self.economy.execute(
            "CREATE INDEX IF NOT EXISTS idx_tx_uid_time ON transactions (uid, timestamp)"
        )
        await self.economy.commit()

        # ── logs.db ──────────────────────────────────────────────────────────
        await self.logs.execute("""
            CREATE TABLE IF NOT EXISTS channel_logs (
                guild_id   INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, channel_id)
            )
        """)
        await self.logs.execute("""
            CREATE TABLE IF NOT EXISTS action_logs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id  INTEGER,
                action    TEXT    NOT NULL,
                actor_id  INTEGER,
                target_id INTEGER,
                details   TEXT,
                timestamp TEXT    NOT NULL
            )
        """)
        await self.logs.commit()
