from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# ========== القائمة الرئيسية ==========
def main_menu(lang="ar"):
    """القائمة الرئيسية - زي الصورة"""
    if lang == "ar":
        btns = [
            ("🎮 العنب الآن", "play_now"),
            ("🏆 التصنيف", "rating"),
            ("📋 المهام", "tasks"),
            ("🏰 العشيرة", "clans"),
            ("🛒 المنجر", "shop"),
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
def channel_options_menu(channel_name, question_type="اختيارات", auto_play_enabled=False):
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

# ========== الأزرار القديمة (للتوافق) ==========
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
        [InlineKeyboardButton("🎡 عجلة الحظ", callback_data="wheel")],
        [InlineKeyboardButton("🖼️ إطارات", callback_data="frames_shop")],
        [InlineKeyboardButton("🏪 السوق", callback_data="market")],
        [InlineKeyboardButton("🛡️ القدرات", callback_data="abilities_shop")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def clans_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏘️ إنشاء عشيرة", callback_data="clan_create")],
        [InlineKeyboardButton("🔗 الانضمام لعشيرة", callback_data="clan_join")],
        [InlineKeyboardButton("📊 ترتيب العشائر", callback_data="clan_ranking")],
        [InlineKeyboardButton("🏦 خزينة العشيرة", callback_data="clan_treasury")],
        [InlineKeyboardButton("⚔️ حرب العشائر", callback_data="clan_war_info")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def tournament_keyboard(tour_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 انضم للبطولة", callback_data=f"join_tournament_{tour_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def group_game_menu(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 فردي ضد البوت", callback_data=f"group_solo_{chat_id}")],
        [InlineKeyboardButton("🎲 انضم للعبة العشوائية", callback_data=f"group_random_join_{chat_id}")],
        [InlineKeyboardButton("⚔️ تحدي صديق", callback_data=f"group_friend_{chat_id}")],
        [InlineKeyboardButton("🎯 تحدي مفتوح", callback_data=f"group_open_{chat_id}")],
        [InlineKeyboardButton("👀 مشاهدة مباراة", callback_data=f"spectate_{chat_id}")],
        [InlineKeyboardButton("🔙 إغلاق", callback_data="delete_message")]
    ])

def open_challenge_accept_button(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 اقبل التحدي!", callback_data=f"accept_open_{chat_id}")]
    ])

def group_choice_buttons(chat_id, player_id, game_id):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"group_pick_{key}_{chat_id}_{player_id}_{game_id}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])

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

def tournament_choice_buttons(tour_id, match_index):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"pick_tournament_{tour_id}_{match_index}_{key}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])

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

def spectator_accept_button(room_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 انضم كمشاهد", callback_data=f"spectate_join_{room_id}")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 رسالة شاملة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👤 تعديل نقاط", callback_data="admin_set_points")],
        [InlineKeyboardButton("📺 إدارة القنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("🔄 مسح المباريات", callback_data="admin_reset")],
        [InlineKeyboardButton("▶️ بدء لعبة في قناة", callback_data="admin_start_channel")],
        [InlineKeyboardButton("⏹️ إيقاف لعبة في قناة", callback_data="admin_stop_channel")],
        [InlineKeyboardButton("🚫 إغلاق", callback_data="delete_message")]
    ])

def abilities_shop():
    from config import ABILITIES
    buttons = []
    for ab_id, data in ABILITIES.items():
        buttons.append([InlineKeyboardButton(f"{data['icon']} {data['name']} - {data['cost']} نقطة", callback_data=f"buy_ability_{ab_id}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="shop")])
    return InlineKeyboardMarkup(buttons)

def mass_battle_start_button(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ انضم للمعركة الجماعية", callback_data=f"mass_join_{chat_id}")]
    ])

def team_battle_team_buttons(battle_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 انضم للفريق الأحمر", callback_data=f"team_join_{battle_id}_red")],
        [InlineKeyboardButton("🔵 انضم للفريق الأزرق", callback_data=f"team_join_{battle_id}_blue")]
    ])

def channel_vote_buttons(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 حجر", callback_data=f"channel_vote_{chat_id}_rock"),
            InlineKeyboardButton("✋ ورق", callback_data=f"channel_vote_{chat_id}_paper"),
            InlineKeyboardButton("✌️ مقص", callback_data=f"channel_vote_{chat_id}_scissors")
        ]
    ])

def channel_leaderboard_button(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 قائمة الأفضل", callback_data=f"ch_leaderboard_{chat_id}")]
    ])

def mini_app_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎮 افتح اللعبة",
            web_app=WebAppInfo(url="https://rps-bot-six.vercel.app/webapp/index.html")
        )]
    ])

def rps_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪨 Rock", callback_data="move_rock"),
            InlineKeyboardButton("📄 Paper", callback_data="move_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="move_scissors"),
        ]
    ])

def channel_main_menu(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play", callback_data=f"channel_play_{chat_id}")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data=f"weekly_leaderboard_{chat_id}")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
    ])

def weekly_leaderboard_button(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الأفضل هذا الأسبوع", callback_data=f"weekly_leaderboard_{chat_id}")]
    ])

def dynamic_rps_keyboard(counts):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🪨 حجر ({counts.get('rock', 0)})", callback_data="move_rock"),
            InlineKeyboardButton(f"📄 ورق ({counts.get('paper', 0)})", callback_data="move_paper"),
            InlineKeyboardButton(f"✂️ مقص ({counts.get('scissors', 0)})", callback_data="move_scissors"),
        ]
    ])
