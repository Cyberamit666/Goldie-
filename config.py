import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TOKEN: str = os.getenv("TOKEN", "")
    PG_DSN: str = os.getenv("PG_DSN", "")
    PREFIX: str = os.getenv("BOT_PREFIX", " go ")

    COGS_DIR: str = "./cogs"
    DATA_DIR: str = "./data"

    # Staff channel for ban appeals
    APPEAL_CHANNEL_ID: int = int(os.getenv("APPEAL_CHANNEL_ID", "1504065884967403580"))

    # Economy settings
    STARTER_BALANCE: int = 1_000
    MAX_BET: int = 300_000

    # Game cooldowns (seconds)
    CF_COOLDOWN: float = 3.0

    def validate(self) -> bool:
        return bool(self.TOKEN)
