import json, random, logging, uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, keyboards, state

logger = logging.getLogger(__name__)

# ---------- بطولات ----------
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

# ---------- World Boss ----------
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

# ---------- تحديات المشاهدة ----------
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

# ---------- Spectator Room ----------
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

# ---------- موسم ----------
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
