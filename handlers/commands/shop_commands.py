import logging, random, sqlite3
from telegram import Update
from telegram.ext import ContextTypes
import db, config

logger = logging.getLogger(__name__)

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛒 **متجر RPS**\n\n"
        "لشراء عنصر استخدم الأمر:\n"
        "/buy <نوع> <معرف>\n\n"
        "الأنواع المتاحة:\n"
        "- booster (مثل: double_points_1h)\n"
        "- title (مثل: title_king)\n"
        "- theme (مثل: theme_2)\n"
        "- frame (مثل: gold)\n"
        "- ability (مثل: shield)\n\n"
        "أمثلة:\n"
        "/buy booster double_points_1h\n"
        "/buy title title_legend\n"
        "/buy frame gold"
    )
    await update.message.reply_text(text)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("استخدم: /buy <نوع> <معرف>\nمثال: /buy frame gold")
        return
    item_type = args[0].lower()
    item_id = args[1]
    success, msg = db.buy_item(user.id, item_type, item_id)
    await update.message.reply_text(msg)

async def market_sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 4:
        await update.message.reply_text("استخدم: /sell <نوع> <معرف> <سعر> <عملة points/gems>\nمثال: /sell frame gold 300 points")
        return
    item_type = args[0]
    item_id = args[1]
    price = int(args[2])
    price_type = args[3].lower()
    if price_type not in ["points", "gems"]:
        await update.message.reply_text("العملة يجب أن تكون points أو gems")
        return
    owned = False
    u = db.get_user(user.id)
    if item_type == "theme" and u.get("theme") == item_id:
        owned = True
    elif item_type == "title" and u.get("title") == item_id:
        owned = True
    elif item_type == "frame":
        conn = sqlite3.connect(config.DB_NAME)
        row = conn.execute("SELECT owned_frames FROM user_frames WHERE user_id=?", (user.id,)).fetchone()
        conn.close()
        if row and item_id in row[0].split(","):
            owned = True
    elif item_type == "booster":
        owned_items = (u.get("shop_items") or "").split(",")
        if item_id in owned_items:
            owned = True
    if not owned:
        await update.message.reply_text("لا تملك هذا العنصر.")
        return
    db.create_listing(user.id, item_type, item_id, price_type, price)
    await update.message.reply_text(f"تم عرض {item_type} {item_id} للبيع بـ {price} {price_type}")

async def battlepass_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bp = db.get_battle_pass(user.id)
    level = bp["level"]
    xp = bp["xp"]
    required_xp = level * config.BATTLE_PASS_XP_PER_LEVEL
    text = f"📊 **Battle Pass - الموسم 1**\n"
    text += f"المستوى: {level}/{config.MAX_BATTLE_PASS_LEVEL}\n"
    text += f"الخبرة: {xp}/{required_xp}\n\n"
    for lvl in range(1, min(level+1, config.MAX_BATTLE_PASS_LEVEL+1)):
        rewards = config.BATTLE_PASS_REWARDS.get(lvl, {})
        free = rewards.get("free")
        prem = rewards.get("premium")
        text += f"م {lvl}: مجاني - {free[0]} {free[1] if free[1] else ''}"
        if prem:
            text += f" | مميز - {prem[0]} {prem[1] if prem[1] else ''}"
        text += "\n"
    await update.message.reply_text(text, reply_markup=keyboards.battlepass_button())
