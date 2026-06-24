# ... (الدوال السابقة main_menu, game_mode_menu, ...)

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

# تحديث shop_categories لإضافة زر الإطارات والسوق
def shop_categories():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 بطاقات", callback_data="shop_cards")],
        [InlineKeyboardButton("🏷️ الألقاب", callback_data="shop_titles")],
        [InlineKeyboardButton("🎨 الثيمات", callback_data="shop_themes")],
        [InlineKeyboardButton("🎁 صندوق الكنز", callback_data="treasure_box")],
        [InlineKeyboardButton("🎡 عجلة الحظ", callback_data="wheel")],
        [InlineKeyboardButton("🖼️ إطارات", callback_data="frames_shop")],
        [InlineKeyboardButton("🏪 السوق", callback_data="market")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

# أزرار اختيار الحركة للبطولة (نفس choice_buttons لكن مع نوع tournament)
def tournament_choice_buttons(tour_id, match_index):
    from config import CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"pick_tournament_{tour_id}_{match_index}_{key}") for key, icon in CHOICES.items()]
    return InlineKeyboardMarkup([buttons])
