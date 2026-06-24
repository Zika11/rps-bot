from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# --- الدوال الأساسية لم تتغير (main_menu, game_mode_menu, etc.) ---
# أضف فقط الدوال الجديدة في نهاية الملف

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

# أزرار اختيار الحركة للفردي الجماعي (تُستخدم في المجموعة)
def group_choice_buttons(chat_id, player_id):
    from config import CHOICES
    buttons = []
    for key, icon in CHOICES.items():
        buttons.append(InlineKeyboardButton(icon, callback_data=f"group_pick_{key}_{chat_id}_{player_id}"))
    return InlineKeyboardMarkup([buttons])
