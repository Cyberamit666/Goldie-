import asyncio
import sys
from dotenv import load_dotenv
from config import Config
from core.bot import GameEngine

load_dotenv()


async def main() -> None:
    config = Config()

    if not config.validate():
        print("❌ ERROR: No TOKEN found. Set it in .env or Replit Secrets.")
        sys.exit(1)

    bot = GameEngine(config)

    try:
        async with bot:
            await bot.start(config.TOKEN)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚡ Shutdown requested. Goodbye.")
