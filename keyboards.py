from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ---------- القائمة الرئيسية ----------
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

# ---------- قائمة أنماط اللعب ----------
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

# ---------- أزرار اختيار الحركة (تُرسل مع game_id) ----------
def choice_buttons(game_type_and_id):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"pick_{game_type_and_id}_{key}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])

# ---------- زر الرجوع ----------
def back_button(callback="back_main", lang="ar"):
    text = "🔙 رجوع" if lang == "ar" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callback)]])

# ---------- قائمة الأصدقاء ----------
def friends_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة صديق", callback_data="add_friend")],
        [InlineKeyboardButton("📥 طلبات الصداقة", callback_data="friend_requests")],
        [InlineKeyboardButton("👥 قائمة الأصدقاء", callback_data="friend_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ---------- المتجر ----------
def shop_categories():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 بطاقات", callback_data="shop_cards")],
        [InlineKeyboardButton("🏷️ الألقاب", callback_data="shop_titles")],
        [InlineKeyboardButton("🎨 الثيمات", callback_data="shop_themes")],
        [InlineKeyboardButton("🎁 صندوق الكنز", callback_data="treasure_box")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ---------- العشائر ----------
def clans_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏘️ إنشاء عشيرة", callback_data="clan_create")],
        [InlineKeyboardButton("🔗 الانضمام لعشيرة", callback_data="clan_join")],
        [InlineKeyboardButton("📊 ترتيب العشائر", callback_data="clan_ranking")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ---------- البطولات ----------
def tournament_keyboard(tour_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 انضم للبطولة", callback_data=f"join_tournament_{tour_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ---------- أزرار المجموعة ----------
def group_game_menu(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 فردي ضد البوت", callback_data=f"group_solo_{chat_id}")],
        [InlineKeyboardButton("🎲 انضم للعبة العشوائية", callback_data=f"group_random_join_{chat_id}")],
        [InlineKeyboardButton("⚔️ تحدي صديق", callback_data=f"group_friend_{chat_id}")],
        [InlineKeyboardButton("🎯 تحدي مفتوح", callback_data=f"group_open_{chat_id}")],
        [InlineKeyboardButton("🔙 إغلاق", callback_data="delete_message")]
    ])

def open_challenge_accept_button(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 اقبل التحدي!", callback_data=f"accept_open_{chat_id}")]
    ])

# أزرار اختيار الحركة للمجموعة (مع game_id)
def group_choice_buttons(chat_id, player_id, game_id):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"group_pick_{key}_{chat_id}_{player_id}_{game_id}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])
