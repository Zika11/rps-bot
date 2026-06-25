from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

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

def game_mode_menu(lang="ar"):
    if lang == "ar":
        modes = [
            ("🕹️ فردي", "solo"), ("🌍 عشوائي", "random"),
            ("👤 ضد صديق", "friend"), ("📢 قناة", "channel"),
            ("🖖 Spock", "spock"), ("📖 القصة", "story"),
            ("🔙 رجوع", "back_main")
        ]
    else:
        modes = [
            ("🕹️ Solo", "solo"), ("🌍 Random", "random"),
            ("👤 vs Friend", "friend"), ("📢 Channel", "channel"),
            ("🖖 Spock", "spock"), ("📖 Story", "story"),
            ("🔙 Back", "back_main")
        ]

    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data)] for text, data in modes])

def choice_buttons(game_type_and_id):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"pick_{game_type_and_id}_{key}") 
               for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])

def back_button(callback="back_main", lang="ar"):
    text = "🔙 رجوع" if lang == "ar" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callback)]])

def weekly_leaderboard_button(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الأفضل هذا الأسبوع", callback_data=f"weekly_leaderboard_{chat_id}")]
    ])

# 🆕 Dynamic RPS keyboard with live counts (used in channel voting)
def dynamic_rps_keyboard(counts):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🪨 حجر ({counts.get('rock', 0)})", callback_data="move_rock"),
            InlineKeyboardButton(f"📄 ورق ({counts.get('paper', 0)})", callback_data="move_paper"),
            InlineKeyboardButton(f"✂️ مقص ({counts.get('scissors', 0)})", callback_data="move_scissors"),
        ]
    ])
