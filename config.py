import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv("TOKEN")
    PG_DSN = os.getenv("PG_DSN")
    # We use BOT_PREFIX to avoid conflict with Termux's system $PREFIX
    PREFIX = os.getenv("BOT_PREFIX", " go ") 
    COGS_DIR = "./cogs"

    # ====================== STAFF APPEALS CHANNEL ======================
    # Change this number to your actual staff appeals channel ID
    APPEAL_CHANNEL_ID = 1504065884967403580  
    # ===================================================================