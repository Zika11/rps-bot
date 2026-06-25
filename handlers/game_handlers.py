# handlers/game_handlers.py
import json
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import db, config, state, keyboards, game_logic, utils
from core.game_engine import get_result, bot_choice, calculate_winner
from core.tournament_manager import (
    get_tournament, update_tournament, get_bracket, save_bracket,
    get_match_data, save_match_data, advance_round
)

# ========== دوال الألعاب الأساسية ==========
async def solo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    game_id = state.start_solo_game(user.id)
    await query.edit_message_text("اختر حركتك:", reply_markup=keyboards.choice_buttons(f"solo_{game_id}"))

async def process_solo_pick(update, context, move, game_id):
    query = update.callback_query
    user = query.from_user
    game = state.get_game(game_id)
    if not game or game["player1"] != user.id:
        await query.edit_message_text("انتهت اللعبة.")
        return

    bot_move = bot_choice(user.id)
    result = get_result(move, bot_move)
    db.apply_game_result(user.id, result, move, None)
    utils.update_user_moves(user.id, move)
    theme = utils.get_choices_for_user(user.id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)
    text = f"أنت: {user_icon} vs البوت: {bot_icon}\nالنتيجة: {result}"
    await query.edit_message_text(text)
    state.finish_solo_game(game_id)

# ========== دوال المطابقة العشوائية ==========
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
        res1 = get_result(m1, m2)
        res2 = get_result(m2, m1)
        db.apply_game_result(p1, res1, m1, p2)
        db.apply_game_result(p2, res2, m2, p1)
        utils.update_user_moves(p1, m1)
        utils.update_user_moves(p2, m2)
        user1 = db.get_user(p1)
        user2 = db.get_user(p2)
        theme1 = utils.get_choices_for_user(p1)
        theme2 = utils.get_choices_for_user(p2)
        icon1 = theme1.get(m1, m1)
        icon2 = theme2.get(m2, m2)
        text = f"⚔️ {user1['first_name']} اختار {icon1} vs {user2['first_name']} اختار {icon2}\nالنتيجة: {res1} لصالح {user1['first_name']}"
        await query.edit_message_text(text)
        try:
            await context.bot.send_message(p2, text)
        except: pass
        await state.remove_game(game_id)
    else:
        await query.edit_message_text("تم تسجيل حركتك، بانتظار الخصم...")

# ========== دوال البطولة ==========
async def process_tournament_pick(update, context, move, tour_id, match_index):
    query = update.callback_query
    user = query.from_user

    tour = get_tournament(tour_id)
    if not tour:
        return

    bracket = get_bracket(tour_id)
    if not bracket:
        return

    current_round = tour["current_round"]
    round_key = f"round{current_round}"
    matches = bracket.get(round_key, [])
    if match_index >= len(matches):
        return

    match = matches[match_index]
    match_data = get_match_data(tour_id)
    match_data[str(match_index)] = match_data.get(str(match_index), {})
    match_data[str(match_index)][str(user.id)] = move
    save_match_data(tour_id, match_data)

    if str(match["p1"]) in match_data[str(match_index)] and str(match["p2"]) in match_data[str(match_index)]:
        m1 = match_data[str(match_index)][str(match["p1"])]
        m2 = match_data[str(match_index)][str(match["p2"])]
        res = get_result(m1, m2)
        winner = match["p1"] if res == "win" else match["p2"] if res == "loss" else None
        match["winner"] = winner
        bracket[round_key][match_index] = match
        save_bracket(tour_id, bracket)

        new_round, new_bracket = advance_round(tour_id, current_round, bracket)
        if new_round == "finished":
            update_tournament(tour_id, status="finished")
            final_winner = match["winner"]
            if final_winner:
                user_data = db.get_user(final_winner)
                db.update_user(final_winner, tournament_wins=user_data.get("tournament_wins", 0) + 1, points=user_data["points"] + 200)
                await context.bot.send_message(final_winner, "🎉 أنت بطل البطولة! ربحت 200 نقطة.")
        else:
            save_bracket(tour_id, new_bracket)
            update_tournament(tour_id, current_round=new_round)
            next_round_key = f"round{new_round}"
            next_matches = new_bracket.get(next_round_key, [])
            for i, m in enumerate(next_matches):
                await context.bot.send_message(m["p1"], f"🏆 الدور القادم! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
                await context.bot.send_message(m["p2"], f"🏆 الدور القادم! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))

    await query.edit_message_text("تم تسجيل حركتك.")

# ========== دوال التحديات ==========
async def friend_challenge_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("أرسل معرف الصديق (@username) لتحديه:")
    context.user_data["awaiting_friend_challenge"] = True

# ... باقي الدوال (spock, group, open, spectate) بنفس النمط.
