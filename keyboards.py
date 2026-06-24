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

def choice_buttons(game_type_and_id):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"pick_{game_type_and_id}_{key}") for key, icon in CHOICES.items()]
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
        if frame_id == "default": continue
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
        [InlineKeyboardButton("🚫 إغلاق", callback_data="delete_message")]
    ])

# Mini Game Platform
def abilities_shop():
    from config import ABILITIES
    buttons = []
    for ab_id, data in ABILITIES.items():
        buttons.append([InlineKeyboardButton(f"{data['icon']} {data['name']} - {data['cost']} نقطة", callback_data=f"buy_ability_{ab_id}")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="shop")])
    return InlineKeyboardMarkup(buttons)

def mass_battle_start_button(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ انضم للمعركة الجماعية", callback_data=f"mass_join_{chat_id}")],
    ])

def team_battle_team_buttons(battle_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 انضم للفريق الأحمر", callback_data=f"team_join_{battle_id}_red")],
        [InlineKeyboardButton("🔵 انضم للفريق الأزرق", callback_data=f"team_join_{battle_id}_blue")],
    ])

# أزرار التصويت للقناة
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

# 🆕 زر فتح Mini App
def mini_app_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎮 افتح اللعبة",
            web_app=WebAppInfo(url="https://rps-bot-six.vercel.app")
        )]
    ])
