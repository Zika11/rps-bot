# config/settings.py
"""
متغيرات البيئة والإعدادات الديناميكية.
كل القيم اللي ممكن تتغير حسب البيئة (تطوير، إنتاج) أو حسب إعدادات المستخدم.
"""

import os

# ========== توكن البوت ==========
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

# ========== إعدادات اللعبة الديناميكية ==========
DEFAULT_RATING = int(os.getenv("DEFAULT_RATING", 1000))
RATING_K = int(os.getenv("RATING_K", 32))

TREASURE_BOX_PRICE = int(os.getenv("TREASURE_BOX_PRICE", 100))
WHEEL_COST = int(os.getenv("WHEEL_COST", 5))

MAX_BATTLE_PASS_LEVEL = int(os.getenv("MAX_BATTLE_PASS_LEVEL", 10))
BATTLE_PASS_XP_PER_LEVEL = int(os.getenv("BATTLE_PASS_XP_PER_LEVEL", 100))

WAR_SEASON_DURATION_DAYS = int(os.getenv("WAR_SEASON_DAYS", 7))
WAR_POINTS_PER_WIN = int(os.getenv("WAR_POINTS_PER_WIN", 3))

SEASON_DURATION_DAYS = int(os.getenv("SEASON_DURATION_DAYS", 30))
SEASON_RESET_RATING = int(os.getenv("SEASON_RESET_RATING", 1000))

BOSS_HP = int(os.getenv("BOSS_HP", 1000))
BOSS_SPAWN_INTERVAL_HOURS = int(os.getenv("BOSS_SPAWN_HOURS", 6))

DROP_CHANCE = float(os.getenv("DROP_CHANCE", 0.1))
EVENT_CHANCE = float(os.getenv("EVENT_CHANCE", 0.3))

MASS_BATTLE_DURATION = int(os.getenv("MASS_BATTLE_DURATION", 30))
MASS_BATTLE_REWARD = (int(os.getenv("MASS_BATTLE_POINTS", 30)), int(os.getenv("MASS_BATTLE_GEMS", 5)))

CHANNEL_LOOP_INTERVAL = int(os.getenv("CHANNEL_INTERVAL", 60))
CHANNEL_LOOP_TTL = int(os.getenv("CHANNEL_TTL", 30))
CHANNEL_LOOP_REWARDS = {
    "win": int(os.getenv("REWARD_WIN", 10)),
    "draw": int(os.getenv("REWARD_DRAW", 5)),
    "loss": int(os.getenv("REWARD_LOSS", 2))
}

STREAK_BONUS = int(os.getenv("STREAK_BONUS", 2))
STREAK_MULTIPLIERS = {
    3: int(os.getenv("STREAK_MULTIPLIER_3", 2)),
    5: int(os.getenv("STREAK_MULTIPLIER_5", 3))
}

PREDICTION_BONUS = int(os.getenv("PREDICTION_BONUS", 3))
VOTE_FREEZE_SECONDS = int(os.getenv("VOTE_FREEZE_SECONDS", 2))

XP_PER_WIN = int(os.getenv("XP_PER_WIN", 20))
XP_PER_LOSS = int(os.getenv("XP_PER_LOSS", 5))
XP_PER_DRAW = int(os.getenv("XP_PER_DRAW", 10))

REFERRAL_REWARD = int(os.getenv("REFERRAL_REWARD", 200))

# ========== التحقق من المتغيرات الإجبارية ==========
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود! أضفه في متغيرات البيئة.")
if not FOUNDER_ID:
    raise ValueError("❌ FOUNDER_ID غير موجود! أضف معرفك في متغيرات البيئة.")
