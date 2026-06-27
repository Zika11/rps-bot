import os

# ========== متغيرات البوت الأساسية ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
FOUNDER_ID = int(os.getenv("FOUNDER_ID", 0))

# ========== قاعدة البيانات ==========
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_NAME = os.path.join(DATA_DIR, "rps_bot.db")

# ========== Google Sheets ==========
GOOGLE_SHEETS_CREDS = os.getenv("GOOGLE_SHEETS_CREDS", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# ========== Redis ==========
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "False").lower() == "true"

# ========== Logging ==========
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", 10_000_000))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 5))

# ========== التحقق ==========
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is required!")
if not FOUNDER_ID:
    raise ValueError("❌ FOUNDER_ID is required!")
