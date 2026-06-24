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

# 🆕 نظام الرانكات (ELO Tiers)
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
