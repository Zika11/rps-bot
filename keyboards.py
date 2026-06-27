from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# ========== القوائم الرئيسية ==========
def main_menu(lang="ar"):
    """القائمة الرئيسية"""
    if lang == "ar":
        btns = [
            ("🎮 ألعاب", "game"),
            ("👥 أصدقاء", "friends"),
            ("🛒 متجر", "shop"),
            ("🏆 عشائر", "clans"),
            ("📋 المهام", "tasks"),
            ("🏅 الإنجازات", "achievements"),
            ("📊 التصنيف", "rating"),
            ("🌐 اللغة", "language")
        ]
    else:
        btns = [
            ("🎮 Games", "game"),
            ("👥 Friends", "friends"),
            ("🛒 Shop", "shop"),
            ("🏆 Clans", "clans"),
            ("📋 Tasks", "tasks"),
            ("🏅 Achievements", "achievements"),
            ("📊 Rating", "rating"),
            ("🌐 Language", "language")
        ]
    keyboard = [[InlineKeyboardButton(text, callback_data=data) for text, data in btns[i:i+2]] for i in range(0, len(btns), 2)]
    return InlineKeyboardMarkup(keyboard)

def back_button(callback="back_main", lang="ar"):
    text = "🔙 رجوع" if lang == "ar" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callback)]])

# ========== أزرار الألعاب ==========
def games_menu():
    """قائمة الألعاب المتاحة"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪨 📄 ✂️ حجر ورقة مقص", callback_data="game_rps")],
        [InlineKeyboardButton("🔢 خمن الرقم", callback_data="game_guess")],
        [InlineKeyboardButton("❓ أسئلة وأجوبة", callback_data="game_quiz")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def game_play_buttons():
    """أزرار اللعب (حجر، ورقة، مقص)"""
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"play_{key}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])

def game_result_buttons(game_id):
    """أزرار إعادة اللعب أو العودة"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 إعادة اللعب", callback_data=f"rematch_{game_id}")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
    ])

# ========== أزرار المطابقة (Matchmaking) ==========
def matchmaking_buttons():
    """أزرار البحث عن خصم وإلغاء البحث"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 بحث عن خصم", callback_data="find_match")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="match_cancel")]
    ])

# ========== أزرار المتجر ==========
def shop_categories():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 بطاقات", callback_data="shop_cards")],
        [InlineKeyboardButton("🏷️ الألقاب", callback_data="shop_titles")],
        [InlineKeyboardButton("🎨 الثيمات", callback_data="shop_themes")],
        [InlineKeyboardButton("🎁 صندوق الكنز", callback_data="treasure_box")],
        [InlineKeyboardButton("🎡 عجلة الحظ", callback_data="wheel")],
        [InlineKeyboardButton("🖼️ إطارات", callback_data="frames_shop")],
        [InlineKeyboardButton("🏪 السوق", callback_data="market")],
        [InlineKeyboardButton("🛡️ القدرات", callback_data="abilities_shop")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ========== أزرار العشائر ==========
def clans_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏘️ إنشاء عشيرة", callback_data="clan_create")],
        [InlineKeyboardButton("🔗 الانضمام لعشيرة", callback_data="clan_join")],
        [InlineKeyboardButton("📊 ترتيب العشائر", callback_data="clan_ranking")],
        [InlineKeyboardButton("🏦 خزينة العشيرة", callback_data="clan_treasury")],
        [InlineKeyboardButton("⚔️ حرب العشائر", callback_data="clan_war_info")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ========== أزرار الأصدقاء ==========
def friends_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة صديق", callback_data="add_friend")],
        [InlineKeyboardButton("📥 طلبات الصداقة", callback_data="friend_requests")],
        [InlineKeyboardButton("👥 قائمة الأصدقاء", callback_data="friend_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# ========== أزرار الإدارة ==========
def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 رسالة شاملة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👤 تعديل نقاط", callback_data="admin_set_points")],
        [InlineKeyboardButton("📺 إدارة القنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("🔄 مسح المباريات", callback_data="admin_reset")],
        [InlineKeyboardButton("🚫 إغلاق", callback_data="delete_message")]
    ])

# ========== أزرار أخرى ==========
def mini_app_button():
    """زر لفتح التطبيق المصغر (Mini App)"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎮 افتح اللعبة",
            web_app=WebAppInfo(url="https://rps-bot-six.vercel.app/webapp/index.html")
        )]
    ])

def wheel_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎡 لف العجلة (5 جواهر)", callback_data="wheel_spin")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="shop")]
    ])

def battlepass_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 عرض التقدم", callback_data="battlepass_progress")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def frame_shop():
    from config import AVATAR_FRAMES, FRAME_PRICES
    buttons = []
    for frame_id, icon in AVATAR_FRAMES.items():
        if frame_id == "default":
            continue
        price = FRAME_PRICES.get(frame_id, 200)
        buttons.append([InlineKeyboardButton(f"{icon} {frame_id} - {price} نقطة", callback_data=f"buy_frame_{frame_id}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="shop")])
    return InlineKeyboardMarkup(buttons)

def market_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 تصفح السوق", callback_data="market_browse")],
        [InlineKeyboardButton("📢 عرض عنصر للبيع", callback_data="market_sell")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="shop")]
    ])

def abilities_shop():
    from config import ABILITIES
    buttons = []
    for ab_id, data in ABILITIES.items():
        buttons.append([InlineKeyboardButton(f"{data['icon']} {data['name']} - {data['cost']} نقطة", callback_data=f"buy_ability_{ab_id}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="shop")])
    return InlineKeyboardMarkup(buttons)

def clan_treasury_menu(clan_name):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 عرض الخزينة", callback_data=f"treasury_view_{clan_name}")],
        [InlineKeyboardButton("📥 تبرع (50 نقطة)", callback_data=f"treasury_donate_points_{clan_name}")],
        [InlineKeyboardButton("💎 تبرع (5 جواهر)", callback_data=f"treasury_donate_gems_{clan_name}")],
        [InlineKeyboardButton("⬆️ تطوير العشيرة", callback_data=f"treasury_upgrade_{clan_name}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="clans")]
    ])

def world_boss_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐉 مهاجمة الزعيم", callback_data="boss_attack")],
        [InlineKeyboardButton("📊 حالة الزعيم", callback_data="boss_status")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def tournament_keyboard(tour_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 انضم للبطولة", callback_data=f"join_tournament_{tour_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def tournament_choice_buttons(tour_id, match_index):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"pick_tournament_{tour_id}_{match_index}_{key}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])
