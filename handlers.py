import json, logging, asyncio, random
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import models, db, config, state, keyboards, game_logic, utils, handlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
models.init_db()

# ---------- أوامر أساسية ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u:
        db.create_user(user.id, user.username, user.first_name, "ar")
    else:
        # تحديث آخر دخول و login streak
        today = date.today().isoformat()
        last_login = u.get("last_login")
        streak = int(u.get("login_streak", 0))
        if last_login:
            last_date = date.fromisoformat(last_login[:10])
            if (date.today() - last_date).days == 1:
                streak += 1
            elif (date.today() - last_date).days > 1:
                streak = 1
        else:
            streak = 1
        days_registered = (date.today() - date.fromisoformat(u["registered_date"][:10])).days if u.get("registered_date") else 0
        db.update_user(user.id, last_login=datetime.now().isoformat(), login_streak=streak, days_since_register=days_registered)
        await game_logic.check_achievements(user.id, context)
        # مهمة تسجيل الدخول
        await game_logic.check_and_complete_task(user.id, "task_1", context, 1)  # مثال
    text = f"أهلاً {user.first_name}! اختر من القائمة:"
    await update.message.reply_text(text, reply_markup=keyboards.main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    # القائمة الرئيسية
    if data == "back_main":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=keyboards.main_menu())
    elif data == "game":
        await query.edit_message_text("اختر نمط اللعب:", reply_markup=keyboards.game_mode_menu())
    elif data == "friends":
        await handlers.friends_menu_handler(update, context)
    elif data == "shop":
        await handlers.shop_main(update, context)
    elif data == "clans":
        await handlers.clans_menu_handler(update, context)
    elif data == "tasks":
        # عرض المهام
        tasks = db.get_tasks()
        u = db.get_user(user.id)
        progress = json.loads(u.get("tasks_progress", "{}") or "{}").get("tasks", {})
        text = "📋 المهام:\n"
        for t in tasks:
            done = progress.get(f"{t['task_id']}_done", False)
            status = "✅" if done else "⭕"
            text += f"{status} {t['description']} (+{t['points_reward']} نقطة)\n"
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
        # تغيير اللغة
        u = db.get_user(user.id)
        new_lang = "en" if u["language"] == "ar" else "ar"
        db.update_user(user.id, language=new_lang)
        await query.edit_message_text("تم تغيير اللغة", reply_markup=keyboards.main_menu(new_lang))

    # أوضاع اللعب
    elif data == "solo":
        await start_solo_game(update, context)
    elif data == "random":
        await random_matchmaking(update, context)
    elif data == "friend":
        await query.edit_message_text("أرسل معرف الصديق (@username) لتحديه:")
        context.user_data["awaiting_friend_challenge"] = True
    elif data == "channel":
        await handlers.channel_challenge(update, context)
    elif data == "spock":
        await handlers.spock_mode(update, context)
    elif data == "story":
        await handlers.story_mode(update, context)

    # اختيار الحركات
    elif data.startswith("pick_"):
        _, move, game_type = data.split("_")
        await process_move(update, context, move, game_type)
    elif data.startswith("spockpick_"):
        move = data.split("_", 1)[1]
        await process_spock_move(update, context, move)

    # الأصدقاء
    elif data == "add_friend":
        await handlers.add_friend_start(update, context)
    elif data == "friend_requests":
        await handlers.friend_requests_list(update, context)
    elif data == "friend_list":
        await handlers.friend_list_display(update, context)
    elif data.startswith("accept_friend_") or data.startswith("reject_friend_"):
        await handlers.handle_friend_action(update, context)

    # المتجر
    elif data == "shop_cards":
        await handlers.shop_cards(update, context)
    elif data.startswith("buy_") and not data.startswith("buy_title") and not data.startswith("buy_theme"):
        await handlers.buy_item(update, context)
    elif data == "shop_titles":
        await handlers.shop_titles(update, context)
    elif data.startswith("buy_title_"):
        await handlers.buy_title(update, context)
    elif data == "shop_themes":
        await handlers.shop_themes(update, context)
    elif data.startswith("buy_theme_"):
        await handlers.buy_theme(update, context)
    elif data == "treasure_box":
        await handlers.treasure_box(update, context)

    # العشائر
    elif data == "clan_create":
        await handlers.clan_create(update, context)
    elif data == "clan_join":
        await handlers.clan_join(update, context)
    elif data == "clan_ranking":
        await handlers.clan_ranking(update, context)

    # البطولات
    elif data == "tournament":
        await handlers.tournament_menu(update, context)
    elif data.startswith("join_tournament_"):
        await handlers.join_tournament_handler(update, context)

# ---------- دوال اللعب ----------
async def start_solo_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    # إنشاء لعبة فردية
    state.active_games[user.id] = {"type": "solo"}
    await query.edit_message_text("اختر حركتك:", reply_markup=keyboards.choice_buttons("solo"))

async def random_matchmaking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    async with state.active_locks:
        # البحث عن لاعب آخر ينتظر
        if state.pending_matches:
            opponent_id = state.pending_matches.pop(0)
            # بدء لعبة بينهما
            state.active_games[user.id] = {"type": "random", "opponent": opponent_id}
            state.active_games[opponent_id] = {"type": "random", "opponent": user.id}
            await query.edit_message_text("تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons("random"))
            await context.bot.send_message(opponent_id, "تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons("random"))
        else:
            state.pending_matches.append(user.id)
            await query.edit_message_text("بانتظار لاعب آخر...")

async def process_move(update: Update, context: ContextTypes.DEFAULT_TYPE, move, game_type):
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
        if not opp_id:
            await query.edit_message_text("خطأ.")
            return
        # تخزين حركة المستخدم
        game["move"] = move
        opp_game = state.active_games.get(opp_id)
        if opp_game and "move" in opp_game:
            # كلا اللاعبين اختاروا
            opp_move = opp_game["move"]
            result_p1 = game_logic.get_result(move, opp_move)
            result_p2 = game_logic.get_result(opp_move, move)
            # إرسال النتائج
            await finish_game(update, context, user.id, move, opp_move, result_p1)
            await context.bot.send_message(opp_id, f"نتيجة المباراة: {result_p2}")
            # تنظيف
            del state.active_games[user.id]
            del state.active_games[opp_id]
        else:
            await query.edit_message_text("تم تسجيل حركتك، بانتظار الخصم...")

async def process_spock_move(update: Update, context: ContextTypes.DEFAULT_TYPE, move):
    query = update.callback_query
    user = query.from_user
    # بوت عشوائي في Spock
    from config import SPOCK_WIN_MAP, SPOCK_CHOICES
    bot_move = random.choice(list(SPOCK_CHOICES.keys()))
    if move == bot_move:
        result = "draw"
    elif bot_move in SPOCK_WIN_MAP[move]:
        result = "win"
    else:
        result = "loss"
    await finish_game(update, context, user.id, move, bot_move, result, spock=True)
    # إرسال رسالة توضح النتيجة مع الأيقونات
    u = db.get_user(user.id)
    theme_icons = utils.get_choices_for_user(user.id)
    user_icon = theme_icons.get(move, SPOCK_CHOICES.get(move, move))
    bot_icon = theme_icons.get(bot_move, SPOCK_CHOICES.get(bot_move, bot_move))
    await query.edit_message_text(f"أنت: {user_icon} vs بوت: {bot_icon}\nالنتيجة: {result}")

async def finish_game(update, context, user_id, user_move, opp_move, result, spock=False):
    query = update.callback_query
    u = db.get_user(user_id)
    theme_icons = utils.get_choices_for_user(user_id)
    user_icon = theme_icons.get(user_move, user_move)
    opp_icon = theme_icons.get(opp_move, opp_move)
    text = f"أنت: {user_icon} vs الخصم: {opp_icon}\nالنتيجة: {result}"
    await query.edit_message_text(text)

    # تحديث الإحصائيات
    points_change = 0
    if result == "win":
        db.update_user(user_id, wins=int(u["wins"])+1, win_streak=int(u.get("win_streak",0))+1,
                       streak_count=int(u.get("streak_count",0))+1)
        points_change = 10
    elif result == "loss":
        db.update_user(user_id, losses=int(u["losses"])+1, win_streak=0,
                       streak_count=max(0, int(u.get("streak_count",0))-1))
    elif result == "draw":
        db.update_user(user_id, draws=int(u["draws"])+1)
        points_change = 5

    # تحديث استخدام الصخرة
    if user_move == "rock":
        db.update_user(user_id, rock_used=int(u.get("rock_used",0))+1)

    # إضافة نقاط وجواهر
    db.update_user(user_id, points=int(u["points"])+points_change, gems=int(u.get("gems",0))+1)

    # تحديث التصنيف
    rating = db.get_user_rating(user_id) or config.DEFAULT_RATING
    # ELO بسيط
    opp_rating = config.DEFAULT_RATING
    if "opponent" in state.active_games.get(user_id, {}):
        opp = state.active_games[user_id]["opponent"]
        opp_rating = db.get_user_rating(opp) or config.DEFAULT_RATING
    expected = 1 / (1 + 10**((opp_rating - rating)/400))
    score = 1 if result == "win" else 0.5 if result == "draw" else 0
    new_rating = rating + config.RATING_K * (score - expected)
    db.update_rating(user_id, int(new_rating))

    # تحديث المهام والإنجازات
    await game_logic.check_and_complete_task(user_id, "task_5", context, 1)  # مثال عام
    await game_logic.check_achievements(user_id, context)
    game_logic.add_clan_points(user_id, 2)

    utils.update_user_moves(user_id, user_move)

# ---------- معالج النصوص (أسماء المستخدمين، تحديات..) ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text
    if context.user_data.get("awaiting_friend_username"):
        await handlers.process_friend_username(update, context)
    elif context.user_data.get("awaiting_clan_name"):
        await handlers.process_clan_name(update, context)
    elif context.user_data.get("awaiting_join_clan"):
        await handlers.process_join_clan(update, context)
    elif context.user_data.get("awaiting_friend_challenge"):
        username = msg.strip().lstrip("@")
        target = db.get_user_by_username(username)
        if not target:
            await update.message.reply_text("المستخدم غير موجود.")
            return
        # بدء تحدي صديق (يمكن تخزينه في active_games)
        await update.message.reply_text(f"تحدي صديق قيد التطوير (سيتم إعلام {target['first_name']}).")
        context.user_data["awaiting_friend_challenge"] = False

# ---------- أمر البانلات (للمؤسس) ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        await update.message.reply_text("غير مسموح")
        return
    await update.message.reply_text("لوحة التحكم:\n/start_war لبدء حرب عشائر")

async def start_war_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    # بدء حرب وهمية
    await update.message.reply_text("بدأت حرب العشائر!")
    # كود إنشاء حرب في db...

# ---------- تشغيل البوت ----------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("start_war", start_war_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
