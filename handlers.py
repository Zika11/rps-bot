import json
import random
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, keyboards, game_logic, utils, state

logger = logging.getLogger(__name__)

# ========== البطولات ==========
async def tournament_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    # ✅ إصلاح: البحث عن بطولة مفتوحة أولاً بدل إنشاء جديدة كل مرة
    conn = db.get_conn()
    row = conn.execute("SELECT tour_id FROM tournaments WHERE status='open' LIMIT 1").fetchone()
    conn.close()
    
    if row:
        tour_id = row[0]
    else:
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
            # ✅ إصلاح: bracket يكون dict وليس list
            bracket = {
                "round1": [
                    {"p1": players[0], "p2": players[1], "winner": None},
                    {"p1": players[2], "p2": players[3], "winner": None},
                    {"p1": players[4], "p2": players[5], "winner": None},
                    {"p1": players[6], "p2": players[7], "winner": None},
                ]
            }
            db.update_tournament(tour_id, status="started", current_round=1,
                                 bracket=json.dumps(bracket))
            await context.bot.send_message(user.id, "بدأت البطولة! سيتم إعلامك بالخصم.")
        await query.edit_message_text("تم تسجيلك في البطولة ✅")
    else:
        await query.edit_message_text("البطولة ممتلئة أو حدث خطأ.")

# ========== الأصدقاء ==========
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

# ========== المتجر ==========
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
    success, msg = db.buy_item(user.id, "title", title_id)
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
    success, msg = db.buy_item(user.id, "theme", theme_id)
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

async def treasure_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    # ✅ إصلاح stale-read
    u = db.get_user(user.id)
    if u["points"] < config.TREASURE_BOX_PRICE:
        await query.answer("تحتاج 100 نقطة")
        return
    
    # خصم النقاط وحفظ القيمة الجديدة
    new_points = u["points"] - config.TREASURE_BOX_PRICE
    db.update_user(user.id, points=new_points)
    
    reward = random.choice(config.TREASURE_REWARDS)
    typ, val = reward[0], reward[1]
    
    if typ == "points":
        # ✅ استخدام new_points بدلاً من u["points"] القديمة
        db.update_user(user.id, points=new_points + val)
    elif typ == "gems":
        current_gems = db.get_user(user.id)["gems"]
        db.update_user(user.id, gems=current_gems + val)
    elif typ == "title":
        db.update_user(user.id, title=val)
    elif typ == "theme":
        db.update_user(user.id, theme=val)
    elif typ == "booster":
        owned = u.get("shop_items", "")
        if owned:
            owned += f",{val}"
        else:
            owned = val
        db.update_user(user.id, shop_items=owned)
    
    await query.answer(f"🎁 حصلت على {val}!")

async def frames_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("اختر إطاراً:", reply_markup=keyboards.frame_shop())

async def buy_frame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    frame = query.data.split("_")[-1]
    success, msg = db.buy_item(user.id, "frame", frame)
    if success:
        await query.answer("تم شراء الإطار! استخدم /me لرؤيته.")
    else:
        await query.answer(msg)

async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("السوق:", reply_markup=keyboards.market_menu())

async def market_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    listings = db.get_active_listings()
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
    success, msg = db.buy_item(user.id, "ability", ability)
    if success:
        await query.answer(f"تم شراء {config.ABILITIES[ability]['name']}!")
    else:
        await query.answer(msg)

# ========== العشائر ==========
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

# ========== Clan Treasury ==========
async def clan_treasury_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    clan_name = u.get("clan")
    if not clan_name:
        await query.answer("أنت لست في عشيرة!")
        return
    await query.edit_message_text(f"🏦 خزينة {clan_name}", reply_markup=keyboards.clan_treasury_menu(clan_name))

async def treasury_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clan_name = query.data.split("_")[-1]
    t = db.get_clan_treasury(clan_name)
    if not t:
        await query.edit_message_text("الخزينة فارغة.")
        return
    upgrades = json.loads(t["upgrades"] or "{}")
    text = f"🏦 خزينة {clan_name}\n💰 نقاط: {t['points']}\n💎 جواهر: {t['gems']}\n\nالتطويرات:\n"
    for up_id, up_data in config.CLAN_UPGRADES.items():
        lvl = upgrades.get(up_id, 0)
        text += f"{up_data['name']}: مستوى {lvl}/{up_data['levels']}\n"
    await query.edit_message_text(text, reply_markup=keyboards.clan_treasury_menu(clan_name))

async def treasury_donate_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    clan_name = query.data.split("_")[-1]
    u = db.get_user(user.id)
    if u["points"] < 50:
        await query.answer("تحتاج 50 نقطة على الأقل")
        return
    db.update_user(user.id, points=u["points"] - 50)
    db.add_clan_treasury_points(clan_name, 50)
    await query.answer("تم التبرع بـ 50 نقطة للعشيرة!")

async def treasury_donate_gems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    clan_name = query.data.split("_")[-1]
    u = db.get_user(user.id)
    if u["gems"] < 5:
        await query.answer("تحتاج 5 جواهر")
        return
    db.update_user(user.id, gems=u["gems"] - 5)
    db.add_clan_treasury_gems(clan_name, 5)
    await query.answer("تم التبرع بـ 5 جواهر!")

async def treasury_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clan_name = query.data.split("_")[-1]
    buttons = []
    for up_id, up_data in config.CLAN_UPGRADES.items():
        buttons.append([InlineKeyboardButton(up_data['name'], callback_data=f"do_upgrade_{clan_name}_{up_id}")])
    buttons.append([InlineKeyboardButton("رجوع", callback_data=f"treasury_view_{clan_name}")])
    await query.edit_message_text("اختر تطويراً:", reply_markup=InlineKeyboardMarkup(buttons))

async def do_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # ✅ إصلاح parsing لأسماء العشائر التي تحتوي على _
    parts = query.data.split("_", 3)  # do_upgrade_CLANNAME_UPID
    # parts = ["do", "upgrade", "clan_name_here", "up_id"]
    if len(parts) < 4:
        await query.answer("صيغة خاطئة!")
        return
    clan_name = parts[2]
    upgrade_id = parts[3]
    
    success = db.upgrade_clan(clan_name, upgrade_id)
    if success:
        await query.answer("تم التطوير بنجاح!")
    else:
        await query.answer("فشل التطوير. نقاط غير كافية أو وصلت لأقصى مستوى.")
    await treasury_view(update, context)

async def clan_war_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    season = db.get_active_war_season()
    if not season:
        await query.edit_message_text("لا يوجد موسم حرب عشائر نشط حالياً.")
        return
    conn = db.get_conn()
    scores = conn.execute("SELECT clan_name, region, score FROM clan_war_scores WHERE season_id=? ORDER BY score DESC", (season["season_id"],)).fetchall()
    conn.close()
    text = f"⚔️ موسم حرب العشائر (من {season['start_date'][:10]} إلى {season['end_date'][:10]})\n\n"
    if scores:
        text += "النتائج:\n"
        for s in scores:
            text += f"{s['clan_name']} - {s['region']}: {s['score']} نقطة\n"
    else:
        text += "لا توجد نتائج بعد."
    await query.edit_message_text(text, reply_markup=keyboards.back_button("clans"))

# ========== تحديات القنوات ==========
async def channel_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("تحدي القنوات: أرسل هذه الرسالة في قناة/مجموعة واطلب من شخص الرد بـ /accept")
    context.user_data["channel_challenge_active"] = True

# ========== وضع القصة و Spock ==========
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

# ========== تحديات المشاهدة (Spectator) ==========
async def challenge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة الشخص الذي تريد تحديه.")
        return
    opponent = update.message.reply_to_message.from_user
    if opponent.id == user.id:
        await update.message.reply_text("لا يمكنك تحدي نفسك.")
        return
    challenge_id = str(uuid.uuid4())[:8]
    async with state.spectate_lock:
        state.spectate_challenges[challenge_id] = {
            "players": [user.id, opponent.id],
            "chat_id": chat_id,
            "moves": {},
            "status": "waiting"
        }
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول التحدي", callback_data=f"accept_challenge_{challenge_id}"),
         InlineKeyboardButton("❌ رفض", callback_data=f"reject_challenge_{challenge_id}")]
    ])
    await context.bot.send_message(opponent.id, f"{user.first_name} يتحداك في مجموعة! اقبل؟", reply_markup=keyboard)
    await update.message.reply_text(f"تم إرسال التحدي إلى {opponent.first_name}. بانتظار القبول...")

async def accept_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    challenge_id = data.split("_")[-1]
    async with state.spectate_lock:
        challenge = state.spectate_challenges.get(challenge_id)
        if not challenge:
            await query.answer("انتهت صلاحية التحدي.")
            return
        if user.id not in challenge["players"]:
            await query.answer("هذا التحدي ليس لك.")
            return
        challenge["status"] = "active"
        p1, p2 = challenge["players"]
        user1 = db.get_user(p1)["first_name"]
        user2 = db.get_user(p2)["first_name"]
        await context.bot.send_message(challenge["chat_id"], f"🔥 بدأت المباراة بين {user1} و {user2}! شاهدوا النتيجة هنا.")
        for pid in [p1, p2]:
            await context.bot.send_message(pid, "المباراة بدأت! اختر حركتك:", reply_markup=keyboards.choice_buttons(f"spectate_{challenge_id}"))
    await query.edit_message_text("تم قبول التحدي. اذهب للمجموعة للمشاهدة.")

async def reject_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    challenge_id = data.split("_")[-1]
    async with state.spectate_lock:
        state.spectate_challenges.pop(challenge_id, None)
    await query.edit_message_text("تم رفض التحدي.")

# ========== Spectator Room ==========
async def spectate_room_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    user = query.from_user
    room_id = str(uuid.uuid4())[:8]
    await context.bot.send_message(user.id, "اختر حركتك (للمشاهدة):", reply_markup=keyboards.choice_buttons(f"spectate_{room_id}"))
    db.create_spectator_room(room_id, user.id, None, chat_id)
    await query.answer("تم إنشاء غرفة مشاهدة. اختر حركتك في الخاص.")

async def spectate_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    room_id = query.data.split("_")[-1]
    room = db.get_spectator_room(room_id)
    if not room or room["status"] != "waiting":
        await query.answer("انتهت الغرفة.")
        return
    if user.id == room["player1"]:
        await query.answer("لا يمكنك الانضمام إلى غرفتك!")
        return
    db.update_spectator_room(room_id, player2=user.id, status="active")
    await context.bot.send_message(user.id, "اختر حركتك:", reply_markup=keyboards.choice_buttons(f"spectate_{room_id}"))
    await query.answer("تم قبول التحدي! اختر حركتك في الخاص.")

# ========== Season ==========
async def season_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    season = db.get_active_season()
    if not season:
        await update.message.reply_text("لا يوجد موسم نشط حالياً.")
        return
    conn = db.get_conn()
    top = conn.execute("""
        SELECT u.first_name, s.rating, s.wins FROM season_rankings s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.season_id = ? ORDER BY s.rating DESC LIMIT 5
    """, (season["season_id"],)).fetchall()
    conn.close()
    text = f"🏆 **موسم {season['name']}**\nينتهي في {season['end_date'][:10]}\n\nأفضل 5 لاعبين:\n"
    for i, r in enumerate(top, 1):
        text += f"{i}. {r['first_name']} - {r['rating']} (انتصارات: {r['wins']})\n"
    await update.message.reply_text(text)

# ========== World Boss ==========
async def boss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    boss = db.get_world_boss()
    if not boss or boss["status"] != "active":
        await update.message.reply_text("لا يوجد زعيم عالمي حالياً. سيظهر قريباً!")
        return
    hp_percent = (boss["current_hp"] / boss["max_hp"]) * 100
    text = f"🐉 **{boss['name']}**\n❤️ الصحة: {boss['current_hp']}/{boss['max_hp']} ({hp_percent:.1f}%)\n\nاضغط أدناه للهجوم!"
    await update.message.reply_text(text, reply_markup=keyboards.world_boss_menu())

async def boss_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    boss = db.get_world_boss()
    if not boss or boss["status"] != "active":
        await query.answer("انتهى الزعيم!")
        return
    damage = random.randint(10, 40)
    db.add_boss_damage(user.id, damage)
    db.update_user(user.id, points=db.get_user(user.id)["points"] + 5)
    boss = db.get_world_boss()
    if boss["status"] == "defeated":
        top_damagers = db.get_top_boss_damagers()
        if top_damagers:
            winner = top_damagers[0]
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🎉 **{winner['first_name']}** وجه الضربة القاضية للزعيم! ربح {config.BOSS_REWARD_TOP_DAMAGE[1]} نقطة!")
        await query.edit_message_text("🐉 الزعيم انهزم! مكافآت قريباً.")
    else:
        await query.answer(f"ألحقت {damage} ضرراً بالزعيم! +5 نقاط")
