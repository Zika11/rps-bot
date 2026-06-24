import json, logging, asyncio, random
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import models, db, config, state, keyboards, game_logic, utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

models.init_db()

# ---------- الأوامر الأساسية ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u:
        db.create_user(user.id, user.username, user.first_name)
    else:
        today = date.today().isoformat()
        last = u.get("last_login")
        streak = int(u.get("login_streak",0))
        if last:
            last_date = date.fromisoformat(last[:10])
            diff = (date.today() - last_date).days
            if diff == 1: streak += 1
            elif diff > 1: streak = 1
        else:
            streak = 1
        days = (date.today() - date.fromisoformat(u["registered_date"][:10])).days if u.get("registered_date") else 0
        db.update_user(user.id, last_login=datetime.now().isoformat(), login_streak=streak, days_since_register=days)
        await game_logic.check_achievements(user.id, context)
    text = f"أهلاً {user.first_name}! اختر من القائمة:"
    await update.message.reply_text(text, reply_markup=keyboards.main_menu())

# ---------- معالج الأزرار ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    # الرجوع
    if data == "back_main":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=keyboards.main_menu())
    # القائمة الرئيسية
    elif data == "game":
        await query.edit_message_text("اختر نمط اللعب:", reply_markup=keyboards.game_mode_menu())
    elif data == "friends":
        await query.edit_message_text("الأصدقاء:", reply_markup=keyboards.friends_menu())
    elif data == "shop":
        await query.edit_message_text("المتجر:", reply_markup=keyboards.shop_categories())
    elif data == "clans":
        await query.edit_message_text("العشائر:", reply_markup=keyboards.clans_menu())
    elif data == "tasks":
        tasks = db.get_tasks()
        u = db.get_user(user.id)
        progress = json.loads(u.get("tasks_progress","{}") or "{}").get("tasks",{})
        text = "📋 المهام:\n"
        for t in tasks:
            done = progress.get(f"{t['task_id']}_done", False)
            text += f"{'✅' if done else '⭕'} {t['description']} (+{t['points_reward']} نقطة)\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
    elif data == "achievements":
        all_ach = db.get_achievements()
        u = db.get_user(user.id)
        earned = [a for a in (u.get("achievements") or "").split(",") if a]
        text = "🏅 الإنجازات:\n"
        for a in all_ach:
            icon = a["icon"] if a["ach_id"] in earned else "🔒"
            text += f"{icon} {a['name']} - {a['description']}\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
    elif data == "rating":
        top = db.get_top_ratings(10)
        text = "📊 أفضل 10 لاعبين:\n"
        for i, r in enumerate(top, 1):
            name = r["first_name"] or str(r["user_id"])
            text += f"{i}. {name} - {r['rating']}\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
    elif data == "language":
        u = db.get_user(user.id)
        new_lang = "en" if u["language"] == "ar" else "ar"
        db.update_user(user.id, language=new_lang)
        await query.edit_message_text("تم تغيير اللغة", reply_markup=keyboards.main_menu(new_lang))

    # أوضاع اللعب
    elif data == "solo":
        state.active_games[user.id] = {"type": "solo"}
        await query.edit_message_text("اختر حركتك:", reply_markup=keyboards.choice_buttons("solo"))
    elif data == "random":
        async with state.active_locks:
            if state.pending_matches:
                opp_id = state.pending_matches.pop(0)
                state.active_games[user.id] = {"type": "random", "opponent": opp_id}
                state.active_games[opp_id] = {"type": "random", "opponent": user.id}
                await query.edit_message_text("تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons("random"))
                await context.bot.send_message(opp_id, "تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons("random"))
            else:
                state.pending_matches.append(user.id)
                await query.edit_message_text("بانتظار لاعب آخر...")
    elif data == "friend":
        await query.edit_message_text("أرسل معرف الصديق (@username) لتحديه:")
        context.user_data["awaiting_friend_challenge"] = True
    elif data == "spock":
        from config import SPOCK_CHOICES
        buttons = [InlineKeyboardButton(icon, callback_data=f"spockpick_{key}") for key, icon in SPOCK_CHOICES.items()]
        await query.edit_message_text("اختر حركتك (Spock):", reply_markup=InlineKeyboardMarkup([buttons]))
    elif data == "story":
        await query.edit_message_text("وضع القصة قيد التطوير...", reply_markup=keyboards.back_button())
    # اختيار حركة
    elif data.startswith("pick_"):
        _, move, game_type = data.split("_")
        await process_move(update, context, move, game_type)
    elif data.startswith("spockpick_"):
        move = data.split("_",1)[1]
        await process_spock_move(update, context, move)

    # الأصدقاء
    elif data == "add_friend":
        await query.edit_message_text("أرسل @username لإضافته:")
        context.user_data["awaiting_friend_username"] = True
    elif data == "friend_requests":
        reqs = db.get_pending_requests(user.id)
        if not reqs:
            await query.edit_message_text("لا توجد طلبات.")
        else:
            buttons = []
            for sender_id in reqs:
                s = db.get_user(sender_id)
                name = s["first_name"] if s else str(sender_id)
                buttons.append([InlineKeyboardButton(f"قبول {name}", callback_data=f"accept_friend_{sender_id}"),
                                InlineKeyboardButton("رفض", callback_data=f"reject_friend_{sender_id}")])
            buttons.append([InlineKeyboardButton("رجوع", callback_data="friends")])
            await query.edit_message_text("طلبات الصداقة:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data == "friend_list":
        friends = db.get_friends(user.id)
        text = "👥 أصدقائي:\n" + "\n".join([f"- {db.get_user(f)['first_name']}" for f in friends]) if friends else "لا يوجد أصدقاء."
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
    elif data.startswith("accept_friend_"):
        sender = int(data.split("_")[-1])
        db.accept_friend_request(sender, user.id)
        await query.answer("تم القبول!")
    elif data.startswith("reject_friend_"):
        sender = int(data.split("_")[-1])
        db.reject_friend_request(sender, user.id)
        await query.answer("تم الرفض")

    # المتجر
    elif data == "shop_cards":
        items = db.get_shop_items()
        text = "🃏 بطاقات المتجر:\n"
        keyboard = []
        for i in items:
            text += f"{i['name']} - {i['price']} نقطة\n"
            keyboard.append([InlineKeyboardButton(f"شراء {i['name']}", callback_data=f"buy_{i['item_id']}")])
        keyboard.append([InlineKeyboardButton("رجوع", callback_data="shop")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("buy_") and "title" not in data and "theme" not in data:
        item_id = data.split("_",1)[1]
        u = db.get_user(user.id)
        item = next((i for i in db.get_shop_items() if i["item_id"]==item_id), None)
        if not item or u["points"] < item["price"]:
            await query.answer("نقاط غير كافية")
            return
        db.update_user(user.id, points=u["points"]-item["price"])
        owned = u.get("shop_items","").split(",")
        owned.append(item_id)
        db.update_user(user.id, shop_items=",".join([o for o in owned if o]))
        await query.answer("تم الشراء!")
    elif data == "shop_titles":
        import db as dbm
        conn = dbm.get_conn()
        titles = conn.execute("SELECT * FROM titles_shop").fetchall()
        conn.close()
        text = "🏷️ الألقاب:\n"
        kb = []
        for t in titles:
            text += f"{t['name']} - {t['price']}\n"
            kb.append([InlineKeyboardButton(f"شراء {t['name']}", callback_data=f"buy_title_{t['title_id']}")])
        kb.append([InlineKeyboardButton("رجوع", callback_data="shop")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("buy_title_"):
        tid = data.split("_",2)[2]
        u = db.get_user(user.id)
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM titles_shop WHERE title_id=?", (tid,)).fetchone()
        conn.close()
        if not row or u["points"] < row["price"]:
            await query.answer("نقاط غير كافية")
            return
        db.update_user(user.id, points=u["points"]-row["price"], title=row["name"])
        await query.answer("تم الشراء!")
    elif data == "shop_themes":
        conn = db.get_conn()
        themes = conn.execute("SELECT * FROM themes_shop").fetchall()
        conn.close()
        text = "🎨 الثيمات:\n"
        kb = []
        for th in themes:
            text += f"{th['name']} - {th['price']}\n"
            kb.append([InlineKeyboardButton(f"شراء {th['name']}", callback_data=f"buy_theme_{th['theme_id']}")])
        kb.append([InlineKeyboardButton("رجوع", callback_data="shop")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("buy_theme_"):
        tid = data.split("_",2)[2]
        u = db.get_user(user.id)
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM themes_shop WHERE theme_id=?", (tid,)).fetchone()
        conn.close()
        if not row or u["points"] < row["price"]:
            await query.answer("نقاط غير كافية")
            return
        db.update_user(user.id, points=u["points"]-row["price"], theme=tid)
        await query.answer("تم الشراء!")
    elif data == "treasure_box":
        u = db.get_user(user.id)
        if u["points"] < config.TREASURE_BOX_PRICE:
            await query.answer("تحتاج 100 نقطة")
            return
        db.update_user(user.id, points=u["points"] - config.TREASURE_BOX_PRICE)
        reward = random.choice(config.TREASURE_REWARDS)
        typ, val = reward
        if typ == "points":
            db.update_user(user.id, points=int(u.get("points",0)) + val)
        elif typ == "gems":
            db.update_user(user.id, gems=int(u.get("gems",0)) + val)
        elif typ == "title":
            db.update_user(user.id, title=val)
        elif typ == "theme":
            db.update_user(user.id, theme=val)
        await query.answer(f"حصلت على {val}!")

    # العشائر
    elif data == "clan_create":
        await query.edit_message_text("أرسل اسم العشيرة:")
        context.user_data["awaiting_clan_name"] = True
    elif data == "clan_join":
        await query.edit_message_text("أرسل اسم العشيرة للانضمام:")
        context.user_data["awaiting_join_clan"] = True
    elif data == "clan_ranking":
        clans = db.get_all_clans()
        text = "🏆 ترتيب العشائر:\n" + "\n".join([f"{i+1}. {c['name']} - {c['points']} نقطة" for i,c in enumerate(clans[:10])])
        await query.edit_message_text(text, reply_markup=keyboards.back_button())

# ---------- دوال الحركات ----------
async def process_move(update, context, move, game_type):
    query = update.callback_query
    user = query.from_user
    game = state.active_games.get(user.id)
    if not game:
        await query.edit_message_text("انتهت اللعبة.")
        return
    if game_type == "solo":
        bot_move = utils.smart_bot_choice(user.id)
        result = game_logic.get_result(move, bot_move)
        await finish_game(update, context, user.id, move, bot_move, result)
    elif game_type == "random":
        opp_id = game.get("opponent")
        if not opp_id: return
        game["move"] = move
        opp_game = state.active_games.get(opp_id)
        if opp_game and "move" in opp_game:
            opp_move = opp_game["move"]
            res1 = game_logic.get_result(move, opp_move)
            res2 = game_logic.get_result(opp_move, move)
            await finish_game(update, context, user.id, move, opp_move, res1)
            await context.bot.send_message(opp_id, f"نتيجة المباراة: {res2}")
            del state.active_games[user.id]
            del state.active_games[opp_id]
        else:
            await query.edit_message_text("تم تسجيل حركتك، بانتظار الخصم...")

async def process_spock_move(update, context, move):
    query = update.callback_query
    user = query.from_user
    from config import SPOCK_CHOICES, SPOCK_WIN_MAP
    bot_move = random.choice(list(SPOCK_CHOICES.keys()))
    if move == bot_move:
        result = "draw"
    elif bot_move in SPOCK_WIN_MAP[move]:
        result = "win"
    else:
        result = "loss"
    await finish_game(update, context, user.id, move, bot_move, result, spock=True)

async def finish_game(update, context, user_id, user_move, opp_move, result, spock=False):
    u = db.get_user(user_id)
    theme = utils.get_choices_for_user(user_id)
    user_icon = theme.get(user_move, user_move)
    opp_icon = theme.get(opp_move, opp_move)
    text = f"أنت: {user_icon} vs الخصم: {opp_icon}\nالنتيجة: {result}"
    if update.callback_query:
        await update.callback_query.edit_message_text(text)

    # تحديث الإحصائيات
    pts = 0
    if result == "win":
        db.update_user(user_id, wins=u["wins"]+1, win_streak=u.get("win_streak",0)+1, streak_count=u.get("streak_count",0)+1)
        pts = 10
    elif result == "loss":
        db.update_user(user_id, losses=u["losses"]+1, win_streak=0, streak_count=max(0,u.get("streak_count",0)-1))
    else:
        db.update_user(user_id, draws=u["draws"]+1)
        pts = 5
    if user_move == "rock":
        db.update_user(user_id, rock_used=u.get("rock_used",0)+1)

    db.update_user(user_id, points=u["points"]+pts, gems=u.get("gems",0)+1)

    rating = db.get_user_rating(user_id) or config.DEFAULT_RATING
    opp_rating = config.DEFAULT_RATING
    if "opponent" in state.active_games.get(user_id, {}):
        opp = state.active_games[user_id]["opponent"]
        opp_rating = db.get_user_rating(opp) or config.DEFAULT_RATING
    expected = 1 / (1 + 10**((opp_rating - rating)/400))
    score = 1 if result == "win" else 0.5 if result == "draw" else 0
    new_rating = rating + config.RATING_K * (score - expected)
    db.update_rating(user_id, int(new_rating))

    await game_logic.check_achievements(user_id, context)
    game_logic.add_clan_points(user_id, 2)
    utils.update_user_moves(user_id, user_move)

# ---------- معالج النصوص ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text.strip()
    if context.user_data.get("awaiting_friend_username"):
        target = db.get_user_by_username(msg.lstrip("@"))
        if not target:
            await update.message.reply_text("المستخدم غير موجود.")
            return
        if target["user_id"] == user.id:
            await update.message.reply_text("لا يمكنك إضافة نفسك.")
            return
        db.send_friend_request(user.id, target["user_id"])
        await update.message.reply_text("تم إرسال طلب الصداقة.")
        context.user_data["awaiting_friend_username"] = False
    elif context.user_data.get("awaiting_clan_name"):
        if db.get_clan(msg):
            await update.message.reply_text("اسم العشيرة موجود مسبقاً.")
            return
        if db.create_clan(msg, user.id):
            db.update_user(user.id, clan=msg)
            await update.message.reply_text(f"تم إنشاء عشيرة {msg}!")
        else:
            await update.message.reply_text("حدث خطأ.")
        context.user_data["awaiting_clan_name"] = False
    elif context.user_data.get("awaiting_join_clan"):
        clan = db.get_clan(msg)
        if not clan:
            await update.message.reply_text("العشيرة غير موجودة.")
            return
        db.update_user(user.id, clan=msg)
        await update.message.reply_text(f"انضممت إلى {msg}!")
        context.user_data["awaiting_join_clan"] = False
    elif context.user_data.get("awaiting_friend_challenge"):
        target = db.get_user_by_username(msg.lstrip("@"))
        if not target:
            await update.message.reply_text("لم يتم العثور على المستخدم.")
            return
        # يمكن تخزين تحدي الصديق في active_games، إلخ.
        await update.message.reply_text(f"تحدي صديق قيد التطوير (سيتم إعلام {target['first_name']}).")
        context.user_data["awaiting_friend_challenge"] = False

# ---------- تشغيل ----------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
