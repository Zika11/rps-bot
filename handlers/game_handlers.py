import json, asyncio, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, state, keyboards, game_logic, utils

# ---------- أوضاع اللعب الخاص ----------
async def solo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    game_id = state.start_solo_game(user.id)
    await query.edit_message_text("اختر حركتك:", reply_markup=keyboards.choice_buttons(f"solo_{game_id}"))

async def random_matchmaking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    result = await state.add_pending(user.id)
    if result is None:
        await query.answer("أنت بالفعل في قائمة الانتظار أو مشغول بلعبة!")
    elif result is True:
        await query.edit_message_text("بانتظار لاعب آخر...")
    else:
        opp_id = result
        game = state.get_game_by_player(user.id)
        if game:
            await query.edit_message_text("تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons(f"random_{game['game_id']}"))
            await context.bot.send_message(opp_id, "تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons(f"random_{game['game_id']}"))

async def friend_challenge_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("أرسل معرف الصديق (@username) لتحديه:")
    context.user_data["awaiting_friend_challenge"] = True

# ---------- معالجة اختيارات اللعب ----------
async def process_solo_pick(update, context, move, game_id):
    query = update.callback_query
    user = query.from_user
    game = state.get_game(game_id)
    if not game or game["player1"] != user.id:
        await query.edit_message_text("انتهت اللعبة.")
        return
    bot_move = utils.markov_bot_choice(user.id)
    result = game_logic.get_result(move, bot_move)
    db.apply_game_result(user.id, result, move, None)
    utils.update_user_moves(user.id, move)
    theme = utils.get_choices_for_user(user.id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)
    text = f"أنت: {user_icon} vs البوت: {bot_icon}\nالنتيجة: {result}"
    await query.edit_message_text(text)
    state.finish_solo_game(game_id)

async def process_random_pick(update, context, move, game_id):
    query = update.callback_query
    user = query.from_user
    game = state.get_game(game_id)
    if not game or (game["player1"] != user.id and game["player2"] != user.id):
        await query.edit_message_text("انتهت اللعبة.")
        return
    state.set_game_move(game_id, user.id, move)
    moves = state.get_game_moves(game_id)
    p1, p2 = game["player1"], game["player2"]
    if str(p1) in moves and str(p2) in moves:
        m1 = moves[str(p1)]
        m2 = moves[str(p2)]
        res1 = game_logic.get_result(m1, m2)
        res2 = game_logic.get_result(m2, m1)
        db.apply_game_result(p1, res1, m1, p2)
        db.apply_game_result(p2, res2, m2, p1)
        utils.update_user_moves(p1, m1)
        utils.update_user_moves(p2, m2)
        theme1 = utils.get_choices_for_user(p1)
        theme2 = utils.get_choices_for_user(p2)
        icon1 = theme1.get(m1, m1)
        icon2 = theme2.get(m2, m2)
        p1_name = db.get_user(p1)["first_name"]      # ✅ تغيير
        p2_name = db.get_user(p2)["first_name"]      # ✅ تغيير
        text = f"⚔️ {p1_name} اختار {icon1} vs {p2_name} اختار {icon2}\nالنتيجة: {res1} لصالح {p1_name}"
        await query.edit_message_text(text)
        try:
            await context.bot.send_message(p2, text)
        except: pass
        await state.remove_game(game_id)
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
    game_id = state.start_solo_game(user.id)
    db.apply_game_result(user.id, result, move, None)
    utils.update_user_moves(user.id, move)
    theme = utils.get_choices_for_user(user.id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)
    text = f"أنت: {user_icon} vs البوت: {bot_icon}\nالنتيجة: {result}"
    await query.edit_message_text(text)
    state.finish_solo_game(game_id)

async def process_group_solo_pick(update, context, move, chat_id, player_id, game_id):
    query = update.callback_query
    user = query.from_user
    if user.id != player_id:
        await query.answer("هذه اللعبة ليست لك!")
        return
    game = state.group_solo_games.get(player_id)
    if not game or game["game_id"] != game_id:
        await query.answer("انتهت اللعبة.")
        return
    try:
        await context.bot.delete_message(chat_id, game["message_id"])
    except: pass
    bot_move = utils.markov_bot_choice(player_id)
    result = game_logic.get_result(move, bot_move)
    db.apply_game_result(player_id, result, move, None)
    utils.update_user_moves(player_id, move)
    theme = utils.get_choices_for_user(player_id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)
    text = (f"🎮 **نتيجة اللعبة الفردية**\n"
            f"{user.first_name} اختار {user_icon}\n"
            f"البوت اختار {bot_icon}\n"
            f"النتيجة: {result}")
    await context.bot.send_message(chat_id, text)
    state.finish_solo_game(game_id)
    state.group_solo_games.pop(player_id, None)
    await query.answer("تم إرسال النتيجة إلى المجموعة.")

# ---------- التحدي المفتوح ----------
async def start_open_challenge(update, context, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        if chat_id in state.open_challenges:
            await query.answer("يوجد بالفعل تحدي مفتوح في هذه المجموعة!")
            return
        await context.bot.send_message(user.id, "اختر حركتك للتحدي المفتوح:", reply_markup=keyboards.choice_buttons(f"open_{chat_id}_temp"))
        state.open_challenges[chat_id] = {"initiator": user.id, "move": None, "message_id": None}
    await query.answer("تم إرسال خيارات الحركة في الخاص.")

async def process_open_pick(update, context, move, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if not challenge or challenge["initiator"] != user.id:
            await query.edit_message_text("لا يوجد تحدي بهذا المعرف.")
            return
        challenge["move"] = move
        await query.edit_message_text("تم اختيار حركتك. سيتم الإعلان في المجموعة...")
        msg = await context.bot.send_message(chat_id, f"🎯 **تحدي مفتوح!**\n{user.first_name} اختار حركته.\nمن يقبل التحدي؟", reply_markup=keyboards.open_challenge_accept_button(chat_id))
        challenge["message_id"] = msg.message_id
        asyncio.create_task(auto_cancel_open_challenge(chat_id, context))

async def auto_cancel_open_challenge(chat_id, context):
    await asyncio.sleep(60)
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if challenge:
            try:
                await context.bot.edit_message_text(chat_id, challenge["message_id"], text="⏰ انتهت صلاحية التحدي المفتوح.")
            except: pass
            state.open_challenges.pop(chat_id, None)

async def accept_open_challenge(update, context, chat_id):
    query = update.callback_query
    user = query.from_user
    acceptor_id = user.id
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if not challenge:
            await query.answer("انتهى التحدي أو غير موجود.")
            return
        if acceptor_id == challenge["initiator"]:
            await query.answer("لا يمكنك تحدي نفسك!")
            return
        challenge["acceptor"] = acceptor_id
    await context.bot.send_message(acceptor_id, "اختر حركتك:", reply_markup=keyboards.choice_buttons(f"open_accept_{chat_id}_temp"))
    await query.answer("تم قبول التحدي! اختر حركتك في الخاص.")

async def process_open_acceptor_pick(update, context, move, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if not challenge or challenge.get("acceptor") != user.id:
            await query.edit_message_text("لا يمكنك الرد على هذا التحدي.")
            return
        initiator_id = challenge["initiator"]
        initiator_move = challenge["move"]
        if not initiator_move:
            await query.edit_message_text("لم يتم تحديد حركة البادئ بعد.")
            return
        result_init = game_logic.get_result(initiator_move, move)
        db.apply_game_result(initiator_id, result_init, initiator_move, user.id)
        result_acceptor = "loss" if result_init == "win" else ("win" if result_init == "loss" else "draw")
        db.apply_game_result(user.id, result_acceptor, move, initiator_id)
        u1 = db.get_user(initiator_id)      # ✅ تغيير
        u2 = db.get_user(user.id)           # ✅ تغيير
        theme1 = utils.get_choices_for_user(initiator_id)
        theme2 = utils.get_choices_for_user(user.id)
        icon1 = theme1.get(initiator_move, initiator_move)
        icon2 = theme2.get(move, move)
        winner = f"🏆 فاز {u1['first_name']}!" if result_init == "win" else (f"🏆 فاز {u2['first_name']}!" if result_acceptor == "win" else "🤝 تعادل!")
        text = f"⚔️ **نتيجة التحدي المفتوح**\n{u1['first_name']} اختار {icon1}\n{u2['first_name']} اختار {icon2}\n{winner}"
        await context.bot.send_message(chat_id, text)
        try: await context.bot.delete_message(chat_id, challenge["message_id"])
        except: pass
        state.open_challenges.pop(chat_id, None)
    await query.edit_message_text("تم إرسال النتيجة إلى المجموعة.")

# ---------- البطولة ----------
async def process_tournament_pick(update, context, move, tour_id, match_index):
    query = update.callback_query
    user = query.from_user
    tour = db.get_tournament(tour_id)
    if not tour: return
    bracket = json.loads(tour.get("bracket", "{}"))
    current_round = tour["current_round"]
    round_key = f"round{current_round}"
    matches = bracket.get(round_key, [])
    if match_index >= len(matches): return
    match = matches[match_index]
    match_data = json.loads(tour.get("match_data", "{}"))
    match_data[str(match_index)] = match_data.get(str(match_index), {})
    match_data[str(match_index)][str(user.id)] = move
    db.update_tournament(tour_id, match_data=json.dumps(match_data))
    if str(match["p1"]) in match_data[str(match_index)] and str(match["p2"]) in match_data[str(match_index)]:
        m1 = match_data[str(match_index)][str(match["p1"])]
        m2 = match_data[str(match_index)][str(match["p2"])]
        res = game_logic.get_result(m1, m2)
        winner = match["p1"] if res == "win" else match["p2"] if res == "loss" else None
        match["winner"] = winner
        bracket[round_key][match_index] = match
        db.update_tournament(tour_id, bracket=json.dumps(bracket))
        if current_round == 1:
            winners = [m["winner"] for m in bracket["round1"] if m.get("winner") is not None]
            if len(winners) == 4:
                bracket["round2"] = [{"p1": winners[0], "p2": winners[1]}, {"p1": winners[2], "p2": winners[3]}]
                db.update_tournament(tour_id, bracket=json.dumps(bracket), current_round=2)
                for i, m2 in enumerate(bracket["round2"]):
                    await context.bot.send_message(m2["p1"], f"🏆 نصف النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
                    await context.bot.send_message(m2["p2"], f"🏆 نصف النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
        elif current_round == 2:
            winners = [m["winner"] for m in bracket["round2"] if m.get("winner") is not None]
            if len(winners) == 2:
                bracket["final"] = [{"p1": winners[0], "p2": winners[1]}]
                db.update_tournament(tour_id, bracket=json.dumps(bracket), current_round=3)
                for i, mf in enumerate(bracket["final"]):
                    await context.bot.send_message(mf["p1"], f"🏆 النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
                    await context.bot.send_message(mf["p2"], f"🏆 النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
        elif current_round == 3:
            final_winner = match["winner"]
            if final_winner:
                user_data = db.get_user(final_winner)   # ✅ تغيير
                db.update_user(final_winner, tournament_wins=user_data.get("tournament_wins",0)+1, points=user_data["points"]+200)   # ✅ تغيير
                await context.bot.send_message(final_winner, "🎉 أنت بطل البطولة! ربحت 200 نقطة.")
            db.update_tournament(tour_id, status="finished")
    await query.edit_message_text("تم تسجيل حركتك.")

# ---------- غرفة المشاهدة ----------
async def process_spectate_pick(update, context, move, room_id):
    query = update.callback_query
    user = query.from_user
    room = db.get_spectator_room(room_id)
    if not room or room["status"] != "active":
        await query.edit_message_text("انتهت الغرفة.")
        return
    if user.id not in (room["player1"], room["player2"]):
        await query.edit_message_text("لست مشاركاً في هذه المباراة.")
        return
    moves = json.loads(room["moves"] or "{}")
    moves[str(user.id)] = move
    db.update_spectator_room(room_id, moves=json.dumps(moves))
    p1, p2 = room["player1"], room["player2"]
    if str(p1) in moves and str(p2) in moves:
        m1 = moves[str(p1)]
        m2 = moves[str(p2)]
        res1 = game_logic.get_result(m1, m2)
        db.apply_game_result(p1, res1, m1, p2)
        res2 = "loss" if res1 == "win" else ("win" if res1 == "loss" else "draw")
        db.apply_game_result(p2, res2, m2, p1)
        u1 = db.get_user(p1)      # ✅ تغيير
        u2 = db.get_user(p2)      # ✅ تغيير
        theme1 = utils.get_choices_for_user(p1)
        theme2 = utils.get_choices_for_user(p2)
        icon1 = theme1.get(m1, m1)
        icon2 = theme2.get(m2, m2)
        text = f"👀 **نتيجة مباراة المشاهدة**\n{u1['first_name']} اختار {icon1}\n{u2['first_name']} اختار {icon2}\nالنتيجة: {res1} لصالح {u1['first_name']}"
        await context.bot.send_message(room["chat_id"], text)
        db.update_spectator_room(room_id, status="finished")
    await query.edit_message_text("تم تسجيل حركتك.")
