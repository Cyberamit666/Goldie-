import asyncio
import os
from core.bot import GameEngine
from config import Config
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Initialize the Config class from config.py
    config = Config()
    
    if not config.TOKEN:
        print("❌ ERROR: No Token found in .env or Config!")
        return

    bot = GameEngine(config)
    async with bot:
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")