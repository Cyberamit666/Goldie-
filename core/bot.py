import discord
from discord.ext import commands
import aiosqlite
import os
import datetime
from core.verification import check_user_access, RulesView

class GameEngine(commands.Bot):
    def __init__(self, config):
        self.cfg = config
        self.db = None
        self.accepted_cache = set()
        intents = discord.Intents.all()
        super().__init__(command_prefix=self.cfg.PREFIX, intents=intents, help_command=None)
        
        # Track start time for uptime calculation
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        
        # Global check from verification.py
        self.add_check(check_user_access)

        # === FIX: Set the channel ID immediately during initialization ===
        self.appeal_channel_id = getattr(self.cfg, 'APPEAL_CHANNEL_ID', None)

    async def setup_hook(self):
        # Database Initializations
        self.db = await aiosqlite.connect("database.db")
        await self.db.execute("CREATE TABLE IF NOT EXISTS players (uid INTEGER PRIMARY KEY, accepted BOOLEAN, balance INTEGER)")
        await self.db.execute("CREATE TABLE IF NOT EXISTS players_ban (uid INTEGER PRIMARY KEY, reason TEXT)")
        
        # === NEW: Ban Appeals Table ===
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS ban_appeals (
                uid INTEGER PRIMARY KEY,
                reason TEXT,
                appeal_time TEXT
            )
        """)
        
        os.makedirs("log", exist_ok=True)
        self.log_db = await aiosqlite.connect("log/setup_config.db")
        await self.log_db.execute("""
            CREATE TABLE IF NOT EXISTS channel_logs (
                guild_id INTEGER, 
                channel_id INTEGER, 
                PRIMARY KEY (guild_id, channel_id)
            )
        """)
        
        await self.db.commit()
        await self.log_db.commit()
        self.add_view(RulesView())
        
        # Load standard cogs
        for f in os.listdir('./cogs'):
            if f.endswith('.py') and not f.startswith('_'): 
                await self.load_extension(f'cogs.{f[:-3]}')

        # Load owner system and sync Slash Commands
        try:
            await self.load_extension('cogs.bot_moderation.main')
            await self.tree.sync()
            print("✅ Loaded Extension & Synced Slash Commands")
        except Exception as e:
            print(f"❌ Failed to load bot_moderation: {e}")

    async def on_ready(self):
        print("-------------------------------")
        print(f"Logged in as: {self.user.name}")
        print(f"Status: Online and Ready")
        print("-------------------------------")

        # === Appeal Channel Debug ===
        if self.appeal_channel_id:
            print(f"✅ Appeal Channel Set Successfully: {self.appeal_channel_id}")
        else:
            print("❌ APPEAL_CHANNEL_ID not found in Config class!")
            print(f"   Available attributes: {dir(self.cfg)}")

    async def on_message(self, message):
        if message.author.bot: return
        await self.process_commands(message)


if __name__ == "__main__":
    from config import Config
    config = Config()
    bot = GameEngine(config)
    bot.run(config.TOKEN)