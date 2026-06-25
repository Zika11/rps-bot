# handlers/shop_handlers.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import keyboards
from core.shop_manager import (
    get_shop_items, get_titles_shop, get_themes_shop, buy_item,
    get_available_frames, set_user_frame, get_abilities, buy_ability,
    get_active_listings, create_listing, buy_listing,
    open_treasure_box, spin_wheel, get_battle_pass,
    get_battle_pass_rewards, get_battle_pass_levels
)
import db, config

logger = logging.getLogger(__name__)

# ========== القائمة الرئيسية ==========
async def shop_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("المتجر:", reply_markup=keyboards.shop_categories())

# ========== البطاقات ==========
async def shop_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    items = get_shop_items()
    text = "🃏 بطاقات المتجر:\n"
    keyboard = []
    for item in items:
        text += f"{item['name']} - {item['price']} نقطة\n"
        keyboard.append([InlineKeyboardButton(f"شراء {item['name']}", callback_data=f"buy_{item['item_id']}")])
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="shop")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_item_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    item_id = query.data.split("_", 1)[1]
    u = db.get_user(user.id)
    item = next((i for i in get_shop_items() if i["item_id"] == item_id), None)
    if not item or u["points"] < item["price"]:
        await query.answer("نقاط غير كافية")
        return
    db.update_user(user.id, points=u["points"] - item["price"])
    owned = (u.get("shop_items") or "").split(",")
    owned.append(item_id)
    db.update_user(user.id, shop_items=",".join([o for o in owned if o]))
    await query.answer("تم الشراء!")

# ========== الألقاب ==========
async def shop_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    titles = get_titles_shop()
    text = "🏷️ الألقاب المتاحة:\n"
    keyboard = []
    for t in titles:
        text += f"{t['name']} - {t['price']} نقطة\n"
        keyboard.append([InlineKeyboardButton(f"شراء {t['name']}", callback_data=f"buy_title_{t['title_id']}")])
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="shop")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    title_id = query.data.split("_", 2)[2]
    success, msg = buy_item(user.id, "title", title_id)
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

# ========== الثيمات ==========
async def shop_themes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    themes = get_themes_shop()
    text = "🎨 الثيمات المتاحة:\n"
    keyboard = []
    for th in themes:
        text += f"{th['name']} - {th['price']} نقطة\n"
        keyboard.append([InlineKeyboardButton(f"شراء {th['name']}", callback_data=f"buy_theme_{th['theme_id']}")])
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="shop")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    theme_id = query.data.split("_", 2)[2]
    success, msg = buy_item(user.id, "theme", theme_id)
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

# ========== الإطارات ==========
async def frames_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("اختر إطاراً:", reply_markup=keyboards.frame_shop())

async def buy_frame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    frame = query.data.split("_")[-1]
    success, msg = buy_item(user.id, "frame", frame)
    if success:
        await query.answer("تم شراء الإطار! استخدم /me لرؤيته.")
    else:
        await query.answer(msg)

# ========== القدرات ==========
async def abilities_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("🛡️ متجر القدرات:", reply_markup=keyboards.abilities_shop())

async def buy_ability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    ability = query.data.split("_")[-1]
    success, msg = buy_item(user.id, "ability", ability)
    if success:
        await query.answer(f"تم شراء {config.ABILITIES[ability]['name']}!")
    else:
        await query.answer(msg)

# ========== السوق ==========
async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("السوق:", reply_markup=keyboards.market_menu())

async def market_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    listings = get_active_listings()
    if not listings:
        await query.edit_message_text("لا توجد عروض حالياً.")
        return
    text = "📊 **عروض السوق:**\n"
    buttons = []
    for l in listings[:5]:
        seller = db.get_user(l["seller_id"])
        name = seller["first_name"] if seller else "مجهول"
        text += f"{l['listing_id']}. {l['item_type']} {l['item_id']} - {l['price']} {l['price_type']} (من {name})\n"
        buttons.append([InlineKeyboardButton(f"شراء {l['listing_id']}", callback_data=f"market_buy_{l['listing_id']}")])
    buttons.append([InlineKeyboardButton("رجوع", callback_data="market")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    lid = int(query.data.split("_")[-1])
    success = buy_listing(lid, user.id)
    if success:
        await query.answer("تم الشراء بنجاح!")
    else:
        await query.answer("فشل الشراء (رصيد غير كاف أو العنصر بيع).")

async def market_sell_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("استخدم /sell <نوع> <معرف> <سعر> <عملة>")

# ========== صندوق الكنز ==========
async def treasure_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    success, msg, _ = open_treasure_box(user.id)
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

# ========== عجلة الحظ ==========
async def wheel_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    success, msg, _ = spin_wheel(user.id)
    if success:
        await query.edit_message_text(f"🎡 العجلة توقفت عند: {msg}", reply_markup=keyboards.wheel_button())
    else:
        await query.answer(msg)

# ========== Battle Pass ==========
async def battlepass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bp = get_battle_pass(user.id)
    level = bp["level"]
    xp = bp["xp"]
    required_xp = level * config.BATTLE_PASS_XP_PER_LEVEL
    text = f"📊 **Battle Pass - الموسم 1**\n"
    text += f"المستوى: {level}/{get_battle_pass_levels()}\n"
    text += f"الخبرة: {xp}/{required_xp}\n\n"
    rewards = get_battle_pass_rewards()
    for lvl in range(1, min(level+1, get_battle_pass_levels()+1)):
        free = rewards.get(lvl, {}).get("free")
        prem = rewards.get(lvl, {}).get("premium")
        if free:
            text += f"م {lvl}: مجاني - {free[0]} {free[1] if free[1] else ''}"
            if prem:
                text += f" | مميز - {prem[0]} {prem[1] if prem[1] else ''}"
            text += "\n"
    await update.message.reply_text(text, reply_markup=keyboards.battlepass_button())
