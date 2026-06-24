import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
FOUNDER_ID = 1232067711

CHOICES = {
    "rock": "🪨",
    "paper": "📄",
    "scissors": "✂️"
}

WIN_MAP = {
    "rock": "scissors",
    "paper": "rock",
    "scissors": "paper"
}

SPOCK_CHOICES = {
    "rock": "🪨",
    "paper": "📄",
    "scissors": "✂️",
    "lizard": "🦎",
    "spock": "🖖"
}

SPOCK_WIN_MAP = {
    "rock": ["scissors", "lizard"],
    "paper": ["rock", "spock"],
    "scissors": ["paper", "lizard"],
    "lizard": ["spock", "paper"],
    "spock": ["rock", "scissors"]
}

THEMES = {
    "theme_1": {"rock": "🪨", "paper": "📄", "scissors": "✂️"},
    "theme_2": {"rock": "🌑", "paper": "📰", "scissors": "⚔️"},
    "theme_3": {"rock": "🔥", "paper": "💧", "scissors": "🌿"},
    "theme_4": {"rock": "💎", "paper": "📜", "scissors": "⚡"},
    "theme_5": {"rock": "🍖", "paper": "🧻", "scissors": "🔪"}
}

THEME_ICONS = THEMES

DEFAULT_RATING = 1000
RATING_K = 32

RATING_TIERS = [
    (0, 999, "برونز", "🥉"),
    (1000, 1199, "فضة", "🥈"),
    (1200, 1399, "ذهبي", "🥇"),
    (1400, 1599, "بلاتينيوم", "🔮"),
    (1600, 1799, "ماسي", "💎"),
    (1800, 9999, "أسطورة", "👑")
]

def get_tier_info(rating):
    for low, high, name, icon in RATING_TIERS:
        if low <= rating <= high:
            return name, icon
    return "غير مصنف", "❓"

SHOP_ITEMS = {
    "double_points_1h": {"type": "booster", "name": "نقاط مضاعفة (ساعة)", "price": 50, "duration_hours": 1},
    "shield_1h": {"type": "booster", "name": "درع الخسارة (ساعة)", "price": 40, "duration_hours": 1},
    "extra_gems_1h": {"type": "booster", "name": "جواهر إضافية (ساعة)", "price": 30, "duration_hours": 1},
}

TREASURE_BOX_PRICE = 100
TREASURE_REWARDS = [
    ("points", 50), ("points", 100), ("gems", 5),
    ("title", "ملك الصندوق"), ("theme", "theme_3"), ("booster", "double_points_1h")
]

TITLES_SHOP = [
    {"id": "title_king", "name": "👑 الملك", "price": 200},
    {"id": "title_legend", "name": "🏆 الأسطورة", "price": 500},
]

THEMES_SHOP = [
    {"id": "theme_2", "name": "🌑 الظلال", "price": 150},
    {"id": "theme_4", "name": "💎 الكريستال", "price": 250},
]

# مكافآت تسجيل الدخول اليومية
DAILY_REWARDS = {
    1: (10, 0),
    2: (15, 0),
    3: (20, 1),
    4: (25, 0),
    5: (30, 2),
    6: (35, 0),
    7: (50, 3)
}

# عجلة الحظ
WHEEL_REWARDS = [
    ("points", 100, 0.15),
    ("points", 200, 0.1),
    ("points", 50, 0.25),
    ("gems", 5, 0.2),
    ("title", "محظوظ", 0.1),
    ("theme", "theme_3", 0.1),
    ("treasure_box", None, 0.1)
]
WHEEL_COST = 5  # جواهر

# Battle Pass
MAX_BATTLE_PASS_LEVEL = 10
BATTLE_PASS_XP_PER_LEVEL = 100
BATTLE_PASS_REWARDS = {
    1: {"free": ("points", 50), "premium": ("gems", 5)},
    2: {"free": ("points", 75), "premium": ("title", "بطل الموسم")},
    3: {"free": ("gems", 3), "premium": ("booster", "double_points_1h")},
    4: {"free": ("points", 100), "premium": ("theme", "theme_4")},
    5: {"free": ("treasure_box", None), "premium": ("gems", 10)},
    6: {"free": ("points", 120), "premium": ("title", "مخضرم")},
    7: {"free": ("gems", 5), "premium": ("booster", "shield_1h")},
    8: {"free": ("points", 150), "premium": ("theme", "theme_2")},
    9: {"free": ("treasure_box", None), "premium": ("gems", 15)},
    10: {"free": ("points", 200), "premium": ("title", "أسطورة الموسم")}
}

# 🆕 إطارات الأفاتار
AVATAR_FRAMES = {
    "default": "⬛",
    "gold": "🟨",
    "diamond": "💠",
    "legend": "👑",
    "fire": "🔥"
}
FRAME_PRICES = {
    "gold": 200,
    "diamond": 500,
    "fire": 300,
    "legend": 1000
}

# 🆕 إعدادات البطولة
TOURNAMENT_SETTINGS = {
    "entry_fee": 20,
    "prize_pool_multiplier": 5,
    "rounds": ["ربع النهائي", "نصف النهائي", "النهائي"]
}
