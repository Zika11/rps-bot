# config/constants.py
"""
الثوابت الخالصة للعبة.
كل القيم اللي مش بتتغير حسب البيئة، زي قوانين اللعبة والجوائز والثيمات.
"""

# ========== قواعد اللعبة ==========
CHOICES = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
WIN_MAP = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

SPOCK_CHOICES = {"rock": "🪨", "paper": "📄", "scissors": "✂️", "lizard": "🦎", "spock": "🖖"}
SPOCK_WIN_MAP = {
    "rock": ["scissors", "lizard"],
    "paper": ["rock", "spock"],
    "scissors": ["paper", "lizard"],
    "lizard": ["spock", "paper"],
    "spock": ["rock", "scissors"]
}

# ========== الثيمات ==========
THEMES = {
    "theme_1": {"rock": "🪨", "paper": "📄", "scissors": "✂️"},
    "theme_2": {"rock": "🌑", "paper": "📰", "scissors": "⚔️"},
    "theme_3": {"rock": "🔥", "paper": "💧", "scissors": "🌿"},
    "theme_4": {"rock": "💎", "paper": "📜", "scissors": "⚡"},
    "theme_5": {"rock": "🍖", "paper": "🧻", "scissors": "🔪"}
}
THEME_ICONS = THEMES

# ========== التصنيف ==========
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

# ========== المتجر ==========
SHOP_ITEMS = {
    "double_points_1h": {"type": "booster", "name": "نقاط مضاعفة (ساعة)", "price": 50},
    "shield_1h": {"type": "booster", "name": "درع الخسارة (ساعة)", "price": 40},
    "extra_gems_1h": {"type": "booster", "name": "جواهر إضافية (ساعة)", "price": 30},
}

TREASURE_REWARDS = [
    ("points", 50),
    ("points", 100),
    ("gems", 5),
    ("title", "ملك الصندوق"),
    ("theme", "theme_3"),
    ("booster", "double_points_1h")
]

TITLES_SHOP = [
    {"id": "title_king", "name": "👑 الملك", "price": 200},
    {"id": "title_legend", "name": "🏆 الأسطورة", "price": 500}
]

THEMES_SHOP = [
    {"id": "theme_2", "name": "🌑 الظلال", "price": 150},
    {"id": "theme_4", "name": "💎 الكريستال", "price": 250}
]

# ========== الإطارات ==========
AVATAR_FRAMES = {"default": "⬛", "gold": "🟨", "diamond": "💠", "legend": "👑", "fire": "🔥"}
FRAME_PRICES = {"gold": 200, "diamond": 500, "fire": 300, "legend": 1000}

# ========== المكافآت اليومية ==========
DAILY_REWARDS = {
    1: (10, 0),
    2: (15, 0),
    3: (20, 1),
    4: (25, 0),
    5: (30, 2),
    6: (35, 0),
    7: (50, 3)
}

# ========== عجلة الحظ ==========
WHEEL_REWARDS = [
    ("points", 100, 0.15),
    ("points", 200, 0.1),
    ("points", 50, 0.25),
    ("gems", 5, 0.2),
    ("title", "محظوظ", 0.1),
    ("theme", "theme_3", 0.1),
    ("treasure_box", None, 0.1)
]

# ========== Battle Pass ==========
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

# ========== البطولات ==========
TOURNAMENT_SETTINGS = {
    "entry_fee": 20,
    "prize_pool_multiplier": 5,
    "rounds": ["ربع النهائي", "نصف النهائي", "النهائي"]
}

# ========== العشائر ==========
CLAN_UPGRADES = {
    "bonus_points": {"name": "نقاط إضافية", "levels": 5, "cost_per_level": 200},
    "bonus_gems": {"name": "جواهر إضافية", "levels": 3, "cost_per_level": 300},
    "shield": {"name": "حماية العشيرة", "levels": 3, "cost_per_level": 500},
}
WAR_REGIONS = ["الصحراء", "الغابة", "الجبل", "المحيط"]

# ========== قدرات اللاعبين ==========
ABILITIES = {
    "shield": {"name": "درع", "icon": "🛡", "cost": 50, "cooldown_minutes": 30},
    "double_points": {"name": "نقاط مضاعفة", "icon": "⚡", "cost": 40, "cooldown_minutes": 20},
    "reverse": {"name": "عكس النتيجة", "icon": "🔄", "cost": 60, "cooldown_minutes": 45},
}

# ========== الإسقاطات التلقائية ==========
DROP_REWARDS = [
    ("points", 200),
    ("gems", 10),
    ("title", "صياد الكنوز"),
    ("theme", "theme_5")
]

# ========== الميتا جيم ==========
POSSIBLE_EVENTS = [
    "double_points",
    "shuffle",
    "boss",
    "ban_rock",
    "ban_paper",
    "ban_scissors",
    "reverse_win",
    "random_winner"
]
BANNED_MOVE_EVENTS = {"ban_rock": "rock", "ban_paper": "paper", "ban_scissors": "scissors"}

# ========== نظام المستويات ==========
LEVEL_THRESHOLDS = {
    1: 0,
    2: 50,
    3: 120,
    4: 220,
    5: 350,
    6: 500,
    7: 700,
    8: 1000,
    9: 1400,
    10: 2000
}

LEVEL_TITLES = {
    1: ("مبتدئ", "🥉"),
    3: ("متوسط", "🥈"),
    5: ("متقدم", "🥇"),
    10: ("محترف", "👑")
}

# ========== مكافآت الزعيم ==========
BOSS_REWARD_TOP_DAMAGE = ("points", 500)
BOSS_REWARD_PARTICIPATION = ("gems", 50)
