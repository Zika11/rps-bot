import json, random, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, keyboards, game_logic, utils

logger = logging.getLogger(__name__)

# ---------- البطولات ----------
async def tournament_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    tour_id = context.user_data.get("tour_created")
    if not tour_id:
        tour_id = db.create_tournament("بطولة الأبطال")
        context.user_data["tour_created"] = tour_id
    tour = db.get_tournament(tour_id)
    players = json.loads(tour["players"] or "[]")
    text = f"🏆 {tour['name']}\nالمشاركون: {len(players)}/8"
    text += "\n✅ أنت مسجل" if user.id in players else "\nاضغط للانضمام"
    await query.edit_message_text(text, reply_markup=keyboards.tournament_keyboard(tour_id))

async def join_tournament_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    tour_id = int(query.data.split("_")[-1])
    ok = db.join_tournament(tour_id, user.id)
    if ok:
        tour = db.get_tournament(tour_id)
        players = json.loads(tour["players"] or "[]")
        if len(players) == 8:
            db.update_tournament(tour_id, status="started", current_round=1,
                                 bracket=json.dumps(players))
            await context.bot.send_message(user.id, "بدأت البطولة! سيتم إعلامك بالخصم.")
        await query.edit_message_text("تم تسجيلك في البطولة ✅")
    else:
        await query.edit_message_text("البطولة ممتلئة أو حدث خطأ.")

# ---------- الأصدقاء ----------
async def friends_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("قائمة الأصدقاء:", reply_markup=keyboards.friends_menu())

async def add_friend_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل معرف المستخدم (@username) الذي تريد إضافته:")
    context.user_data["awaiting_friend_username"] = True

async def process_friend_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = update.message.text.strip().lstrip("@")
    target = db.get_user_by_username(username)
    if not target:
        await update.message.reply_text("لم يتم العثور على مستخدم بهذا المعرف.")
        return
    if target["user_id"] == user.id:
        await update.message.reply_text("لا يمكنك إضافة نفسك.")
        return
    db.send_friend_request(user.id, target["user_id"])
    await update.message.reply_text("تم إرسال طلب الصداقة.")
    context.user_data["awaiting_friend_username"] = False

async def friend_requests_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    requests = db.get_pending_requests(user.id)
    if not requests:
        await query.edit_message_text("لا توجد طلبات صداقة.")
        return
    buttons = []
    for sender_id in requests:
        sender = db.get_user(sender_id)
        name = sender["first_name"] if sender else str(sender_id)
        buttons.append([InlineKeyboardButton(f"قبول من {name}", callback_data=f"accept_friend_{sender_id}"),
                        InlineKeyboardButton("رفض", callback_data=f"reject_friend_{sender_id}")])
    buttons.append([InlineKeyboardButton("رجوع", callback_data="friends")])
    await query.edit_message_text("طلبات الصداقة:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_friend_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    if data.startswith("accept_friend_"):
        sender_id = int(data.split("_")[-1])
        db.accept_friend_request(sender_id, user.id)
        await query.answer("تم قبول الصداقة")
    elif data.startswith("reject_friend_"):
        sender_id = int(data.split("_")[-1])
        db.reject_friend_request(sender_id, user.id)
        await query.answer("تم رفض الطلب")
    # تحديث القائمة
    await friend_requests_list(update, context)

async def friend_list_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    friends = db.get_friends(user.id)
    if not friends:
        await query.edit_message_text("لا يوجد أصدقاء بعد.")
        return
    lines = []
    for fid in friends:
        friend = db.get_user(fid)
        name = friend["first_name"] if friend else "Unknown"
        lines.append(f"- {name}")
    text = "👥 أصدقائي:\n" + "\n".join(lines)
    await query.edit_message_text(text, reply_markup=keyboards.back_button())

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
    u = db.get_user(user.id)
    item = next((i for i in db.get_shop_items() if i["item_id"] == item_id), None)
    if not item or u["points"] < item["price"]:
        await query.answer("نقاط غير كافية")
        return
    db.update_user(user.id, points=u["points"] - item["price"])
    owned = (u.get("shop_items") or "").split(",")
    owned.append(item_id)
    db.update_user(user.id, shop_items=",".join([o for o in owned if o]))
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
    u = db.get_user(user.id)
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM titles_shop WHERE title_id=?", (title_id,)).fetchone()
    conn.close()
    if not row or u["points"] < row["price"]:
        await query.answer("نقاط غير كافية")
        return
    db.update_user(user.id, points=u["points"] - row["price"], title=row["name"])
    await query.answer("تم شراء اللقب!")

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
    u = db.get_user(user.id)
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM themes_shop WHERE theme_id=?", (theme_id,)).fetchone()
    conn.close()
    if not row or u["points"] < row["price"]:
        await query.answer("نقاط غير كافية")
        return
    db.update_user(user.id, points=u["points"] - row["price"], theme=theme_id)
    await query.answer("تم شراء الثيم!")

async def treasure_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    if u["points"] < config.TREASURE_BOX_PRICE:
        await query.answer("تحتاج 100 نقطة")
        return
    db.update_user(user.id, points=u["points"] - config.TREASURE_BOX_PRICE)
    reward = random.choice(config.TREASURE_REWARDS)
    typ, val = reward[0], reward[1]
    if typ == "points":
        db.update_user(user.id, points=u["points"] + val)  # u still has old points, so careful: we deduct then add
        # But better to do atomic: points = (u["points"] - price) + val
        # Since we already deducted, we just add
    elif typ == "gems":
        db.update_user(user.id, gems=int(u.get("gems",0)) + val)
    elif typ == "title":
        db.update_user(user.id, title=val)
    elif typ == "theme":
        db.update_user(user.id, theme=val)
    elif typ == "booster":
        owned = u.get("shop_items","") + f",{val}" if u.get("shop_items") else val
        db.update_user(user.id, shop_items=owned)
    await query.answer(f"حصلت على {val}!")

# ---------- العشائر ----------
async def clans_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("العشائر:", reply_markup=keyboards.clans_menu())

async def clan_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل اسم العشيرة الجديدة:")
    context.user_data["awaiting_clan_name"] = True

async def process_clan_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = update.message.text.strip()
    if db.get_clan(name):
        await update.message.reply_text("الاسم موجود مسبقاً.")
        return
    if db.create_clan(name, user.id):
        db.update_user(user.id, clan=name)
        await update.message.reply_text(f"تم إنشاء العشيرة {name}!")
    else:
        await update.message.reply_text("حدث خطأ.")
    context.user_data["awaiting_clan_name"] = False

async def clan_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل اسم العشيرة التي تريد الانضمام إليها:")
    context.user_data["awaiting_join_clan"] = True

async def process_join_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    clan_name = update.message.text.strip()
    clan = db.get_clan(clan_name)
    if not clan:
        await update.message.reply_text("العشيرة غير موجودة.")
        return
    db.update_user(user.id, clan=clan_name)
    await update.message.reply_text(f"انضممت إلى {clan_name}!")
    context.user_data["awaiting_join_clan"] = False

async def clan_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clans = db.get_all_clans()
    text = "🏆 ترتيب العشائر:\n"
    if clans:
        text += "\n".join([f"{i+1}. {c['name']} - {c['points']} نقطة" for i,c in enumerate(clans[:10])])
    else:
        text += "لا توجد عشائر بعد."
    await query.edit_message_text(text, reply_markup=keyboards.back_button())

# ---------- تحديات القنوات ----------
async def channel_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("تحدي القنوات: أرسل هذه الرسالة في قناة/مجموعة واطلب من شخص الرد بـ /accept")
    context.user_data["channel_challenge_active"] = True

# ---------- وضع القصة و Spock ----------
async def story_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("وضع القصة قيد التطوير...", reply_markup=keyboards.back_button())

async def spock_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    from config import SPOCK_CHOICES
    buttons = [InlineKeyboardButton(icon, callback_data=f"spockpick_{key}") for key, icon in SPOCK_CHOICES.items()]
    await query.edit_message_text("اختر حركتك (Spock):", reply_markup=InlineKeyboardMarkup([buttons]))
