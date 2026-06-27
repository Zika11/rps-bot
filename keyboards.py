from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# ========== القائمة الرئيسية ==========
def main_menu(lang="ar"):
    """القائمة الرئيسية - زي الصورة"""
    if lang == "ar":
        btns = [
            ("🎮 العنب الآن", "play_now"),  # العنب = لعب
            ("🏆 التصنيف", "rating"),
            ("📋 المهام", "tasks"),
            ("🏰 العشيرة", "clans"),
            ("🛒 المنجر", "shop"),         # المنجر = متجر
            ("👤 حسابي", "profile"),
            ("⚙️ المزيد", "more")
        ]
    else:
        btns = [
            ("🎮 Play Now", "play_now"),
            ("🏆 Ranking", "rating"),
            ("📋 Tasks", "tasks"),
            ("🏰 Clan", "clans"),
            ("🛒 Store", "shop"),
            ("👤 My Account", "profile"),
            ("⚙️ More", "more")
        ]
    # 2 أزرار في كل صف
    keyboard = []
    for i in range(0, len(btns), 2):
        row = []
        for j in range(2):
            if i + j < len(btns):
                text, callback = btns[i+j]
                row.append(InlineKeyboardButton(text, callback_data=callback))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# ========== قائمة المزيد ==========
def more_menu(lang="ar"):
    """قائمة المزيد - زي الصورة"""
    if lang == "ar":
        btns = [
            ("📖 طريقة اللعب", "how_to_play"),
            ("💬 دعم البوت", "support"),
            ("⭐ تقييم البوت", "rate_bot"),
            ("🔙 رجوع للقائمة الرئيسية", "back_main")
        ]
    else:
        btns = [
            ("📖 How to Play", "how_to_play"),
            ("💬 Support", "support"),
            ("⭐ Rate Bot", "rate_bot"),
            ("🔙 Back to Main", "back_main")
        ]
    keyboard = [[InlineKeyboardButton(text, callback_data=callback)] for text, callback in btns]
    return InlineKeyboardMarkup(keyboard)

# ========== اختيار وضع اللعب ==========
def game_mode_menu(lang="ar"):
    """قائمة اختيار وضع اللعب - زي الصورة"""
    if lang == "ar":
        btns = [
            ("📋 تحديد النوع (قائمة)", "select_type"),
            ("📱 تصفح الأقسام (سريع)", "browse_sections"),
            ("🎮 اللعب الفردي", "solo"),
            ("🆕 أنشئ غرفة", "create_room"),
            ("🔍 بحث عن ألعاب", "search_games"),
            ("🔍 بحث عن غرفة", "search_room"),
            ("🔙 رجوع", "back_main")
        ]
    else:
        btns = [
            ("📋 Select Type (List)", "select_type"),
            ("📱 Browse Sections (Quick)", "browse_sections"),
            ("🎮 Single Player", "solo"),
            ("🆕 Create Room", "create_room"),
            ("🔍 Search Games", "search_games"),
            ("🔍 Search Room", "search_room"),
            ("🔙 Back", "back_main")
        ]
    keyboard = [
        [InlineKeyboardButton(btns[0][0], callback_data=btns[0][1]),
         InlineKeyboardButton(btns[1][0], callback_data=btns[1][1])]
    ]
    for text, callback in btns[2:]:
        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    return InlineKeyboardMarkup(keyboard)

# ========== اختيار القناة ==========
def channel_selection_menu(channels):
    """قائمة اختيار القناة - زي الصورة"""
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(channel["name"], callback_data=f"channel_{channel['id']}")])
    keyboard.append([InlineKeyboardButton("📋 إدارة القنوات", callback_data="manage_channels")])
    keyboard.append([InlineKeyboardButton("🔄 تغيير نوع الأسئلة", callback_data="change_question_type")])
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ========== خيارات القناة ==========
def channel_options_menu(channel_name, question_type, auto_play_enabled):
    """خيارات القناة - زي الصورة"""
    q_type_icon = "🔴" if question_type == "اختيارات" else "🔵"
    auto_icon = "🟢" if auto_play_enabled else "🔴"
    keyboard = [
        [InlineKeyboardButton(f"نوع الأسئلة: {q_type_icon} {question_type}", callback_data="show_question_type")],
        [InlineKeyboardButton(f"اللعب التلقائي: {auto_icon} {'مفعل' if auto_play_enabled else 'معطل'}", callback_data="toggle_auto_play")],
        [InlineKeyboardButton("🎮 إنشاء لعبة الآن", callback_data="create_game_now")],
        [InlineKeyboardButton("⚡ تفعيل اللعب التلقائي", callback_data="enable_auto_play")],
        [InlineKeyboardButton("🔄 تغيير نوع الأسئلة", callback_data="change_question_type")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== أزرار اللعب (حجره ورقه مقص) ==========
def game_play_buttons(broadcast=False):
    """أزرار حجره ورقه مقص - زي الصورة"""
    from config import CHOICES
    buttons = []
    row = []
    for key, icon in CHOICES.items():
        label = f"{icon} {key.capitalize()}"
        row.append(InlineKeyboardButton(label, callback_data=f"play_{key}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if broadcast:
        buttons.append([InlineKeyboardButton("📢 Broadcast", callback_data="broadcast_game")])
    return InlineKeyboardMarkup(buttons)
