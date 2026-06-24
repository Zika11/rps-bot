from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


# =========================
# 🆕 SOLO LIVE BUTTONS
# =========================
def solo_choice_buttons(game_id):
    from config import CHOICES

    buttons = [
        InlineKeyboardButton(icon, callback_data=f"solo_{game_id}_{key}")
        for key, icon in CHOICES.items()
    ]

    return InlineKeyboardMarkup([buttons])


# =========================
# 🔄 AFTER GAME BUTTONS
# =========================
def after_game_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 العب تاني", callback_data="replay_solo"),
            InlineKeyboardButton("🏠 القائمة", callback_data="main_menu")
        ]
    ])


# =========================
# 🏠 MAIN MENU
# =========================
def main_menu(lang="ar"):
    if lang == "ar":
        btns = [
            ("🎮 لعب", "game"), ("👥 أصدقاء", "friends"),
            ("🛒 متجر", "shop"), ("🏆 عشائر", "clans"),
            ("📋 المهام", "tasks"), ("🏅 الإنجازات", "achievements"),
            ("📊 التصنيف", "rating"), ("🌐 اللغة", "language")
        ]
    else:
        btns = [
            ("🎮 Play", "game"), ("👥 Friends", "friends"),
            ("🛒 Shop", "shop"), ("🏆 Clans", "clans"),
            ("📋 Tasks", "tasks"), ("🏅 Achievements", "achievements"),
            ("📊 Rating", "rating"), ("🌐 Language", "language")
        ]

    keyboard = [
        [InlineKeyboardButton(text, callback_data=data) for text, data in btns[i:i+2]]
        for i in range(0, len(btns), 2)
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# 🎮 GAME MODE MENU
# =========================
def game_mode_menu(lang="ar"):
    modes = [
        ("🕹️ فردي", "solo"), ("🌍 عشوائي", "random"),
        ("👤 ضد صديق", "friend"), ("📢 قناة", "channel"),
        ("🖖 Spock", "spock"), ("📖 القصة", "story"),
        ("🔙 رجوع", "back_main")
    ] if lang == "ar" else [
        ("🕹️ Solo", "solo"), ("🌍 Random", "random"),
        ("👤 vs Friend", "friend"), ("📢 Channel", "channel"),
        ("🖖 Spock", "spock"), ("📖 Story", "story"),
        ("🔙 Back", "back_main")
    ]

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=data)]
        for text, data in modes
    ])


# =========================
# ⚠️ OLD SYSTEM (مسيبناه زي ما هو)
# =========================
def choice_buttons(game_type_and_id):
    from config import CHOICES

    buttons = [
        InlineKeyboardButton(icon, callback_data=f"pick_{game_type_and_id}_{key}")
        for key, icon in CHOICES.items()
    ]

    return InlineKeyboardMarkup([buttons])


# =========================
# 🔙 BACK BUTTON
# =========================
def back_button(callback="back_main", lang="ar"):
    text = "🔙 رجوع" if lang == "ar" else "🔙 Back"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=callback)]
    ])


# =========================
# 👥 FRIENDS MENU
# =========================
def friends_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة صديق", callback_data="add_friend")],
        [InlineKeyboardButton("📥 طلبات الصداقة", callback_data="friend_requests")],
        [InlineKeyboardButton("👥 قائمة الأصدقاء", callback_data="friend_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])
