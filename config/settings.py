# config/settings.py
"""
متغيرات البيئة - Environment Variables
يتم قراءتها من os.getenv()
"""

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

# ========== التحقق من المتغيرات الإجبارية ==========
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is required! Set it in environment variables.")
if not FOUNDER_ID:
    raise ValueError("❌ FOUNDER_ID is required! Set it in environment variables.")
