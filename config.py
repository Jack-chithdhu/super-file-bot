#(©)CodeXBotz - Enhanced by Claude

import os
import logging
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv()

# ── Core ──────────────────────────────────────────────────────────────────────
TG_BOT_TOKEN  = os.environ.get("TG_BOT_TOKEN", "")
APP_ID        = int(os.environ.get("APP_ID", "0"))
API_HASH      = os.environ.get("API_HASH", "")
_ch = os.environ.get("CHANNEL_ID", "0")
CHANNEL_ID = _ch if _ch.startswith("@") else int(_ch)
OWNER_ID      = int(os.environ.get("OWNER_ID", "0"))
PORT          = int(os.environ.get("PORT", "8080"))

# ── Database ──────────────────────────────────────────────────────────────────
DB_URI   = os.environ.get("DATABASE_URL", "")
DB_NAME  = os.environ.get("DATABASE_NAME", "filesharexbot")

# ── Force Subscribe ───────────────────────────────────────────────────────────
FORCE_SUB_CHANNEL   = int(os.environ.get("FORCE_SUB_CHANNEL", "0"))
JOIN_REQUEST_ENABLE = os.environ.get("JOIN_REQUEST_ENABLED", None)

# ── Request Channel (movie/anime requests forwarded here) ─────────────────────
REQUEST_CHANNEL_ID  = int(os.environ.get("REQUEST_CHANNEL_ID", "0"))

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

# ── Messages & UI ─────────────────────────────────────────────────────────────
START_PIC = os.environ.get("START_PIC", "")

START_MSG = os.environ.get(
    "START_MESSAGE",
    "👋 <b>Hello {first}!</b>\n\n"
    "Welcome to <b>File Sharing Bot</b> 🗂️\n\n"
    "I store private files and share them via special links.\n\n"
    "🎬 Use /request to request a movie or anime\n"
    "💬 Use /support to chat with admin\n"
    "💎 Use /premium to check your subscription"
)

FORCE_MSG = os.environ.get(
    "FORCE_SUB_MESSAGE",
    "👋 <b>Hey {mention}!</b>\n\n"
    "🔒 <b>Access Restricted</b>\n\n"
    "You must join our channel to use this bot.\n"
    "Click the button below, then tap <b>Try Again</b>."
)

CUSTOM_CAPTION   = os.environ.get("CUSTOM_CAPTION", None)
PROTECT_CONTENT  = os.environ.get("PROTECT_CONTENT", "False") == "True"

AUTO_DELETE_TIME     = int(os.getenv("AUTO_DELETE_TIME", "0"))
AUTO_DELETE_MSG      = os.environ.get(
    "AUTO_DELETE_MSG",
    "⏳ <b>Auto-Delete Notice</b>\n\nThis file will be deleted in <b>{time} seconds</b>. Please save it!"
)
AUTO_DEL_SUCCESS_MSG = os.environ.get(
    "AUTO_DEL_SUCCESS_MSG",
    "✅ <b>File deleted successfully.</b> Thank you for using our service!"
)

DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == "True"
BOT_STATS_TEXT         = "<b>📊 BOT UPTIME</b>\n⏱ {uptime}"
USER_REPLY_TEXT        = "❌ I only share files via special links. Use /request for requests or /support to contact admin."

# ── Premium ───────────────────────────────────────────────────────────────────
PREMIUM_DURATION_DAYS = int(os.environ.get("PREMIUM_DURATION_DAYS", "30"))
FREE_DAILY_LIMIT      = int(os.environ.get("FREE_DAILY_LIMIT", "20"))

# ── Admins (from env — these are always admins regardless of DB) ──────────────
try:
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split() if x]
except ValueError:
    raise Exception("ADMINS list contains invalid integers.")

ADMINS.append(OWNER_ID)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(LOG_FILE_NAME, maxBytes=50_000_000, backupCount=10),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
