from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎮 العب", callback_data="play"),
        ],
        [
            InlineKeyboardButton("📊 احصائياتي", callback_data="stats"),
            InlineKeyboardButton("🏆 إنجازاتي", callback_data="achievements"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def game_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🪨 حجر", callback_data="choice_rock"),
            InlineKeyboardButton("📄 ورق", callback_data="choice_paper"),
            InlineKeyboardButton("✂️ مقص", callback_data="choice_scissors"),
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def play_again_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🔁 العب تاني", callback_data="play"),
            InlineKeyboardButton("🏠 القائمة", callback_data="back_to_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
