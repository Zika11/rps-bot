import json, random, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, keyboards

logger = logging.getLogger(__name__)

# ---------- المتجر ----------
async def shop_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("المتجر:", reply_markup=keyboards.shop_categories())

async def shop_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    items = db.get_shop_items()
    text = "🃏 بطاقات المتجر:\n"
    keyboard = []
    for item in items:
        text += f"{item['name']} - {item['price']} نقطة\n"
        keyboard.append([InlineKeyboardButton(f"شراء {item['name']}", callback_data=f"buy_{item['item_id']}")])
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="shop")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    item_id = query.data.split("_", 1)[1]
    u = db.get_user(user.id)   # ✅ تغيير
    item = next((i for i in db.get_shop_items() if i["item_id"] == item_id), None)
    if not item or u["points"] < item["price"]:
        await query.answer("نقاط غير كافية")
        return
    db.update_user(user.id, points=u["points"] - item["price"])   # ✅ تغيير
    owned = (u.get("shop_items") or "").split(",")
    owned.append(item_id)
    db.update_user(user.id, shop_items=",".join([o for o in owned if o]))   # ✅ تغيير
    await query.answer("تم الشراء!")

async def shop_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = db.get_conn()
    titles = conn.execute("SELECT * FROM titles_shop").fetchall()
    conn.close()
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
    success, msg = db.buy_item(user.id, "title", title_id)   # ✅ تغيير
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

async def shop_themes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = db.get_conn()
    themes = conn.execute("SELECT * FROM themes_shop").fetchall()
    conn.close()
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
    success, msg = db.buy_item(user.id, "theme", theme_id)   # ✅ تغيير
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

async def treasure_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)   # ✅ تغيير
    if u["points"] < config.TREASURE_BOX_PRICE:
        await query.answer("تحتاج 100 نقطة")
        return
    db.update_user(user.id, points=u["points"] - config.TREASURE_BOX_PRICE)   # ✅ تغيير
    reward = random.choice(config.TREASURE_REWARDS)
    typ, val = reward[0], reward[1]
    if typ == "points":
        db.update_user(user.id, points=u["points"] + val)   # ✅ تغيير
    elif typ == "gems":
        db.update_user(user.id, gems=int(u.get("gems",0)) + val)   # ✅ تغيير
    elif typ == "title":
        db.update_user(user.id, title=val)   # ✅ تغيير
    elif typ == "theme":
        db.update_user(user.id, theme=val)   # ✅ تغيير
    elif typ == "booster":
        owned = u.get("shop_items","") + f",{val}" if u.get("shop_items") else val
        db.update_user(user.id, shop_items=owned)   # ✅ تغيير
    await query.answer(f"حصلت على {val}!")

async def frames_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("اختر إطاراً:", reply_markup=keyboards.frame_shop())

async def buy_frame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    frame = query.data.split("_")[-1]
    success, msg = db.buy_item(user.id, "frame", frame)   # ✅ تغيير
    if success:
        await query.answer("تم شراء الإطار! استخدم /me لرؤيته.")
    else:
        await query.answer(msg)

async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("السوق:", reply_markup=keyboards.market_menu())

async def market_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    listings = db.get_active_listings()
    if not listings:
        await query.edit_message_text("لا توجد عروض حالياً.")
        return
    text = "📊 **عروض السوق:**\n"
    buttons = []
    for l in listings[:5]:
        seller = db.get_user(l["seller_id"])   # ✅ تغيير
        name = seller["first_name"] if seller else "مجهول"
        text += f"{l['listing_id']}. {l['item_type']} {l['item_id']} - {l['price']} {l['price_type']} (من {name})\n"
        buttons.append([InlineKeyboardButton(f"شراء {l['listing_id']}", callback_data=f"market_buy_{l['listing_id']}")])
    buttons.append([InlineKeyboardButton("رجوع", callback_data="market")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    lid = int(query.data.split("_")[-1])
    success = db.buy_listing(lid, user.id)
    if success:
        await query.answer("تم الشراء بنجاح!")
    else:
        await query.answer("فشل الشراء (رصيد غير كاف أو العنصر بيع).")

async def market_sell_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("استخدم /sell <نوع> <معرف> <سعر> <عملة>")

async def abilities_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("🛡️ متجر القدرات:", reply_markup=keyboards.abilities_shop())

async def buy_ability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    ability = query.data.split("_")[-1]
    success, msg = db.buy_item(user.id, "ability", ability)   # ✅ تغيير
    if success:
        await query.answer(f"تم شراء {config.ABILITIES[ability]['name']}!")
    else:
        await query.answer(msg)
