import os

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود!")

try:
    FOUNDER_ID = int(os.environ.get("FOUNDER_ID", "1232067711"))
except (ValueError, TypeError):
    FOUNDER_ID = 1232067711

CHOICES = {"rock": "🪨 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
WIN_MAP = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
THEME_ICONS = {
    "theme_1": CHOICES,
    "theme_2": {"rock":"🟡 حجر","paper":"🟨 ورقة","scissors":"🟧 مقص"},
    "theme_3": {"rock":"🔥 حجر","paper":"🌪️ ورقة","scissors":"💧 مقص"},
    "theme_4": {"rock":"🌍 حجر","paper":"🌟 ورقة","scissors":"🌙 مقص"}
}
CHOICES_SPOCK = {"rock": "🪨", "paper": "📄", "scissors": "✂️", "lizard": "🦎", "spock": "🖖"}
WIN_MAP_SPOCK = {
    "scissors": ["paper", "lizard"], "paper": ["rock", "spock"],
    "rock": ["lizard", "scissors"], "lizard": ["spock", "paper"],
    "spock": ["scissors", "rock"]
}

WIN_POINTS_SOLO = 10
LOSS_POINTS_SOLO = -3
DRAW_POINTS_SOLO = 5
WIN_POINTS_MULTI = 15
LOSS_POINTS_MULTI = -3
ROUND_WIN_POINTS = 5
ROUND_LOSS_POINTS = -1
ROUND_DRAW_POINTS = 2
DAILY_REFERRAL_POINTS = 1000

GAME_TIMEOUT = 120
CHANNEL_ROUND_INTERVAL = 120
MAX_STREAK_REWARD = 100
MIN_STREAK_MULTIPLIER = 10
MAX_STORY_LEVEL = 3
STORY_LEVELS = {
    1: {"boss": "الرجل الحجري", "emoji": "🗿", "story": "في مملكة الأحجار..."},
    2: {"boss": "ملك الورق", "emoji": "📜", "story": "بعد هزيمة الرجل الحجري..."},
    3: {"boss": "سيد المقصات", "emoji": "⚔️", "story": "أقوى زعيم في المملكة..."}
}
