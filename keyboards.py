from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
    keyboard = [[InlineKeyboardButton(text, callback_data=data) for text, data in btns[i:i+2]] for i in range(0, len(btns), 2)]
    return InlineKeyboardMarkup(keyboard)

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
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data)] for text, data in modes])

def choice_buttons(game_type="solo"):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"pick_{key}_{game_type}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])

def back_button(callback="back_main", lang="ar"):
    text = "🔙 رجوع" if lang == "ar" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callback)]])

def friends_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة صديق", callback_data="add_friend")],
        [InlineKeyboardButton("📥 طلبات الصداقة", callback_data="friend_requests")],
        [InlineKeyboardButton("👥 قائمة الأصدقاء", callback_data="friend_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def shop_categories():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 بطاقات", callback_data="shop_cards")],
        [InlineKeyboardButton("🏷️ الألقاب", callback_data="shop_titles")],
        [InlineKeyboardButton("🎨 الثيمات", callback_data="shop_themes")],
        [InlineKeyboardButton("🎁 صندوق الكنز", callback_data="treasure_box")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def clans_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏘️ إنشاء عشيرة", callback_data="clan_create")],
        [InlineKeyboardButton("🔗 الانضمام لعشيرة", callback_data="clan_join")],
        [InlineKeyboardButton("📊 ترتيب العشائر", callback_data="clan_ranking")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def tournament_keyboard(tour_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 انضم للبطولة", callback_data=f"join_tournament_{tour_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])
